"""Negative safety and invalid input tests — T4981-T5010."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.strategy_research_interface import (
    DEFAULT_SAFETY_FLAGS,
    REQUIRED_BAR_FIELDS,
    REQUIRED_SAFETY_NOTES,
    StrategyDefinition,
    is_strategy_safe,
    validate_adapter_safety,
    validate_strategy_definition,
)
from core.research_workbench_manifest import (
    WorkbenchManifest,
    build_manifest,
    validate_manifest,
)
from core.parameter_search_guard import check_search_budget
from core.strategy_registry_core import StrategyRegistry
from core.research_artifact_index import ArtifactEntry, ArtifactIndex, validate_artifact_index


def _make_defn(**overrides):
    defaults = dict(
        strategy_id="test", strategy_family="breakout", display_name="Test", description="Test",
        parameter_schema={"x": {"type": "int", "min": 1, "max": 10}},
        required_bar_fields=list(REQUIRED_BAR_FIELDS),
        signal_generation_contract={"input": "bars", "output": "signals", "deterministic": True},
        safety_notes=list(REQUIRED_SAFETY_NOTES), safety_flags=dict(DEFAULT_SAFETY_FLAGS),
        deterministic=True, local_only=True, no_network=True, no_exchange=True,
    )
    defaults.update(overrides)
    return StrategyDefinition(**defaults)


class TestUnsafeAdapterRejection:
    def test_no_network_false(self):
        defn = _make_defn(no_network=False)
        assert is_strategy_safe(defn) is False

    def test_no_exchange_false(self):
        defn = _make_defn(no_exchange=False)
        assert is_strategy_safe(defn) is False

    def test_not_deterministic(self):
        defn = _make_defn(deterministic=False)
        assert is_strategy_safe(defn) is False

    def test_missing_safety_notes(self):
        defn = _make_defn(safety_notes=[])
        assert is_strategy_safe(defn) is False


class TestUnboundedParameterRejection:
    def test_empty_parameter_schema(self):
        defn = _make_defn(parameter_schema={})
        errors = validate_strategy_definition(defn)
        assert any("parameter_schema" in e for e in errors)


class TestForbiddenImportDetection:
    def test_live_runner(self):
        errors = validate_adapter_safety(["core.live_runner"])
        assert len(errors) > 0

    def test_binance(self):
        errors = validate_adapter_safety(["core.binance_connector"])
        assert len(errors) > 0

    def test_runtime(self):
        errors = validate_adapter_safety(["core.runtime_module"])
        assert len(errors) > 0

    def test_planner(self):
        errors = validate_adapter_safety(["core.planner_integration"])
        assert len(errors) > 0


class TestManifestSafetyFlags:
    def test_wrong_release_hold(self):
        m = WorkbenchManifest(
            manifest_id="t", generated_by="t", release_hold="READY",
            no_live=True, no_submit=True, no_exchange=True,
            no_runtime_integration=True, no_planner_integration=True, no_network=True,
            artifacts=(), sha256={}, artifact_sizes={}, warnings=(), validation_status="PASS",
        )
        errors = validate_manifest(m)
        assert any("HOLD" in e for e in errors)

    def test_no_live_false(self):
        m = WorkbenchManifest(
            manifest_id="t", generated_by="t", release_hold="HOLD",
            no_live=False, no_submit=True, no_exchange=True,
            no_runtime_integration=True, no_planner_integration=True, no_network=True,
            artifacts=(), sha256={}, artifact_sizes={}, warnings=(), validation_status="PASS",
        )
        errors = validate_manifest(m)
        assert any("no_live" in e for e in errors)

    def test_no_network_false(self):
        m = WorkbenchManifest(
            manifest_id="t", generated_by="t", release_hold="HOLD",
            no_live=True, no_submit=True, no_exchange=True,
            no_runtime_integration=True, no_planner_integration=True, no_network=False,
            artifacts=(), sha256={}, artifact_sizes={}, warnings=(), validation_status="PASS",
        )
        errors = validate_manifest(m)
        assert any("no_network" in e for e in errors)


class TestForbiddenFilePath:
    def test_forbidden_path_in_artifact_index(self):
        entry = ArtifactEntry(
            artifact_id="a1", artifact_type="test",
            path="core/live_runner.py", sha256="abc", size_bytes=10,
        )
        index = ArtifactIndex(artifact_index_id="idx", artifacts=(entry,))
        errors = validate_artifact_index(index)
        assert any("forbidden" in e for e in errors)

    def test_remote_uri_in_artifact_index(self):
        entry = ArtifactEntry(
            artifact_id="a1", artifact_type="test",
            path="https://evil.com/data.json", sha256="abc", size_bytes=10,
        )
        index = ArtifactIndex(artifact_index_id="idx", artifacts=(entry,))
        errors = validate_artifact_index(index)
        assert any("remote" in e for e in errors)


class TestSearchBudgetBypass:
    def test_cannot_bypass_in_strict_mode(self):
        result = check_search_budget(999999, search_budget=10, mode="strict")
        assert result.allowed is False

    def test_truncation_marks_warning(self):
        result = check_search_budget(200, search_budget=100, mode="truncate")
        assert result.budget_truncated is True
        assert result.overfit_warning is True
