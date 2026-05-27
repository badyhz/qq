"""Tests for runtime governance scenario catalog."""

from __future__ import annotations

import pytest

from core.runtime_governance_contract import validate_runtime_governance_input
from core.governance_failure_taxonomy import FailureCategory
from core.runtime_governance_scenario_catalog import (
    RuntimeGovernanceScenario,
    build_runtime_governance_scenario_catalog,
    get_runtime_governance_scenario,
    scenario_catalog_to_dict,
    scenario_catalog_to_markdown,
)


# ── fixtures ──────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def catalog() -> list[RuntimeGovernanceScenario]:
    return build_runtime_governance_scenario_catalog()


# ── tests ─────────────────────────────────────────────────────────────


def test_catalog_has_8_scenarios(catalog: list[RuntimeGovernanceScenario]) -> None:
    assert len(catalog) == 8


def test_lookup_by_id_works() -> None:
    s = get_runtime_governance_scenario("valid_shadow")
    assert s.scenario_id == "valid_shadow"
    assert s.expected_verdict == "PASS"


def test_unknown_id_raises_value_error() -> None:
    with pytest.raises(ValueError, match="unknown scenario_id"):
        get_runtime_governance_scenario("does_not_exist")


def test_each_scenario_expected_verdict_matches_validate(
    catalog: list[RuntimeGovernanceScenario],
) -> None:
    """Verify expected_verdict aligns with actual validate_runtime_governance_input."""
    for s in catalog:
        result = validate_runtime_governance_input(s.input)
        if s.expected_verdict == "PASS":
            assert result.ok, f"{s.scenario_id}: expected PASS but got failures"
        elif s.expected_verdict == "FAIL":
            assert not result.ok, f"{s.scenario_id}: expected FAIL but got ok"
            categories = {f.category for f in result.failures}
            assert FailureCategory.VALIDATION_FAILURE in categories, (
                f"{s.scenario_id}: expected VALIDATION_FAILURE"
            )
        elif s.expected_verdict == "BLOCKED":
            assert not result.ok, f"{s.scenario_id}: expected BLOCKED but got ok"
            categories = {f.category for f in result.failures}
            assert FailureCategory.POLICY_BLOCK in categories, (
                f"{s.scenario_id}: expected POLICY_BLOCK"
            )
        else:
            raise AssertionError(f"unexpected verdict: {s.expected_verdict}")


def test_dict_serialization_deterministic(
    catalog: list[RuntimeGovernanceScenario],
) -> None:
    d1 = scenario_catalog_to_dict(catalog)
    d2 = scenario_catalog_to_dict(catalog)
    assert d1 == d2


def test_markdown_deterministic(
    catalog: list[RuntimeGovernanceScenario],
) -> None:
    m1 = scenario_catalog_to_markdown(catalog)
    m2 = scenario_catalog_to_markdown(catalog)
    assert m1 == m2


def test_repeated_calls_identical() -> None:
    c1 = build_runtime_governance_scenario_catalog()
    c2 = build_runtime_governance_scenario_catalog()
    assert len(c1) == len(c2)
    for a, b in zip(c1, c2):
        assert a.scenario_id == b.scenario_id
        assert a.expected_verdict == b.expected_verdict
        assert a.tags == b.tags
        assert a.input == b.input


def test_markdown_contains_table_header(
    catalog: list[RuntimeGovernanceScenario],
) -> None:
    md = scenario_catalog_to_markdown(catalog)
    assert "| scenario_id |" in md
    assert "|---|---|" in md
