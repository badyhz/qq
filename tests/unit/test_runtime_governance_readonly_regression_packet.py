"""Tests for T835: Runtime governance read-only regression packet."""

import pytest

from core.runtime_governance_readonly_regression_packet import (
    RuntimeGovernanceReadOnlyRegressionPacket,
    build_readonly_regression_packet,
    readonly_regression_packet_to_dict,
    readonly_regression_packet_to_markdown,
)


class TestBuildDefaults:
    def test_default_packet_is_pass(self):
        p = build_readonly_regression_packet()
        assert p.final_verdict == "PASS"
        assert p.scenario_fail_count == 0
        assert p.side_effect_verdict == "PASS"
        assert p.manifest_verdict == "PASS"


class TestVerdictLogic:
    def test_scenario_fail_gives_fail(self):
        p = build_readonly_regression_packet(scenario_fail_count=1)
        assert p.final_verdict == "FAIL"

    def test_side_effect_verdict_not_pass_gives_fail(self):
        p = build_readonly_regression_packet(side_effect_verdict="FAIL")
        assert p.final_verdict == "FAIL"

    def test_manifest_verdict_not_pass_gives_fail(self):
        p = build_readonly_regression_packet(manifest_verdict="FAIL")
        assert p.final_verdict == "FAIL"


class TestDeterminism:
    def test_deterministic_output(self):
        a = build_readonly_regression_packet()
        b = build_readonly_regression_packet()
        assert a == b
        assert readonly_regression_packet_to_dict(a) == readonly_regression_packet_to_dict(b)
        assert readonly_regression_packet_to_markdown(a) == readonly_regression_packet_to_markdown(b)


class TestToDict:
    def test_has_expected_keys(self):
        d = readonly_regression_packet_to_dict(build_readonly_regression_packet())
        expected = {
            "title",
            "scenario_count",
            "scenario_pass_count",
            "scenario_fail_count",
            "side_effect_verdict",
            "manifest_verdict",
            "final_verdict",
            "notes",
        }
        assert set(d.keys()) == expected


class TestToMarkdown:
    def test_contains_title(self):
        md = readonly_regression_packet_to_markdown(build_readonly_regression_packet())
        assert "Read-Only Regression Packet" in md

    def test_contains_final_verdict(self):
        md = readonly_regression_packet_to_markdown(build_readonly_regression_packet())
        assert "PASS" in md


class TestFrozen:
    def test_dataclass_is_frozen(self):
        p = build_readonly_regression_packet()
        with pytest.raises(AttributeError):
            p.title = "changed"
