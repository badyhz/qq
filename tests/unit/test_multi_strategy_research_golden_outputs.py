"""Golden output regression tests — T4951-T4980.

Tests deterministic output of registry, parameter search, matrix, manifest.
"""
from __future__ import annotations

import json

import pytest

from core.multi_strategy_matrix import build_experiment_matrix
from core.parameter_search_engine import run_parameter_search
from core.research_workbench_manifest import build_manifest, validate_manifest
from core.strategy_research_parameters import ParameterSchema, ParameterSpec
from core.strategy_registry_adapters import register_all_adapters
from core.strategy_registry_core import StrategyRegistry


class TestGoldenRegistry:
    def test_registry_deterministic(self):
        """Registry output must be byte-identical across runs."""
        reg = StrategyRegistry()
        register_all_adapters(reg)
        j1 = reg.to_json()
        j2 = reg.to_json()
        assert j1 == j2

    def test_registry_golden_structure(self):
        reg = StrategyRegistry()
        register_all_adapters(reg)
        d = json.loads(reg.to_json())
        assert d["registry_id"] == "multi_strategy_research_registry"
        assert d["strategy_count"] == 4
        assert d["validation_status"] == "PASS"
        assert d["release_hold"] == "HOLD"
        assert d["safety_flags"]["no_live"] is True
        assert len(d["rejected_strategies"]) == 0
        strategy_ids = [s["strategy_id"] for s in d["strategies"]]
        assert strategy_ids == sorted(strategy_ids)


class TestGoldenParameterSearch:
    def test_search_deterministic(self):
        schema = ParameterSchema(
            strategy_id="test",
            parameters=(ParameterSpec(name="x", type="int", min=1, max=5),),
        )
        r1 = run_parameter_search({"test": schema}, search_budget=100)
        r2 = run_parameter_search({"test": schema}, search_budget=100)
        assert r1.to_json() == r2.to_json()

    def test_search_golden_structure(self):
        schema = ParameterSchema(
            strategy_id="test",
            parameters=(ParameterSpec(name="x", type="int", min=1, max=5),),
        )
        result = run_parameter_search({"test": schema}, search_budget=100)
        d = json.loads(result.to_json())
        assert d["search_result_id"] == "parameter_search_001"
        assert d["release_hold"] == "HOLD"
        assert d["budget_truncated"] is False


class TestGoldenMatrix:
    def test_matrix_deterministic(self):
        from core.strategy_research_parameters import ParameterSet
        ps = [ParameterSet(parameter_set_id="ps1", strategy_id="breakout", preset_name="b", parameters={"x": 1})]
        m1 = build_experiment_matrix(["breakout"], ["BTCUSDT"], ["5m"], ["s0"], ps)
        m2 = build_experiment_matrix(["breakout"], ["BTCUSDT"], ["5m"], ["s0"], ps)
        j1 = json.dumps({"rows": [{"id": r.matrix_row_id} for r in m1.rows]}, sort_keys=True)
        j2 = json.dumps({"rows": [{"id": r.matrix_row_id} for r in m2.rows]}, sort_keys=True)
        assert j1 == j2


class TestGoldenManifest:
    def test_manifest_deterministic(self, tmp_path):
        (tmp_path / "strategy_registry.json").write_text("{}")
        m = build_manifest(tmp_path, required_artifacts=["strategy_registry.json", "manifest.json"])
        d1 = json.dumps(json.loads(json.dumps({
            "release_hold": m.release_hold,
            "no_live": m.no_live,
            "validation_status": m.validation_status,
        }, sort_keys=True)))
        m2 = build_manifest(tmp_path, required_artifacts=["strategy_registry.json", "manifest.json"])
        d2 = json.dumps(json.loads(json.dumps({
            "release_hold": m2.release_hold,
            "no_live": m2.no_live,
            "validation_status": m2.validation_status,
        }, sort_keys=True)))
        assert d1 == d2
