"""Tests for runtime_governance_phase_control_report module.

Deterministic. No I/O. No network. No random. No timestamps.
"""

from __future__ import annotations

import pytest

from core.runtime_governance_phase_control_report import (
    RuntimeGovernancePhaseControlReport,
    build_runtime_governance_phase_control_report,
    phase_control_report_to_dict,
    phase_control_report_to_markdown,
)
from core.runtime_governance_regression_packet import (
    build_runtime_governance_regression_packet,
)
from core.runtime_governance_readiness_score import (
    compute_runtime_governance_readiness_score,
)
from core.runtime_governance_blocker_summary import (
    RuntimeGovernanceBlocker,
    summarize_runtime_governance_blockers,
)
from core.runtime_governance_no_submit_evidence_packet import (
    RuntimeGovernanceNoSubmitEvidence,
    build_runtime_governance_no_submit_evidence_packet,
)


class TestDefaultDecision:
    """Default (all-pass) report should be PROCEED_TO_MANUAL_SCOPE_ONLY."""

    def test_default_decision_proceed_or_review(self) -> None:
        report = build_runtime_governance_phase_control_report()
        assert report.final_decision in ("PROCEED_TO_MANUAL_SCOPE_ONLY", "REVIEW")

    def test_default_phase_is_pre_live_audit(self) -> None:
        report = build_runtime_governance_phase_control_report()
        assert report.phase == "pre-live audit"

    def test_default_regression_verdict_pass(self) -> None:
        report = build_runtime_governance_phase_control_report()
        assert report.regression_verdict == "PASS"

    def test_default_blocker_action_proceed(self) -> None:
        report = build_runtime_governance_phase_control_report()
        assert report.blocker_action == "PROCEED"

    def test_default_no_submit_verdict_pass(self) -> None:
        report = build_runtime_governance_phase_control_report()
        assert report.no_submit_verdict == "PASS"


class TestDecisionLogic:
    """Verify decision logic priorities."""

    def test_hold_when_blocker_is_block(self) -> None:
        blockers = summarize_runtime_governance_blockers(
            blockers=[RuntimeGovernanceBlocker(
                blocker_id="b1", action="BLOCK", message="test blocker", severity="critical",
            )],
        )
        report = build_runtime_governance_phase_control_report(blocker_summary=blockers)
        assert report.final_decision == "HOLD"

    def test_hold_when_no_submit_not_pass(self) -> None:
        no_submit = build_runtime_governance_no_submit_evidence_packet(
            evidence=[RuntimeGovernanceNoSubmitEvidence(
                component="e1:submit detected",
                no_submit=False,
                no_network=True,
                deterministic=True,
                message="submit detected",
            )],
        )
        report = build_runtime_governance_phase_control_report(no_submit_evidence=no_submit)
        assert report.final_decision == "HOLD"

    def test_review_when_readiness_below_b(self) -> None:
        # build a regression packet that yields low readiness (many fails)
        reg = build_runtime_governance_regression_packet(
            scenario_count=10,
            scenario_pass_count=0,
            scenario_fail_count=10,
            final_verdict="FAIL",
            invariant_summary={"errors": 5, "warnings": 0},
            manifest_summary={"verdict": "FAIL"},
        )
        readiness = compute_runtime_governance_readiness_score(reg)
        assert readiness.grade in ("C", "D", "F"), f"expected below B, got {readiness.grade}"
        report = build_runtime_governance_phase_control_report(
            regression_packet=reg,
            readiness_score=readiness,
        )
        assert report.final_decision == "REVIEW"

    def test_proceed_when_all_pass_and_grade_b_or_above(self) -> None:
        reg = build_runtime_governance_regression_packet(
            scenario_count=10,
            scenario_pass_count=10,
            scenario_fail_count=0,
            final_verdict="PASS",
            invariant_summary={"errors": 0, "warnings": 0},
            manifest_summary={"verdict": "PASS"},
        )
        readiness = compute_runtime_governance_readiness_score(reg)
        assert readiness.grade in ("A", "B"), f"expected B or above, got {readiness.grade}"
        report = build_runtime_governance_phase_control_report(
            regression_packet=reg,
            readiness_score=readiness,
        )
        assert report.final_decision == "PROCEED_TO_MANUAL_SCOPE_ONLY"

    def test_blocker_takes_priority_over_no_submit(self) -> None:
        blockers = summarize_runtime_governance_blockers(
            blockers=[RuntimeGovernanceBlocker(
                blocker_id="b1", action="BLOCK", message="test", severity="critical",
            )],
        )
        no_submit = build_runtime_governance_no_submit_evidence_packet(
            evidence=[RuntimeGovernanceNoSubmitEvidence(
                component="e1:test",
                no_submit=False,
                no_network=True,
                deterministic=True,
                message="test",
            )],
        )
        report = build_runtime_governance_phase_control_report(
            blocker_summary=blockers,
            no_submit_evidence=no_submit,
        )
        assert report.final_decision == "HOLD"
        assert "blocker action is BLOCK" in " ".join(report.notes)


class TestNeverLiveTrading:
    """Report must never mention 'live trading' in any output."""

    def test_markdown_no_live_trading(self) -> None:
        report = build_runtime_governance_phase_control_report()
        md = phase_control_report_to_markdown(report)
        assert "live trading" not in md.lower()

    def test_dict_no_live_trading(self) -> None:
        report = build_runtime_governance_phase_control_report()
        d = phase_control_report_to_dict(report)
        for v in d.values():
            if isinstance(v, str):
                assert "live trading" not in v.lower()

    def test_notes_no_live_trading(self) -> None:
        report = build_runtime_governance_phase_control_report()
        for note in report.notes:
            assert "live trading" not in note.lower()


class TestManualScope:
    """Report must contain 'manual scope' in output."""

    def test_markdown_contains_manual_scope(self) -> None:
        report = build_runtime_governance_phase_control_report()
        md = phase_control_report_to_markdown(report)
        assert "manual scope" in md.lower()

    def test_dict_contains_manual_scope(self) -> None:
        report = build_runtime_governance_phase_control_report()
        d = phase_control_report_to_dict(report)
        decision_lower = d["final_decision"].lower()
        assert "manual" in decision_lower and "scope" in decision_lower


class TestMarkdownDeterministic:
    """Markdown output must be deterministic (no timestamps, no random)."""

    def test_markdown_identical_on_repeat(self) -> None:
        report = build_runtime_governance_phase_control_report()
        md1 = phase_control_report_to_markdown(report)
        md2 = phase_control_report_to_markdown(report)
        assert md1 == md2

    def test_markdown_header_present(self) -> None:
        report = build_runtime_governance_phase_control_report()
        md = phase_control_report_to_markdown(report)
        assert md.startswith("# Runtime Governance Phase Control Report")


class TestDictSerialization:
    """Dict serialization round-trips correctly."""

    def test_dict_keys(self) -> None:
        report = build_runtime_governance_phase_control_report()
        d = phase_control_report_to_dict(report)
        expected_keys = {
            "phase", "regression_verdict", "readiness_grade",
            "blocker_action", "no_submit_verdict", "final_decision", "notes",
        }
        assert set(d.keys()) == expected_keys

    def test_dict_values_match_report(self) -> None:
        report = build_runtime_governance_phase_control_report()
        d = phase_control_report_to_dict(report)
        assert d["phase"] == report.phase
        assert d["regression_verdict"] == report.regression_verdict
        assert d["readiness_grade"] == report.readiness_grade
        assert d["blocker_action"] == report.blocker_action
        assert d["no_submit_verdict"] == report.no_submit_verdict
        assert d["final_decision"] == report.final_decision
        assert d["notes"] == list(report.notes)


class TestImmutable:
    """Report must be frozen dataclass."""

    def test_cannot_mutate(self) -> None:
        report = build_runtime_governance_phase_control_report()
        with pytest.raises(AttributeError):
            report.final_decision = "HOLD"  # type: ignore[misc]
