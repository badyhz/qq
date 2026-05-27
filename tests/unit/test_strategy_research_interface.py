"""Tests for strategy research interface — T4201-T4230."""
from __future__ import annotations

import pytest

from core.strategy_research_interface import (
    ALLOWED_SIGNAL_SIDES,
    ALLOWED_STRATEGY_FAMILIES,
    DEFAULT_SAFETY_FLAGS,
    REQUIRED_BAR_FIELDS,
    REQUIRED_SAFETY_NOTES,
    StrategyDefinition,
    StrategySignal,
    StrategyValidationError,
    is_strategy_safe,
    validate_adapter_safety,
    validate_strategy_definition,
    validate_strategy_signal,
)


# --- Helpers ---

def _make_valid_definition(**overrides) -> StrategyDefinition:
    """Create a valid strategy definition for testing."""
    defaults = dict(
        strategy_id="test_breakout",
        strategy_family="breakout",
        display_name="Test Breakout",
        description="A test breakout strategy.",
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


def _make_valid_signal(**overrides) -> StrategySignal:
    """Create a valid strategy signal for testing."""
    defaults = dict(
        signal_id="signal_001",
        strategy_id="test_breakout",
        symbol="BTCUSDT",
        timeframe="5m",
        timestamp=1700000000.0,
        side="LONG",
        entry_reference_price=50000.0,
        confidence=0.75,
        metadata={},
    )
    defaults.update(overrides)
    return StrategySignal(**defaults)


# --- Strategy Definition Validation ---

class TestStrategyDefinitionValidation:
    def test_valid_definition_passes(self):
        defn = _make_valid_definition()
        errors = validate_strategy_definition(defn)
        assert errors == []

    def test_missing_strategy_id(self):
        defn = _make_valid_definition(strategy_id="")
        errors = validate_strategy_definition(defn)
        assert any("strategy_id" in e for e in errors)

    def test_invalid_strategy_family(self):
        defn = _make_valid_definition(strategy_family="invalid_family")
        errors = validate_strategy_definition(defn)
        assert any("strategy_family" in e for e in errors)

    def test_allowed_families_all_valid(self):
        for family in ALLOWED_STRATEGY_FAMILIES:
            defn = _make_valid_definition(strategy_family=family)
            errors = validate_strategy_definition(defn)
            family_errors = [e for e in errors if "strategy_family" in e]
            assert family_errors == [], f"family {family!r} rejected: {family_errors}"

    def test_missing_display_name(self):
        defn = _make_valid_definition(display_name="")
        errors = validate_strategy_definition(defn)
        assert any("display_name" in e for e in errors)

    def test_missing_description(self):
        defn = _make_valid_definition(description="")
        errors = validate_strategy_definition(defn)
        assert any("description" in e for e in errors)

    def test_missing_parameter_schema(self):
        defn = _make_valid_definition(parameter_schema={})
        errors = validate_strategy_definition(defn)
        assert any("parameter_schema" in e for e in errors)

    def test_missing_required_bar_field(self):
        defn = _make_valid_definition(required_bar_fields=["timestamp", "open", "high", "low", "close"])
        errors = validate_strategy_definition(defn)
        assert any("volume" in e for e in errors)

    def test_missing_safety_notes(self):
        defn = _make_valid_definition(safety_notes=[])
        errors = validate_strategy_definition(defn)
        assert any("safety_notes" in e for e in errors)

    def test_incomplete_safety_notes(self):
        defn = _make_valid_definition(safety_notes=["local pure function", "offline only"])
        errors = validate_strategy_definition(defn)
        assert any("safety_note" in e for e in errors)

    def test_not_deterministic_rejected(self):
        defn = _make_valid_definition(deterministic=False)
        errors = validate_strategy_definition(defn)
        assert any("deterministic" in e for e in errors)

    def test_not_local_only_rejected(self):
        defn = _make_valid_definition(local_only=False)
        errors = validate_strategy_definition(defn)
        assert any("local_only" in e for e in errors)

    def test_not_no_network_rejected(self):
        defn = _make_valid_definition(no_network=False)
        errors = validate_strategy_definition(defn)
        assert any("no_network" in e for e in errors)

    def test_not_no_exchange_rejected(self):
        defn = _make_valid_definition(no_exchange=False)
        errors = validate_strategy_definition(defn)
        assert any("no_exchange" in e for e in errors)

    def test_wrong_safety_flag_rejected(self):
        flags = dict(DEFAULT_SAFETY_FLAGS)
        flags["no_live"] = False
        defn = _make_valid_definition(safety_flags=flags)
        errors = validate_strategy_definition(defn)
        assert any("no_live" in e for e in errors)


# --- Strategy Signal Validation ---

class TestStrategySignalValidation:
    def test_valid_signal_passes(self):
        sig = _make_valid_signal()
        errors = validate_strategy_signal(sig)
        assert errors == []

    def test_missing_signal_id(self):
        sig = _make_valid_signal(signal_id="")
        errors = validate_strategy_signal(sig)
        assert any("signal_id" in e for e in errors)

    def test_missing_strategy_id(self):
        sig = _make_valid_signal(strategy_id="")
        errors = validate_strategy_signal(sig)
        assert any("strategy_id" in e for e in errors)

    def test_missing_symbol(self):
        sig = _make_valid_signal(symbol="")
        errors = validate_strategy_signal(sig)
        assert any("symbol" in e for e in errors)

    def test_invalid_side(self):
        sig = _make_valid_signal(side="BUY")
        errors = validate_strategy_signal(sig)
        assert any("side" in e for e in errors)

    def test_allowed_sides(self):
        for side in ALLOWED_SIGNAL_SIDES:
            sig = _make_valid_signal(side=side)
            errors = validate_strategy_signal(sig)
            side_errors = [e for e in errors if "side" in e]
            assert side_errors == [], f"side {side!r} rejected"

    def test_negative_price_rejected(self):
        sig = _make_valid_signal(entry_reference_price=-1.0)
        errors = validate_strategy_signal(sig)
        assert any("entry_reference_price" in e for e in errors)

    def test_zero_price_rejected(self):
        sig = _make_valid_signal(entry_reference_price=0.0)
        errors = validate_strategy_signal(sig)
        assert any("entry_reference_price" in e for e in errors)

    def test_confidence_out_of_range_rejected(self):
        sig = _make_valid_signal(confidence=1.5)
        errors = validate_strategy_signal(sig)
        assert any("confidence" in e for e in errors)

    def test_negative_confidence_rejected(self):
        sig = _make_valid_signal(confidence=-0.1)
        errors = validate_strategy_signal(sig)
        assert any("confidence" in e for e in errors)


# --- Adapter Safety ---

class TestAdapterSafety:
    def test_clean_imports_pass(self):
        errors = validate_adapter_safety(["math", "statistics", "json", "dataclasses"])
        assert errors == []

    def test_forbidden_import_detected(self):
        errors = validate_adapter_safety(["core.live_runner"])
        assert len(errors) == 1
        assert "live_runner" in errors[0]

    def test_exchange_import_detected(self):
        errors = validate_adapter_safety(["core.binance_connector"])
        assert any("binance" in e for e in errors)

    def test_testnet_import_detected(self):
        errors = validate_adapter_safety(["scripts.run_testnet_order_smoke"])
        assert any("testnet" in e for e in errors)


# --- is_strategy_safe ---

class TestIsStrategySafe:
    def test_valid_strategy_is_safe(self):
        defn = _make_valid_definition()
        assert is_strategy_safe(defn) is True

    def test_unsafe_strategy_is_not_safe(self):
        defn = _make_valid_definition(no_network=False)
        assert is_strategy_safe(defn) is False


# --- Determinism ---

class TestDeterminism:
    def test_definition_frozen(self):
        defn = _make_valid_definition()
        with pytest.raises(AttributeError):
            defn.strategy_id = "changed"

    def test_signal_frozen(self):
        sig = _make_valid_signal()
        with pytest.raises(AttributeError):
            sig.side = "SHORT"
