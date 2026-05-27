"""Tests for strategy registry core — T4261-T4290."""
from __future__ import annotations

import json

import pytest

from core.strategy_research_interface import (
    DEFAULT_SAFETY_FLAGS,
    REQUIRED_BAR_FIELDS,
    REQUIRED_SAFETY_NOTES,
    StrategyDefinition,
)
from core.strategy_registry_core import RejectedStrategy, StrategyRegistry


# --- Helpers ---

def _make_defn(strategy_id: str = "test_breakout", family: str = "breakout", **overrides) -> StrategyDefinition:
    defaults = dict(
        strategy_id=strategy_id,
        strategy_family=family,
        display_name=f"Test {strategy_id}",
        description=f"A test strategy: {strategy_id}",
        parameter_schema={"lookback_bars": {"type": "int", "min": 5, "max": 100, "default": 20}},
        required_bar_fields=list(REQUIRED_BAR_FIELDS),
        signal_generation_contract={"input": "bars", "output": "signals", "deterministic": True},
        safety_notes=list(REQUIRED_SAFETY_NOTES),
        safety_flags=dict(DEFAULT_SAFETY_FLAGS),
        deterministic=True,
        local_only=True,
        no_network=True,
        no_exchange=True,
    )
    defaults.update(overrides)
    return StrategyDefinition(**defaults)


# --- Registration ---

class TestRegistryRegister:
    def test_register_valid_strategy(self):
        reg = StrategyRegistry()
        errors = reg.register(_make_defn())
        assert errors == []
        assert reg.strategy_count() == 1
        assert reg.list_strategies() == ["test_breakout"]

    def test_register_multiple_strategies(self):
        reg = StrategyRegistry()
        reg.register(_make_defn("breakout"))
        reg.register(_make_defn("momentum", family="momentum"))
        assert reg.strategy_count() == 2
        assert reg.list_strategies() == ["breakout", "momentum"]

    def test_register_unsafe_strategy_rejected(self):
        reg = StrategyRegistry()
        errors = reg.register(_make_defn(no_network=False))
        assert len(errors) > 0
        assert reg.strategy_count() == 0
        assert len(reg.rejected_strategies()) == 1
        assert reg.rejected_strategies()[0].strategy_id == "test_breakout"

    def test_register_duplicate_overwrites(self):
        reg = StrategyRegistry()
        reg.register(_make_defn())
        reg.register(_make_defn())  # same id
        assert reg.strategy_count() == 1

    def test_get_existing_strategy(self):
        reg = StrategyRegistry()
        defn = _make_defn()
        reg.register(defn)
        result = reg.get_strategy("test_breakout")
        assert result is not None
        assert result.strategy_id == "test_breakout"

    def test_get_missing_strategy(self):
        reg = StrategyRegistry()
        assert reg.get_strategy("nonexistent") is None


# --- Validation status ---

class TestValidationStatus:
    def test_empty_registry(self):
        reg = StrategyRegistry()
        assert reg.validation_status() == "EMPTY"

    def test_with_strategies(self):
        reg = StrategyRegistry()
        reg.register(_make_defn())
        assert reg.validation_status() == "PASS"


# --- Deterministic export ---

class TestDeterministicExport:
    def test_sorted_strategies(self):
        reg = StrategyRegistry()
        reg.register(_make_defn("momentum", family="momentum"))
        reg.register(_make_defn("breakout"))
        d = reg.to_dict()
        ids = [s["strategy_id"] for s in d["strategies"]]
        assert ids == ["breakout", "momentum"]

    def test_json_deterministic(self):
        reg = StrategyRegistry()
        reg.register(_make_defn())
        j1 = reg.to_json()
        j2 = reg.to_json()
        assert j1 == j2

    def test_json_contains_safety_flags(self):
        reg = StrategyRegistry()
        reg.register(_make_defn())
        d = reg.to_dict()
        assert d["safety_flags"]["no_live"] is True
        assert d["safety_flags"]["no_submit"] is True
        assert d["release_hold"] == "HOLD"

    def test_json_roundtrip(self):
        reg = StrategyRegistry()
        reg.register(_make_defn())
        j = reg.to_json()
        d = json.loads(j)
        assert d["registry_id"] == "multi_strategy_research_registry"
        assert d["strategy_count"] == 1

    def test_rejected_strategies_in_export(self):
        reg = StrategyRegistry()
        reg.register(_make_defn(no_network=False))
        d = reg.to_dict()
        assert len(d["rejected_strategies"]) == 1
        assert d["rejected_strategies"][0]["strategy_id"] == "test_breakout"


# --- CLI ---

class TestRegistryCLI:
    def test_cli_runs(self, tmp_path):
        """Test the generate_strategy_experiment_registry CLI script."""
        import subprocess
        result = subprocess.run(
            [
                "python3", "scripts/generate_strategy_experiment_registry.py",
                "--output-dir", str(tmp_path),
                "--strategies", "breakout,mean_reversion",
            ],
            capture_output=True,
            text=True,
            cwd="/Users/winnie/Documents/trae_projects/qq",
        )
        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        out_file = tmp_path / "strategy_registry.json"
        assert out_file.exists()
        d = json.loads(out_file.read_text())
        assert d["strategy_count"] == 2
        assert d["release_hold"] == "HOLD"
