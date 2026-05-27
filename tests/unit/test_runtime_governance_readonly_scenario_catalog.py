"""T831 — Tests for read-only scenario catalog."""

import pytest

from core.runtime_governance_readonly_scenario_catalog import (
    RuntimeGovernanceReadOnlyScenario,
    build_readonly_scenario_catalog,
    get_readonly_scenario,
    readonly_scenario_catalog_to_dict,
    readonly_scenario_catalog_to_markdown,
)


class TestCatalogCompleteness:
    def test_all_6_scenarios_present(self):
        catalog = build_readonly_scenario_catalog()
        ids = [s.scenario_id for s in catalog]
        assert len(ids) == 6
        expected = [
            "safe_summary_read",
            "unsafe_network",
            "unsafe_write",
            "unsafe_order",
            "unsafe_secret",
            "unsafe_account_mutation",
        ]
        assert ids == expected


class TestUnsafeBlocked:
    def test_unsafe_scenarios_blocked(self):
        catalog = build_readonly_scenario_catalog()
        unsafe = [s for s in catalog if s.expected_blocked]
        assert len(unsafe) == 5
        for s in unsafe:
            assert s.expected_verdict == "BLOCKED"
            assert s.expected_blocked is True

    def test_safe_scenario_passes(self):
        s = get_readonly_scenario("safe_summary_read")
        assert s.expected_verdict == "PASS"
        assert s.expected_blocked is False


class TestLookup:
    def test_known_scenario(self):
        s = get_readonly_scenario("unsafe_network")
        assert s.scenario_id == "unsafe_network"

    def test_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown scenario_id"):
            get_readonly_scenario("does_not_exist")


class TestDeterminism:
    def test_catalog_deterministic(self):
        a = build_readonly_scenario_catalog()
        b = build_readonly_scenario_catalog()
        assert a == b

    def test_to_dict_deterministic(self):
        catalog = build_readonly_scenario_catalog()
        a = readonly_scenario_catalog_to_dict(catalog)
        b = readonly_scenario_catalog_to_dict(catalog)
        assert a == b

    def test_to_markdown_deterministic(self):
        catalog = build_readonly_scenario_catalog()
        a = readonly_scenario_catalog_to_markdown(catalog)
        b = readonly_scenario_catalog_to_markdown(catalog)
        assert a == b


class TestSerialization:
    def test_to_dict_roundtrip(self):
        catalog = build_readonly_scenario_catalog()
        dicts = readonly_scenario_catalog_to_dict(catalog)
        assert len(dicts) == 6
        assert dicts[0]["scenario_id"] == "safe_summary_read"
        assert dicts[0]["expected_blocked"] is False
        assert dicts[1]["expected_verdict"] == "BLOCKED"

    def test_to_markdown_has_header(self):
        catalog = build_readonly_scenario_catalog()
        md = readonly_scenario_catalog_to_markdown(catalog)
        assert "# Read-Only Scenario Catalog" in md
        assert "safe_summary_read" in md
        assert "unsafe_order" in md
