"""T838 — Runtime governance read-only phase control report.

Determine if read-only design may move to manual review.
Pure. Deterministic. No I/O. No timestamps. No random.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from core.runtime_governance_readonly_regression_packet import (
    build_readonly_regression_packet,
)
from core.runtime_governance_readonly_readiness_score import (
    compute_readonly_readiness_score,
)
from core.runtime_governance_readonly_blocker_summary import (
    summarize_readonly_blockers,
)


@dataclass(frozen=True)
class RuntimeGovernanceReadOnlyPhaseControlReport:
    """Immutable phase control report for read-only design gate."""

    phase: str
    regression_verdict: str
    readiness_grade: str
    blocker_action: str
    final_decision: str  # HOLD / REVIEW / PROCEED_TO_MANUAL_REVIEW_ONLY
    notes: List[str] = field(default_factory=list)


def _decide(blocker_action: str, readiness_grade: str) -> str:
    """Decision logic. Pure. Deterministic.

    HOLD if blocker_action == "BLOCK"
    REVIEW if readiness_grade not in ("A", "B")
    PROCEED_TO_MANUAL_REVIEW_ONLY otherwise
    """
    if blocker_action == "BLOCK":
        return "HOLD"
    if readiness_grade not in ("A", "B"):
        return "REVIEW"
    return "PROCEED_TO_MANUAL_REVIEW_ONLY"


def build_readonly_phase_control_report(
    phase: str = "read-only design review",
    regression_packet=None,
    readiness_score=None,
    blocker_summary=None,
) -> RuntimeGovernanceReadOnlyPhaseControlReport:
    """Build phase control report from sub-components.

    Pure. Deterministic. No I/O. No timestamps. No random.

    Defaults produce: PROCEED_TO_MANUAL_REVIEW_ONLY.
    """
    if regression_packet is None:
        regression_packet = build_readonly_regression_packet()
    if readiness_score is None:
        readiness_score = compute_readonly_readiness_score(regression_packet)
    if blocker_summary is None:
        blocker_summary = summarize_readonly_blockers()

    regression_verdict = regression_packet.final_verdict
    readiness_grade = readiness_score.grade
    blocker_action = blocker_summary.recommended_action

    notes: List[str] = []
    notes.append(f"regression_verdict={regression_verdict}")
    notes.append(f"readiness_grade={readiness_grade}")
    notes.append(f"blocker_action={blocker_action}")

    final_decision = _decide(blocker_action, readiness_grade)

    return RuntimeGovernanceReadOnlyPhaseControlReport(
        phase=phase,
        regression_verdict=regression_verdict,
        readiness_grade=readiness_grade,
        blocker_action=blocker_action,
        final_decision=final_decision,
        notes=notes,
    )


def readonly_phase_control_report_to_dict(
    report: RuntimeGovernanceReadOnlyPhaseControlReport,
) -> Dict[str, Any]:
    """Serialize report to plain dict. Pure. Deterministic."""
    return {
        "phase": report.phase,
        "regression_verdict": report.regression_verdict,
        "readiness_grade": report.readiness_grade,
        "blocker_action": report.blocker_action,
        "final_decision": report.final_decision,
        "notes": list(report.notes),
    }


def readonly_phase_control_report_to_markdown(
    report: RuntimeGovernanceReadOnlyPhaseControlReport,
) -> str:
    """Render report as deterministic markdown. No timestamps."""
    lines = [
        "# Runtime Governance Read-Only Phase Control Report",
        "",
        "| Field | Value |",
        "|-------|-------|",
        f"| Phase | {report.phase} |",
        f"| Regression Verdict | {report.regression_verdict} |",
        f"| Readiness Grade | {report.readiness_grade} |",
        f"| Blocker Action | {report.blocker_action} |",
        f"| **Final Decision** | **{report.final_decision}** |",
    ]
    if report.notes:
        lines.append("")
        lines.append("## Notes")
        lines.append("")
        for note in report.notes:
            lines.append(f"- {note}")
    lines.append("")
    return "\n".join(lines)
