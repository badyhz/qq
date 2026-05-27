"""Tests for parameter search space — T4441-T4470."""
from __future__ import annotations

import pytest

from core.parameter_search_space import (
    ParameterSearchSpace,
    enumerate_parameter_sets,
    expand_search_space,
    search_space_to_dict,
)
from core.strategy_research_parameters import ParameterSchema, ParameterSpec


def _make_schema():
    return ParameterSchema(
        strategy_id="test_strat",
        parameters=(
            ParameterSpec(name="lookback", type="int", min=10, max=30, default=20),
            ParameterSpec(name="threshold", type="float", min=0.0, max=1.0, default=0.5),
        ),
    )


class TestSearchSpaceExpansion:
    def test_expands_bounded(self):
        space = expand_search_space(_make_schema(), search_budget=100)
        assert space.bounded is True
        assert space.strategy_id == "test_strat"
        assert space.expanded_combinations > 0

    def test_deterministic_order(self):
        s1 = expand_search_space(_make_schema(), search_budget=100)
        s2 = expand_search_space(_make_schema(), search_budget=100)
        assert s1.expanded_combinations == s2.expanded_combinations

    def test_preset_values_included(self):
        space = expand_search_space(
            _make_schema(),
            search_budget=100,
            preset_values={"lookback": 15},
        )
        assert space.expanded_combinations > 0


class TestParameterSetEnumeration:
    def test_enumerates_sets(self):
        param_sets, truncated = enumerate_parameter_sets(_make_schema(), search_budget=100)
        assert len(param_sets) > 0
        assert truncated is False

    def test_deterministic_ids(self):
        ps1, _ = enumerate_parameter_sets(_make_schema(), search_budget=100)
        ps2, _ = enumerate_parameter_sets(_make_schema(), search_budget=100)
        for a, b in zip(ps1, ps2):
            assert a.parameter_set_id == b.parameter_set_id
            assert a.parameters == b.parameters

    def test_budget_truncation(self):
        # Create schema with many combos
        schema = ParameterSchema(
            strategy_id="big",
            parameters=(
                ParameterSpec(name="a", type="int", min=1, max=20),
                ParameterSpec(name="b", type="int", min=1, max=20),
            ),
        )
        ps, truncated = enumerate_parameter_sets(schema, search_budget=5)
        assert len(ps) <= 5
        assert truncated is True

    def test_no_truncation_when_budget_sufficient(self):
        ps, truncated = enumerate_parameter_sets(_make_schema(), search_budget=1000)
        assert truncated is False

    def test_release_hold(self):
        ps, _ = enumerate_parameter_sets(_make_schema(), search_budget=100)
        for p in ps:
            assert p.release_hold == "HOLD"

    def test_stable_parameter_set_ids(self):
        ps, _ = enumerate_parameter_sets(_make_schema(), search_budget=100)
        for p in ps:
            assert p.parameter_set_id.startswith("test_strat_ps_")

    def test_enum_parameter(self):
        schema = ParameterSchema(
            strategy_id="enum_test",
            parameters=(
                ParameterSpec(name="mode", type="enum", values=("fast", "slow", "medium")),
            ),
        )
        ps, _ = enumerate_parameter_sets(schema, search_budget=100)
        assert len(ps) == 3
        modes = [p.parameters["mode"] for p in ps]
        assert modes == ["fast", "medium", "slow"]


class TestSearchSpaceDict:
    def test_to_dict(self):
        space = expand_search_space(_make_schema(), search_budget=100)
        d = search_space_to_dict(space)
        assert d["search_space_id"] == "search_space_test_strat"
        assert d["bounded"] is True
        assert d["deterministic_order"] is True
