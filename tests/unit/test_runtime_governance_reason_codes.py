"""Tests for core.runtime_governance_reason_codes — deterministic reason code registry."""

import pytest

from core.governance_failure_taxonomy import FailureCategory, FailureSeverity
from core.runtime_governance_reason_codes import (
    RuntimeGovernanceReasonCode,
    build_runtime_governance_reason_code_registry,
    get_runtime_governance_reason_code,
    reason_code_registry_to_dict,
    reason_code_registry_to_markdown,
)

EXPECTED_CODES = [
    "RG_OK",
    "RG_MISSING_RUN_ID",
    "RG_MISSING_ADAPTER_ID",
    "RG_UNKNOWN_MODE",
    "RG_SUBMIT_BLOCKED_NON_TEST",
    "RG_NETWORK_BLOCKED_MODE",
    "RG_POLICY_BLOCK",
    "RG_UNKNOWN_FAILURE",
]


class TestRegistryBuild:
    def test_registry_has_eight_codes(self):
        registry = build_runtime_governance_reason_code_registry()
        assert len(registry) == 8

    def test_registry_codes_match_expected(self):
        registry = build_runtime_governance_reason_code_registry()
        codes = [rc.code for rc in registry]
        assert codes == EXPECTED_CODES


class TestLookup:
    def test_lookup_by_code_returns_correct(self):
        rc = get_runtime_governance_reason_code("RG_OK")
        assert rc.code == "RG_OK"
        assert rc.description == "governance check passed"

    def test_lookup_unknown_raises_value_error(self):
        with pytest.raises(ValueError, match="unknown governance reason code"):
            get_runtime_governance_reason_code("DOES_NOT_EXIST")


class TestFieldValues:
    def test_rg_ok_fields(self):
        rc = get_runtime_governance_reason_code("RG_OK")
        assert rc.category == FailureCategory.VALIDATION_FAILURE
        assert rc.severity == FailureSeverity.INFO
        assert rc.retryable is False

    def test_rg_submit_blocked_fields(self):
        rc = get_runtime_governance_reason_code("RG_SUBMIT_BLOCKED_NON_TEST")
        assert rc.category == FailureCategory.POLICY_BLOCK
        assert rc.severity == FailureSeverity.CRITICAL
        assert rc.retryable is False

    def test_rg_unknown_failure_fields(self):
        rc = get_runtime_governance_reason_code("RG_UNKNOWN_FAILURE")
        assert rc.category == FailureCategory.UNKNOWN
        assert rc.severity == FailureSeverity.ERROR
        assert rc.retryable is True

    def test_rg_network_blocked_fields(self):
        rc = get_runtime_governance_reason_code("RG_NETWORK_BLOCKED_MODE")
        assert rc.category == FailureCategory.POLICY_BLOCK
        assert rc.severity == FailureSeverity.CRITICAL
        assert rc.retryable is False

    def test_rg_policy_block_fields(self):
        rc = get_runtime_governance_reason_code("RG_POLICY_BLOCK")
        assert rc.category == FailureCategory.POLICY_BLOCK
        assert rc.severity == FailureSeverity.CRITICAL
        assert rc.retryable is False


class TestDictSerialization:
    def test_dict_deterministic(self):
        registry = build_runtime_governance_reason_code_registry()
        d1 = reason_code_registry_to_dict(registry)
        d2 = reason_code_registry_to_dict(registry)
        assert d1 == d2

    def test_dict_keys_present(self):
        registry = build_runtime_governance_reason_code_registry()
        dicts = reason_code_registry_to_dict(registry)
        assert len(dicts) == 8
        for d in dicts:
            assert set(d.keys()) == {"code", "category", "severity", "retryable", "description"}

    def test_dict_values_match_enum_values(self):
        registry = build_runtime_governance_reason_code_registry()
        dicts = reason_code_registry_to_dict(registry)
        ok = next(d for d in dicts if d["code"] == "RG_OK")
        assert ok["category"] == "validation_failure"
        assert ok["severity"] == "info"
        assert ok["retryable"] is False


class TestMarkdownSerialization:
    def test_markdown_deterministic(self):
        registry = build_runtime_governance_reason_code_registry()
        md1 = reason_code_registry_to_markdown(registry)
        md2 = reason_code_registry_to_markdown(registry)
        assert md1 == md2

    def test_markdown_contains_table(self):
        registry = build_runtime_governance_reason_code_registry()
        md = reason_code_registry_to_markdown(registry)
        assert "| Code |" in md
        assert "|------|" in md
        assert "| RG_OK |" in md
        assert "| RG_UNKNOWN_FAILURE |" in md

    def test_markdown_has_all_codes(self):
        registry = build_runtime_governance_reason_code_registry()
        md = reason_code_registry_to_markdown(registry)
        for code in EXPECTED_CODES:
            assert f"| {code} |" in md
