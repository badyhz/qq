"""Tests for strategy research parameters — T4231-T4260."""
from __future__ import annotations

import pytest

from core.strategy_research_parameters import (
    NamedPreset,
    ParameterSchema,
    ParameterSet,
    ParameterSpec,
    generate_default_presets,
    make_parameter_set_id,
    parameter_schema_to_dict,
    parameter_set_to_dict,
    parameter_spec_to_dict,
    validate_parameter_schema,
    validate_parameter_spec,
)


# --- ParameterSpec ---

class TestParameterSpec:
    def test_valid_int_parameter(self):
        spec = ParameterSpec(name="lookback", type="int", min=5, max=100, default=20)
        assert spec.name == "lookback"
        assert spec.type == "int"

    def test_valid_float_parameter(self):
        spec = ParameterSpec(name="threshold", type="float", min=0.0, max=1.0, default=0.5)
        assert spec.type == "float"

    def test_valid_enum_parameter(self):
        spec = ParameterSpec(name="mode", type="enum", values=("fast", "slow", "medium"))
        assert spec.type == "enum"

    def test_missing_name_raises(self):
        with pytest.raises(ValueError, match="name"):
            ParameterSpec(name="", type="int", min=0, max=10)

    def test_invalid_type_raises(self):
        with pytest.raises(ValueError, match="type"):
            ParameterSpec(name="x", type="string", min=0, max=10)

    def test_enum_without_values_raises(self):
        with pytest.raises(ValueError, match="values"):
            ParameterSpec(name="mode", type="enum")

    def test_numeric_without_min_raises(self):
        with pytest.raises(ValueError, match="min"):
            ParameterSpec(name="x", type="int", min=None, max=10)

    def test_numeric_without_max_raises(self):
        with pytest.raises(ValueError, match="max"):
            ParameterSpec(name="x", type="int", min=0, max=None)

    def test_min_greater_than_max_raises(self):
        with pytest.raises(ValueError, match="min"):
            ParameterSpec(name="x", type="int", min=100, max=5)

    def test_frozen(self):
        spec = ParameterSpec(name="x", type="int", min=0, max=10)
        with pytest.raises(AttributeError):
            spec.name = "changed"


# --- ParameterSchema ---

class TestParameterSchema:
    def _make_schema(self, **overrides):
        defaults = dict(
            strategy_id="test_strat",
            parameters=(
                ParameterSpec(name="lookback", type="int", min=5, max=100, default=20),
                ParameterSpec(name="threshold", type="float", min=0.0, max=1.0, default=0.5),
            ),
            bounded=True,
            deterministic_order=True,
        )
        defaults.update(overrides)
        return ParameterSchema(**defaults)

    def test_valid_schema_passes(self):
        schema = self._make_schema()
        errors = validate_parameter_schema(schema)
        assert errors == []

    def test_missing_strategy_id(self):
        schema = self._make_schema(strategy_id="")
        errors = validate_parameter_schema(schema)
        assert any("strategy_id" in e for e in errors)

    def test_empty_parameters_rejected(self):
        schema = self._make_schema(parameters=())
        errors = validate_parameter_schema(schema)
        assert any("non-empty" in e for e in errors)

    def test_unbounded_rejected(self):
        schema = self._make_schema(bounded=False)
        errors = validate_parameter_schema(schema)
        assert any("bounded" in e for e in errors)

    def test_non_deterministic_rejected(self):
        schema = self._make_schema(deterministic_order=False)
        errors = validate_parameter_schema(schema)
        assert any("deterministic" in e for e in errors)

    def test_frozen(self):
        schema = self._make_schema()
        with pytest.raises(AttributeError):
            schema.strategy_id = "changed"


# --- Preset generation ---

class TestPresetGeneration:
    def _make_schema(self):
        return ParameterSchema(
            strategy_id="test",
            parameters=(
                ParameterSpec(name="lookback", type="int", min=10, max=40),
                ParameterSpec(name="threshold", type="float", min=0.0, max=1.0),
                ParameterSpec(name="mode", type="enum", values=("fast", "slow", "medium")),
            ),
        )

    def test_three_presets_generated(self):
        presets = generate_default_presets(self._make_schema())
        assert len(presets) == 3
        names = [p.name for p in presets]
        assert names == ["conservative", "balanced", "aggressive"]

    def test_conservative_uses_min(self):
        presets = generate_default_presets(self._make_schema())
        c = presets[0]
        assert c.parameter_values["lookback"] == 10
        assert c.parameter_values["threshold"] == 0.0
        assert c.parameter_values["mode"] == "fast"

    def test_balanced_uses_mid(self):
        presets = generate_default_presets(self._make_schema())
        b = presets[1]
        assert b.parameter_values["lookback"] == 25
        assert b.parameter_values["threshold"] == 0.5
        assert b.parameter_values["mode"] == "slow"

    def test_aggressive_uses_max(self):
        presets = generate_default_presets(self._make_schema())
        a = presets[2]
        assert a.parameter_values["lookback"] == 40
        assert a.parameter_values["threshold"] == 1.0
        assert a.parameter_values["mode"] == "medium"


# --- Parameter set id ---

class TestParameterSetId:
    def test_deterministic(self):
        params = {"lookback": 20, "threshold": 0.5}
        id1 = make_parameter_set_id("breakout", params)
        id2 = make_parameter_set_id("breakout", params)
        assert id1 == id2

    def test_different_params_different_id(self):
        id1 = make_parameter_set_id("breakout", {"lookback": 20})
        id2 = make_parameter_set_id("breakout", {"lookback": 40})
        assert id1 != id2

    def test_different_strategy_different_id(self):
        params = {"lookback": 20}
        id1 = make_parameter_set_id("breakout", params)
        id2 = make_parameter_set_id("momentum", params)
        assert id1 != id2

    def test_format(self):
        psid = make_parameter_set_id("breakout", {"x": 1})
        assert psid.startswith("breakout_ps_")
        assert len(psid) == len("breakout_ps_") + 12


# --- Serialization ---

class TestSerialization:
    def test_spec_to_dict_int(self):
        spec = ParameterSpec(name="lookback", type="int", min=5, max=100, default=20)
        d = parameter_spec_to_dict(spec)
        assert d["name"] == "lookback"
        assert d["type"] == "int"
        assert d["min"] == 5
        assert d["max"] == 100
        assert d["default"] == 20

    def test_spec_to_dict_enum(self):
        spec = ParameterSpec(name="mode", type="enum", values=("fast", "slow"))
        d = parameter_spec_to_dict(spec)
        assert d["values"] == ["fast", "slow"]
        assert "min" not in d

    def test_schema_to_dict(self):
        schema = ParameterSchema(
            strategy_id="test",
            parameters=(ParameterSpec(name="x", type="int", min=0, max=10),),
        )
        d = parameter_schema_to_dict(schema)
        assert d["strategy_id"] == "test"
        assert d["bounded"] is True
        assert len(d["parameters"]) == 1

    def test_set_to_dict(self):
        ps = ParameterSet(
            parameter_set_id="test_ps_001",
            strategy_id="test",
            preset_name="balanced",
            parameters={"x": 5},
        )
        d = parameter_set_to_dict(ps)
        assert d["parameter_set_id"] == "test_ps_001"
        assert d["release_hold"] == "HOLD"
