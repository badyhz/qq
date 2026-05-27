"""T1466 - Tests for HoldDecisionReport, generator, and renderer."""
from __future__ import annotations

import pytest

from core.hold_decision_report import HoldDecisionReport
from core.hold_decision_report_generator import generate_hold_decision_report
from core.hold_decision_report_renderer import (
    render_hold_decision_report_md,
    render_hold_status_md,
    render_human_decision_md,
)


# --- Frozen dataclass tests ---

def test_hold_decision_report_frozen() -> None:
    report = HoldDecisionReport(
        report_id="r1",
        file_path="a.py",
        risk_class="HIGH",
        current_hold_status="HOLD",
        readiness_score=0.0,
        unlock_recommendation="HOLD",
        human_decision="PENDING",
        decision_rationale="",
        required_evidence=("e1",),
    )
    with pytest.raises(AttributeError):
        report.report_id = "changed"  # type: ignore[misc]


def test_hold_decision_report_fields() -> None:
    report = HoldDecisionReport(
        report_id="r1",
        file_path="a.py",
        risk_class="HIGH",
        current_hold_status="HOLD",
        readiness_score=0.0,
        unlock_recommendation="HOLD",
        human_decision="PENDING",
        decision_rationale="",
        required_evidence=("e1", "e2"),
    )
    assert report.report_id == "r1"
    assert report.file_path == "a.py"
    assert report.risk_class == "HIGH"
    assert report.current_hold_status == "HOLD"
    assert report.human_decision == "PENDING"
    assert report.required_evidence == ("e1", "e2")


def test_hold_status_must_be_hold() -> None:
    with pytest.raises(ValueError, match="HOLD"):
        HoldDecisionReport(
            report_id="r1",
            file_path="a.py",
            risk_class="HIGH",
            current_hold_status="RELEASED",
            readiness_score=0.0,
            unlock_recommendation="HOLD",
            human_decision="PENDING",
            decision_rationale="",
            required_evidence=(),
        )


def test_hold_decision_report_class_constants() -> None:
    assert HoldDecisionReport.HOLD == "HOLD"
    assert HoldDecisionReport.PENDING == "PENDING"
    assert HoldDecisionReport.APPROVED == "APPROVED"
    assert HoldDecisionReport.DENIED == "DENIED"


def test_hold_decision_report_all_decisions() -> None:
    assert "PENDING" in HoldDecisionReport.ALL_DECISIONS
    assert "APPROVED" in HoldDecisionReport.ALL_DECISIONS
    assert "DENIED" in HoldDecisionReport.ALL_DECISIONS


# --- Generator tests ---

def test_generator_produces_hold_status() -> None:
    report = generate_hold_decision_report(file_path="a.py", risk_class="HIGH")
    assert report.current_hold_status == "HOLD"


def test_generator_default_human_decision_pending() -> None:
    report = generate_hold_decision_report(file_path="a.py", risk_class="MEDIUM")
    assert report.human_decision == "PENDING"


def test_generator_high_risk_extra_evidence() -> None:
    report = generate_hold_decision_report(file_path="a.py", risk_class="HIGH")
    assert "sign_off_from_two_reviewers" in report.required_evidence
    assert "regression_suite_green" in report.required_evidence


def test_generator_medium_risk_no_extra_evidence() -> None:
    report = generate_hold_decision_report(file_path="a.py", risk_class="MEDIUM")
    assert "sign_off_from_two_reviewers" not in report.required_evidence


def test_generator_output_is_frozen() -> None:
    report = generate_hold_decision_report(file_path="a.py", risk_class="HIGH")
    with pytest.raises(AttributeError):
        report.file_path = "changed"  # type: ignore[misc]


def test_generator_deterministic() -> None:
    r1 = generate_hold_decision_report(file_path="a.py", risk_class="HIGH")
    r2 = generate_hold_decision_report(file_path="a.py", risk_class="HIGH")
    assert r1 == r2


# --- Renderer tests ---

def test_renderer_full_md() -> None:
    report = generate_hold_decision_report(file_path="a.py", risk_class="HIGH")
    md = render_hold_decision_report_md(report)
    assert "Hold Decision Report" in md
    assert "HOLD" in md
    assert "PENDING" in md


def test_renderer_hold_status_md() -> None:
    report = generate_hold_decision_report(file_path="a.py", risk_class="HIGH")
    md = render_hold_status_md(report)
    assert "Hold Status" in md
    assert "HOLD" in md


def test_renderer_human_decision_md() -> None:
    report = generate_hold_decision_report(file_path="a.py", risk_class="HIGH")
    md = render_human_decision_md(report)
    assert "Human Decision" in md
    assert "PENDING" in md
