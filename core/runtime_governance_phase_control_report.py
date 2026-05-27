"""Runtime governance phase control report — determine if project may advance.

Combines regression, readiness, blocker, no-submit, and preflight signals
into a single phase-control decision. Pure. No I/O. No network. No random.

Decision logic:
  HOLD if any blocker action is BLOCK
  HOLD if no_submit evidence not all PASS
  REVIEW if readiness grade below B
  PROCEED_TO_MANUAL_SCOPE_ONLY if all pass
  NEVER say ready for live trading
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from core.runtime_governance_regression_packet import (
    RuntimeGovernanceRegressionPacket,
    build_runtime_governance_regression_packet,
    runtime_regression_packet_to_dict,
    runtime_regression_packet_to_markdown,
)
from core.runtime_governance_readiness_score import (
    RuntimeGovernanceReadinessScore,
    compute_runtime_governance_readiness_score,
    readiness_score_to_dict,
    readiness_score_to_markdown,
)

# Grade ordering: A > B > C > D > F (lower index = higher grade)
_GRADE_ORDER = ("A", "B", "C", "D", "F")
from core.runtime_governance_blocker_summary import (
    RuntimeGovernanceBlockerSummary,
    summarize_runtime_governance_blockers,
    blocker_summary_to_dict,
    blocker_summary_to_markdown,
)
from core.runtime_governance_no_submit_evidence_packet import (
    RuntimeGovernanceNoSubmitEvidence,
    build_runtime_governance_no_submit_evidence_packet,
    no_submit_evidence_verdict,
)


# ── report dataclass ──────────────────────────────────────────────────


@dataclass(frozen=True)
class RuntimeGovernancePhaseControlReport:
    """Immutable phase control report for runtime governance."""

    phase: str
    regression_verdict: str
    readiness_grade: str
    blocker_action: str
    no_submit_verdict: str
    final_decision: str
    notes: List[str] = field(default_factory=list)


# ── grade comparison ──────────────────────────────────────────────────


def _grade_below_b(grade: str) -> bool:
    """Return True if grade is below B (i.e. C, D, or F). Pure."""
    try:
        return _GRADE_ORDER.index(grade) > _GRADE_ORDER.index("B")
    except ValueError:
        return True  # unknown grade treated as below B


# ── decision logic ────────────────────────────────────────────────────


def _resolve_final_decision(
    *,
    blocker_action: str,
    no_submit_verdict: str,
    readiness_grade: str,
) -> str:
    """Resolve final decision from component results. Pure.

    Priority:
    1. HOLD if blocker_action is BLOCK
    2. HOLD if no_submit_verdict is not PASS
    3. REVIEW if readiness_grade below B
    4. PROCEED_TO_MANUAL_SCOPE_ONLY otherwise
    """
    if blocker_action == "BLOCK":
        return "HOLD"
    if no_submit_verdict != "PASS":
        return "HOLD"
    if _grade_below_b(readiness_grade):
        return "REVIEW"
    return "PROCEED_TO_MANUAL_SCOPE_ONLY"


# ── builder ───────────────────────────────────────────────────────────


def build_runtime_governance_phase_control_report(
    *,
    regression_packet: RuntimeGovernanceRegressionPacket | None = None,
    readiness_score: RuntimeGovernanceReadinessScore | None = None,
    blocker_summary: RuntimeGovernanceBlockerSummary | None = None,
    no_submit_evidence: List[RuntimeGovernanceNoSubmitEvidence] | None = None,
    notes: List[str] | None = None,
) -> RuntimeGovernancePhaseControlReport:
    """Build phase control report from governance components. Pure. No I/O.

    Steps:
    1. Use provided components or build defaults (empty = all pass)
    2. Resolve final decision via decision logic
    3. Assemble immutable report
    """
    extra_notes: List[str] = list(notes) if notes else []

    # step 1: resolve components (defaults to all-pass)
    reg = regression_packet if regression_packet is not None else build_runtime_governance_regression_packet()
    readiness = readiness_score if readiness_score is not None else compute_runtime_governance_readiness_score(reg)
    blockers = blocker_summary if blocker_summary is not None else summarize_runtime_governance_blockers()
    evidence = no_submit_evidence if no_submit_evidence is not None else build_runtime_governance_no_submit_evidence_packet()
    no_submit_verdict = no_submit_evidence_verdict(evidence)

    # step 2: resolve decision
    final_decision = _resolve_final_decision(
        blocker_action=blockers.action,
        no_submit_verdict=no_submit_verdict,
        readiness_grade=readiness.grade,
    )

    # step 3: assemble
    all_notes = list(extra_notes)
    all_notes.extend(reg.notes)
    all_notes.extend(readiness.notes)
    all_notes.extend(blockers.notes)

    # append decision reasoning
    if final_decision == "HOLD":
        if blockers.action == "BLOCK":
            all_notes.append("decision: HOLD — blocker action is BLOCK")
        elif no_submit_verdict != "PASS":
            all_notes.append("decision: HOLD — no-submit evidence not all PASS")
    elif final_decision == "REVIEW":
        all_notes.append(f"decision: REVIEW — readiness grade {readiness.grade} below B")
    else:
        all_notes.append("decision: PROCEED_TO_MANUAL_SCOPE_ONLY — all checks passed")

    return RuntimeGovernancePhaseControlReport(
        phase="pre-live audit",
        regression_verdict=reg.final_verdict,
        readiness_grade=readiness.grade,
        blocker_action=blockers.action,
        no_submit_verdict=no_submit_verdict,
        final_decision=final_decision,
        notes=all_notes,
    )


# ── serialization ─────────────────────────────────────────────────────


def phase_control_report_to_dict(report: RuntimeGovernancePhaseControlReport) -> Dict[str, Any]:
    """Serialize to dict. Pure."""
    return {
        "phase": report.phase,
        "regression_verdict": report.regression_verdict,
        "readiness_grade": report.readiness_grade,
        "blocker_action": report.blocker_action,
        "no_submit_verdict": report.no_submit_verdict,
        "final_decision": report.final_decision,
        "notes": list(report.notes),
    }


def phase_control_report_to_markdown(report: RuntimeGovernancePhaseControlReport) -> str:
    """Render as deterministic markdown. No timestamps.

    Never mentions 'live trading'. Always mentions 'manual scope'.
    """
    lines: List[str] = ["# Runtime Governance Phase Control Report", ""]

    lines.append(f"**Phase:** {report.phase}")
    lines.append(f"**Final Decision:** {report.final_decision}")
    lines.append("")

    lines.append("## Component Summary")
    lines.append("")
    lines.append(f"- **Regression Verdict:** {report.regression_verdict}")
    lines.append(f"- **Readiness Grade:** {report.readiness_grade}")
    lines.append(f"- **Blocker Action:** {report.blocker_action}")
    lines.append(f"- **No-Submit Verdict:** {report.no_submit_verdict}")
    lines.append("")

    lines.append("## Decision Logic")
    lines.append("")
    if report.final_decision == "HOLD":
        lines.append("Project is on HOLD. Resolve blockers before advancing.")
    elif report.final_decision == "REVIEW":
        lines.append("Project needs REVIEW. Readiness grade is below B.")
    else:
        lines.append(
            "Project may proceed to manual scope only. "
            "This does NOT indicate readiness for production deployment. "
            "Manual review and explicit approval are required before any production use."
        )
    lines.append("")

    if report.notes:
        lines.append("## Notes")
        lines.append("")
        for note in report.notes:
            lines.append(f"- {note}")
        lines.append("")

    return "\n".join(lines)
