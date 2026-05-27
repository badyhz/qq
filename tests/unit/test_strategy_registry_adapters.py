"""Tests for adapter registry integration — T4411-T4440."""
from __future__ import annotations

import json

import pytest

from core.strategy_registry_adapters import (
    SIGNAL_GENERATORS,
    STRATEGY_DEFINITIONS,
    get_parameter_class,
    get_signal_generator,
    register_all_adapters,
)
from core.strategy_registry_core import StrategyRegistry


class TestRegisterAllAdapters:
    def test_register_all_four(self):
        reg = StrategyRegistry()
        errors = register_all_adapters(reg)
        assert errors == []
        assert reg.strategy_count() == 4
        ids = reg.list_strategies()
        assert ids == ["breakout", "mean_reversion", "momentum", "volatility_compression"]

    def test_register_subset(self):
        reg = StrategyRegistry()
        errors = register_all_adapters(reg, ["breakout", "momentum"])
        assert errors == []
        assert reg.strategy_count() == 2

    def test_register_unknown_strategy(self):
        reg = StrategyRegistry()
        errors = register_all_adapters(reg, ["nonexistent"])
        assert len(errors) == 1
        assert "unknown" in errors[0]

    def test_deterministic_order(self):
        reg = StrategyRegistry()
        register_all_adapters(reg)
        ids = reg.list_strategies()
        assert ids == sorted(ids)

    def test_registry_json_contains_all(self):
        reg = StrategyRegistry()
        register_all_adapters(reg)
        d = reg.to_dict()
        assert d["strategy_count"] == 4
        strategy_ids = [s["strategy_id"] for s in d["strategies"]]
        assert strategy_ids == sorted(strategy_ids)

    def test_safety_flags_present(self):
        reg = StrategyRegistry()
        register_all_adapters(reg)
        d = reg.to_dict()
        assert d["safety_flags"]["no_live"] is True
        assert d["safety_flags"]["no_submit"] is True
        assert d["release_hold"] == "HOLD"


class TestSignalGenerators:
    def test_all_four_generators_exist(self):
        for sid in ["breakout", "mean_reversion", "momentum", "volatility_compression"]:
            gen = get_signal_generator(sid)
            assert gen is not None, f"missing generator for {sid}"

    def test_unknown_generator(self):
        assert get_signal_generator("nonexistent") is None


class TestParameterClasses:
    def test_all_four_param_classes(self):
        for sid in ["breakout", "mean_reversion", "momentum", "volatility_compression"]:
            cls = get_parameter_class(sid)
            assert cls is not None, f"missing param class for {sid}"

    def test_unknown_param_class(self):
        assert get_parameter_class("nonexistent") is None


class TestGoldenRegistry:
    def test_golden_registry_deterministic(self, tmp_path):
        """Test that registry JSON output is deterministic."""
        reg = StrategyRegistry()
        register_all_adapters(reg)
        j1 = reg.to_json()
        j2 = reg.to_json()
        assert j1 == j2

        d = json.loads(j1)
        assert d["strategy_count"] == 4
        assert d["validation_status"] == "PASS"
        assert d["release_hold"] == "HOLD"
        assert len(d["rejected_strategies"]) == 0
