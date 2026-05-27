"""Tests for T838: Runtime governance read-only phase control report."""

import pytest

from core.runtime_governance_readonly_phase_control_report import (
    RuntimeGovernanceReadOnlyPhaseControlReport,
    build_readonly_phase_control_report,
    readonly_phase_control_report_to_dict,
    readonly_phase_control_report_to_markdown,
)
from core.runtime_governance_readonly_regression_packet import (
    build_readonly_regression_packet,
    RuntimeGovernanceReadOnlyRegressionPacket,
)
from core.runtime_governance_readonly_readiness_score import (
    RuntimeGovernanceReadOnlyReadinessScore,
)
from core.runtime_governance_readonly_blocker_summary import (
    RuntimeGovernanceReadOnlyBlockerSummary,
)


# ── helpers ──────────────────────────────────────────────────────────────


def _make_readiness_score(grade: str) -> RuntimeGovernanceReadOnlyReadinessScore:
    """Build a readiness score with given grade. Pure test helper."""
    return RuntimeGovernanceReadOnlyReadinessScore(
        score=100 if grade == "A" else 0,
        max_score=100,
        percent=100.0 if grade == "A" else 0.0,
        grade=grade,
        blockers=[],
        warnings=[],
        notes=[],
    )


def _make_blocker_summary(action: str) -> RuntimeGovernanceReadOnlyBlockerSummary:
    """Build a blocker summary with given action. Pure test helper."""
    return RuntimeGovernanceReadOnlyBlockerSummary(
        total_blockers=0,
        dangerous_permission_blockers=0,
        invariant_blockers=0,
        recommended_action=action,
        notes=[],
    )


# ── tests ────────────────────────────────────────────────────────────────


class TestDefaultDecision:
    def test_default_proceeds_to_manual_review(self):
        report = build_readonly_phase_control_report()
        assert report.final_decision == "PROCEED_TO_MANUAL_REVIEW_ONLY"

    def test_default_values(self):
        report = build_readonly_phase_control_report()
        assert report.phase == "read-only design review"
        assert report.regression_verdict == "PASS"
        assert report.readiness_grade == "A"
        assert report.blocker_action == "PROCEED"


class TestDecisionLogic:
    def test_blocker_action_block_gives_hold(self):
        packet = build_readonly_regression_packet()
        score = _make_readiness_score("A")
        blockers = _make_blocker_summary("BLOCK")
        report = build_readonly_phase_control_report(
            regression_packet=packet,
            readiness_score=score,
            blocker_summary=blockers,
        )
        assert report.final_decision == "HOLD"

    def test_readiness_grade_d_gives_review(self):
        packet = build_readonly_regression_packet()
        score = _make_readiness_score("D")
        blockers = _make_blocker_summary("PROCEED")
        report = build_readonly_phase_control_report(
            regression_packet=packet,
            readiness_score=score,
            blocker_summary=blockers,
        )
        assert report.final_decision == "REVIEW"

    def test_readiness_grade_f_gives_review(self):
        packet = build_readonly_regression_packet()
        score = _make_readiness_score("F")
        blockers = _make_blocker_summary("PROCEED")
        report = build_readonly_phase_control_report(
            regression_packet=packet,
            readiness_score=score,
            blocker_summary=blockers,
        )
        assert report.final_decision == "REVIEW"

    def test_readiness_grade_c_gives_review(self):
        packet = build_readonly_regression_packet()
        score = _make_readiness_score("C")
        blockers = _make_blocker_summary("PROCEED")
        report = build_readonly_phase_control_report(
            regression_packet=packet,
            readiness_score=score,
            blocker_summary=blockers,
        )
        assert report.final_decision == "REVIEW"

    def test_blocker_block_takes_priority_over_grade(self):
        """BLOCK should win even if grade is A."""
        packet = build_readonly_regression_packet()
        score = _make_readiness_score("A")
        blockers = _make_blocker_summary("BLOCK")
        report = build_readonly_phase_control_report(
            regression_packet=packet,
            readiness_score=score,
            blocker_summary=blockers,
        )
        assert report.final_decision == "HOLD"

    def test_grade_b_proceeds(self):
        packet = build_readonly_regression_packet()
        score = _make_readiness_score("B")
        blockers = _make_blocker_summary("PROCEED")
        report = build_readonly_phase_control_report(
            regression_packet=packet,
            readiness_score=score,
            blocker_summary=blockers,
        )
        assert report.final_decision == "PROCEED_TO_MANUAL_REVIEW_ONLY"


class TestDeterminism:
    def test_deterministic_output(self):
        a = build_readonly_phase_control_report()
        b = build_readonly_phase_control_report()
        assert a == b
        assert readonly_phase_control_report_to_dict(a) == readonly_phase_control_report_to_dict(b)
        assert readonly_phase_control_report_to_markdown(a) == readonly_phase_control_report_to_markdown(b)


class TestToDict:
    def test_has_expected_keys(self):
        d = readonly_phase_control_report_to_dict(build_readonly_phase_control_report())
        expected = {
            "phase",
            "regression_verdict",
            "readiness_grade",
            "blocker_action",
            "final_decision",
            "notes",
        }
        assert set(d.keys()) == expected


class TestToMarkdown:
    def test_contains_final_decision(self):
        md = readonly_phase_control_report_to_markdown(build_readonly_phase_control_report())
        assert "PROCEED_TO_MANUAL_REVIEW_ONLY" in md

    def test_contains_title(self):
        md = readonly_phase_control_report_to_markdown(build_readonly_phase_control_report())
        assert "Phase Control Report" in md


class TestFrozen:
    def test_dataclass_is_frozen(self):
        report = build_readonly_phase_control_report()
        with pytest.raises(AttributeError):
            report.phase = "changed"
