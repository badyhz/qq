"""T1463 - Pure hold decision report generator."""
from __future__ import annotations

from core.hold_decision_report import HoldDecisionReport
from core.unlock_recommendation_engine import generate_unlock_recommendation


def generate_hold_decision_report(
    *,
    file_path: str,
    risk_class: str,
) -> HoldDecisionReport:
    """Create a HoldDecisionReport with HOLD status, PENDING human decision. Pure, no I/O."""
    rec = generate_unlock_recommendation(
        file_path=file_path,
        risk_class=risk_class,
        readiness_score=0.0,
    )

    evidence: list[str] = []
    evidence.append("pass_all_frozen_tests")
    evidence.append("complete_peer_review")
    if risk_class.upper() == "HIGH":
        evidence.append("sign_off_from_two_reviewers")
        evidence.append("regression_suite_green")

    rid = f"hold_{file_path}_{risk_class.upper()}"

    return HoldDecisionReport(
        report_id=rid,
        file_path=file_path,
        risk_class=risk_class.upper(),
        current_hold_status=HoldDecisionReport.HOLD,
        readiness_score=rec.readiness_score,
        unlock_recommendation=rec.recommendation,
        human_decision=HoldDecisionReport.PENDING,
        decision_rationale="",
        required_evidence=tuple(evidence),
    )
