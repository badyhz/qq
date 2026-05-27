"""Tests for runtime governance input contract — T794."""

from __future__ import annotations

import pytest

from core.governance_failure_taxonomy import FailureCategory
from core.runtime_governance_contract import (
    RuntimeGovernanceContractResult,
    RuntimeGovernanceInput,
    normalize_runtime_governance_input,
    runtime_governance_input_to_dict,
    validate_runtime_governance_input,
)


# ── helpers ──────────────────────────────────────────────────────────


def _valid_shadow(**overrides) -> RuntimeGovernanceInput:
    base = dict(
        run_id="run-001",
        adapter_id="adapter-spot",
        mode="shadow",
        requested_action="place_order",
        symbol="BTCUSDT",
        environment="staging",
        allow_network=False,
        allow_submit=False,
        allow_file_io=False,
    )
    base.update(overrides)
    return normalize_runtime_governance_input(**base)


# ── valid inputs ─────────────────────────────────────────────────────


class TestValidInputs:
    def test_valid_shadow(self):
        inp = _valid_shadow()
        result = validate_runtime_governance_input(inp)
        assert result.ok is True
        assert result.failures == []
        assert result.normalized_input is inp
        assert result.notes == ["input valid"]

    def test_valid_dry_run(self):
        inp = _valid_shadow(mode="dry_run")
        result = validate_runtime_governance_input(inp)
        assert result.ok is True


# ── structural validation ────────────────────────────────────────────


class TestStructuralValidation:
    def test_missing_run_id(self):
        inp = _valid_shadow(run_id="")
        result = validate_runtime_governance_input(inp)
        assert result.ok is False
        assert any(f.code == "VALIDATION_FAILURE" and "run_id" in f.message for f in result.failures)

    def test_missing_adapter_id(self):
        inp = _valid_shadow(adapter_id="")
        result = validate_runtime_governance_input(inp)
        assert result.ok is False
        assert any(f.code == "VALIDATION_FAILURE" and "adapter_id" in f.message for f in result.failures)

    def test_unknown_mode(self):
        inp = _valid_shadow(mode="live")
        result = validate_runtime_governance_input(inp)
        assert result.ok is False
        assert any("unknown mode" in f.message for f in result.failures)


# ── policy blocks ────────────────────────────────────────────────────


class TestPolicyBlocks:
    def test_submit_blocked_outside_test_env(self):
        inp = _valid_shadow(allow_submit=True, environment="staging")
        result = validate_runtime_governance_input(inp)
        assert result.ok is False
        policy_failures = [f for f in result.failures if f.category == FailureCategory.POLICY_BLOCK]
        assert len(policy_failures) == 1
        assert "allow_submit" in policy_failures[0].message

    def test_submit_allowed_in_test_env(self):
        inp = _valid_shadow(allow_submit=True, environment="test")
        result = validate_runtime_governance_input(inp)
        assert result.ok is True

    def test_network_blocked_without_explicit_mode(self):
        inp = normalize_runtime_governance_input(
            run_id="run-001",
            adapter_id="adapter-spot",
            mode="",
            allow_network=True,
        )
        result = validate_runtime_governance_input(inp)
        assert result.ok is False
        policy_failures = [f for f in result.failures if f.category == FailureCategory.POLICY_BLOCK]
        assert len(policy_failures) == 1
        assert "allow_network" in policy_failures[0].message


# ── serialization ────────────────────────────────────────────────────


class TestSerialization:
    def test_dict_roundtrip(self):
        inp = _valid_shadow(metadata={"tag": "unit"})
        d = runtime_governance_input_to_dict(inp)
        assert d["run_id"] == "run-001"
        assert d["mode"] == "shadow"
        assert d["metadata"] == {"tag": "unit"}
        assert d["allow_submit"] is False

    def test_metadata_copied_safely(self):
        meta = {"key": "value"}
        inp = _valid_shadow(metadata=meta)
        d = runtime_governance_input_to_dict(inp)
        meta["key"] = "mutated"
        assert d["metadata"]["key"] == "value"


# ── determinism ──────────────────────────────────────────────────────


class TestDeterminism:
    def test_repeated_result_deterministic(self):
        inp = _valid_shadow()
        r1 = validate_runtime_governance_input(inp)
        r2 = validate_runtime_governance_input(inp)
        assert r1.ok == r2.ok
        assert len(r1.failures) == len(r2.failures)
        assert r1.notes == r2.notes
