"""T836 — Tests for read-only readiness score."""

import pytest

from core.runtime_governance_readonly_readiness_score import (
    RuntimeGovernanceReadOnlyReadinessScore,
    compute_readonly_readiness_score,
    readonly_readiness_score_to_dict,
    readonly_readiness_score_to_markdown,
)
from core.runtime_governance_readonly_regression_packet import (
    RuntimeGovernanceReadOnlyRegressionPacket,
    build_readonly_regression_packet,
)


# ── helpers ────────────────────────────────────────────────────────────


def _perfect_packet():
    return build_readonly_regression_packet()


# ── tests ──────────────────────────────────────────────────────────────


class TestPerfectPacket:
    def test_score_is_100(self):
        score = compute_readonly_readiness_score(_perfect_packet())
        assert score.score == 100

    def test_grade_is_a(self):
        score = compute_readonly_readiness_score(_perfect_packet())
        assert score.grade == "A"

    def test_blockers_empty(self):
        score = compute_readonly_readiness_score(_perfect_packet())
        assert score.blockers == []

    def test_warnings_empty(self):
        score = compute_readonly_readiness_score(_perfect_packet())
        assert score.warnings == []

    def test_percent_is_100(self):
        score = compute_readonly_readiness_score(_perfect_packet())
        assert score.percent == 100.0

    def test_max_score_is_100(self):
        score = compute_readonly_readiness_score(_perfect_packet())
        assert score.max_score == 100


class TestScenarioFail:
    def test_lower_score(self):
        pkt = build_readonly_regression_packet(
            scenario_fail_count=1,
            scenario_pass_count=5,
        )
        score = compute_readonly_readiness_score(pkt)
        assert score.score < 100

    def test_not_grade_a(self):
        pkt = build_readonly_regression_packet(
            scenario_fail_count=1,
            scenario_pass_count=5,
        )
        score = compute_readonly_readiness_score(pkt)
        assert score.grade != "A"

    def test_score_is_80(self):
        pkt = build_readonly_regression_packet(
            scenario_fail_count=1,
            scenario_pass_count=5,
        )
        score = compute_readonly_readiness_score(pkt)
        assert score.score == 80

    def test_has_warning(self):
        pkt = build_readonly_regression_packet(
            scenario_fail_count=1,
            scenario_pass_count=5,
        )
        score = compute_readonly_readiness_score(pkt)
        assert any("scenario_fail_count" in w for w in score.warnings)


class TestSideEffectFail:
    def test_lower_score(self):
        pkt = build_readonly_regression_packet(side_effect_verdict="FAIL")
        score = compute_readonly_readiness_score(pkt)
        assert score.score < 100

    def test_score_is_75(self):
        pkt = build_readonly_regression_packet(side_effect_verdict="FAIL")
        score = compute_readonly_readiness_score(pkt)
        assert score.score == 75

    def test_has_warning(self):
        pkt = build_readonly_regression_packet(side_effect_verdict="FAIL")
        score = compute_readonly_readiness_score(pkt)
        assert any("side_effect_verdict" in w for w in score.warnings)


class TestManifestFail:
    """Manifest fail with final_verdict=PASS (no cap) — tests penalty isolation."""

    def _pkt(self):
        # Construct directly so final_verdict stays PASS despite manifest FAIL
        return RuntimeGovernanceReadOnlyRegressionPacket(
            title="manifest-fail",
            scenario_count=6,
            scenario_pass_count=6,
            scenario_fail_count=0,
            side_effect_verdict="PASS",
            manifest_verdict="FAIL",
            final_verdict="PASS",
        )

    def test_lower_score(self):
        score = compute_readonly_readiness_score(self._pkt())
        assert score.score < 100

    def test_score_is_80(self):
        score = compute_readonly_readiness_score(self._pkt())
        assert score.score == 80

    def test_grade_is_b(self):
        score = compute_readonly_readiness_score(self._pkt())
        assert score.grade == "B"

    def test_has_warning(self):
        score = compute_readonly_readiness_score(self._pkt())
        assert any("manifest_verdict" in w for w in score.warnings)


class TestFinalVerdictFail:
    def test_grade_cap_at_f(self):
        pkt = build_readonly_regression_packet(
            scenario_fail_count=0,
            side_effect_verdict="PASS",
            manifest_verdict="PASS",
        )
        # Force final_verdict to FAIL by passing a fail scenario
        pkt_fail = build_readonly_regression_packet(
            scenario_fail_count=1,
            scenario_pass_count=5,
            side_effect_verdict="FAIL",
            manifest_verdict="FAIL",
        )
        score = compute_readonly_readiness_score(pkt_fail)
        assert score.grade == "F"
        assert any("final_verdict" in b for b in score.blockers)


class TestDeterministic:
    def test_same_input_same_output(self):
        pkt = _perfect_packet()
        s1 = compute_readonly_readiness_score(pkt)
        s2 = compute_readonly_readiness_score(pkt)
        assert s1 == s2

    def test_repeated_calls(self):
        pkt = build_readonly_regression_packet(
            scenario_fail_count=2,
            scenario_pass_count=4,
            side_effect_verdict="FAIL",
        )
        results = [compute_readonly_readiness_score(pkt) for _ in range(10)]
        assert all(r == results[0] for r in results)


class TestToDict:
    def test_expected_keys(self):
        score = compute_readonly_readiness_score(_perfect_packet())
        d = readonly_readiness_score_to_dict(score)
        expected = {"score", "max_score", "percent", "grade", "blockers", "warnings", "notes"}
        assert set(d.keys()) == expected

    def test_values_match(self):
        score = compute_readonly_readiness_score(_perfect_packet())
        d = readonly_readiness_score_to_dict(score)
        assert d["score"] == 100
        assert d["grade"] == "A"
        assert d["percent"] == 100.0
        assert d["blockers"] == []
        assert d["warnings"] == []


class TestToMarkdown:
    def test_contains_grade(self):
        score = compute_readonly_readiness_score(_perfect_packet())
        md = readonly_readiness_score_to_markdown(score)
        assert "**Grade:** A" in md

    def test_contains_score(self):
        score = compute_readonly_readiness_score(_perfect_packet())
        md = readonly_readiness_score_to_markdown(score)
        assert "**Score:** 100/100" in md

    def test_contains_warnings_when_present(self):
        pkt = build_readonly_regression_packet(
            scenario_fail_count=1,
            scenario_pass_count=5,
        )
        score = compute_readonly_readiness_score(pkt)
        md = readonly_readiness_score_to_markdown(score)
        assert "## Warnings" in md

    def test_contains_blockers_when_present(self):
        pkt = build_readonly_regression_packet(
            scenario_fail_count=1,
            scenario_pass_count=5,
            side_effect_verdict="FAIL",
            manifest_verdict="FAIL",
        )
        score = compute_readonly_readiness_score(pkt)
        md = readonly_readiness_score_to_markdown(score)
        assert "## Blockers" in md
