"""Tests for parameter search engine — T4471-T4500."""
from __future__ import annotations

import json

import pytest

from core.parameter_search_engine import (
    ParameterSearchResult,
    run_parameter_search,
)
from core.strategy_research_parameters import ParameterSchema, ParameterSpec


def _make_schema(strategy_id: str = "test"):
    return ParameterSchema(
        strategy_id=strategy_id,
        parameters=(
            ParameterSpec(name="lookback", type="int", min=10, max=30, default=20),
            ParameterSpec(name="threshold", type="float", min=0.0, max=1.0, default=0.5),
        ),
    )


class TestParameterSearch:
    def test_basic_search(self):
        schemas = {"test": _make_schema()}
        result = run_parameter_search(schemas, search_budget=100)
        assert result.evaluated_combinations > 0
        assert result.release_hold == "HOLD"
        assert "test" in result.strategy_ids

    def test_multi_strategy_search(self):
        schemas = {
            "a": _make_schema("a"),
            "b": _make_schema("b"),
        }
        result = run_parameter_search(schemas, search_budget=200)
        assert len(result.strategy_ids) == 2
        assert result.evaluated_combinations > 0

    def test_budget_truncation(self):
        # Schema with many combos
        schema = ParameterSchema(
            strategy_id="big",
            parameters=(
                ParameterSpec(name="a", type="int", min=1, max=20),
                ParameterSpec(name="b", type="int", min=1, max=20),
            ),
        )
        result = run_parameter_search({"big": schema}, search_budget=5)
        assert result.budget_truncated is True
        assert result.overfit_warning is True

    def test_no_truncation_within_budget(self):
        schemas = {"test": _make_schema()}
        result = run_parameter_search(schemas, search_budget=1000)
        assert result.budget_truncated is False

    def test_deterministic_output(self):
        schemas = {"test": _make_schema()}
        r1 = run_parameter_search(schemas, search_budget=100)
        r2 = run_parameter_search(schemas, search_budget=100)
        assert r1.to_json() == r2.to_json()

    def test_json_roundtrip(self):
        schemas = {"test": _make_schema()}
        result = run_parameter_search(schemas, search_budget=100)
        d = json.loads(result.to_json())
        assert d["search_result_id"] == "parameter_search_001"
        assert d["release_hold"] == "HOLD"


class TestCLI:
    def test_cli_runs(self, tmp_path):
        import subprocess
        # First generate registry
        reg_dir = tmp_path / "registry"
        reg_dir.mkdir()
        result = subprocess.run(
            [
                "python3", "scripts/generate_strategy_experiment_registry.py",
                "--output-dir", str(reg_dir),
                "--strategies", "breakout,mean_reversion",
            ],
            capture_output=True, text=True,
            cwd="/Users/winnie/Documents/trae_projects/qq",
        )
        assert result.returncode == 0

        # Then run parameter search
        result = subprocess.run(
            [
                "python3", "scripts/run_parameter_search_lab.py",
                "--registry", str(reg_dir / "strategy_registry.json"),
                "--output-dir", str(tmp_path),
                "--search-budget", "50",
            ],
            capture_output=True, text=True,
            cwd="/Users/winnie/Documents/trae_projects/qq",
        )
        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        out_file = tmp_path / "parameter_search.json"
        assert out_file.exists()
        d = json.loads(out_file.read_text())
        assert d["release_hold"] == "HOLD"
