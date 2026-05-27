"""T837 — Runtime governance read-only blocker summary.

Summarize blockers for the read-only layer.
Pure. No I/O. No timestamps. No random. Frozen dataclass.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class RuntimeGovernanceReadOnlyBlockerSummary:
    """Immutable read-only blocker summary."""

    total_blockers: int
    dangerous_permission_blockers: int
    invariant_blockers: int
    recommended_action: str  # PROCEED / REVIEW / BLOCK
    notes: List[str] = field(default_factory=list)


def summarize_readonly_blockers(
    evaluations: Optional[List[Any]] = None,
    invariant_summary: Optional[Dict[str, Any]] = None,
) -> RuntimeGovernanceReadOnlyBlockerSummary:
    """Summarize blockers from scenario evaluations and invariant summary.

    Pure. Deterministic. No I/O. No timestamps. No random.

    Args:
        evaluations: list of RuntimeGovernanceReadOnlyScenarioEvaluation (T834)
        invariant_summary: dict from invariant checker (T832)
    """
    if evaluations is None:
        evaluations = []
    if invariant_summary is None:
        invariant_summary = {}

    dangerous_permission_blockers = sum(
        1 for e in evaluations if e.actual_verdict == "BLOCKED"
    )
    invariant_blockers = invariant_summary.get("failed", 0)
    total_blockers = dangerous_permission_blockers + invariant_blockers

    notes: List[str] = []
    if dangerous_permission_blockers > 0:
        notes.append(
            f"{dangerous_permission_blockers} dangerous permission blocker(s)"
        )
    if invariant_blockers > 0:
        notes.append(f"{invariant_blockers} invariant failure(s)")

    if dangerous_permission_blockers > 0 or invariant_blockers > 0:
        recommended_action = "BLOCK"
    elif total_blockers > 0:
        recommended_action = "REVIEW"
    else:
        recommended_action = "PROCEED"

    return RuntimeGovernanceReadOnlyBlockerSummary(
        total_blockers=total_blockers,
        dangerous_permission_blockers=dangerous_permission_blockers,
        invariant_blockers=invariant_blockers,
        recommended_action=recommended_action,
        notes=notes,
    )


def readonly_blocker_summary_to_dict(
    summary: RuntimeGovernanceReadOnlyBlockerSummary,
) -> Dict[str, Any]:
    """Serialize to dict. Pure. Deterministic."""
    return {
        "total_blockers": summary.total_blockers,
        "dangerous_permission_blockers": summary.dangerous_permission_blockers,
        "invariant_blockers": summary.invariant_blockers,
        "recommended_action": summary.recommended_action,
        "notes": list(summary.notes),
    }


def readonly_blocker_summary_to_markdown(
    summary: RuntimeGovernanceReadOnlyBlockerSummary,
) -> str:
    """Render as deterministic markdown. No timestamps."""
    lines = [
        "# Read-Only Blocker Summary",
        "",
        f"**Recommended Action:** {summary.recommended_action}",
        f"**Total Blockers:** {summary.total_blockers}",
        f"**Dangerous Permission Blockers:** {summary.dangerous_permission_blockers}",
        f"**Invariant Blockers:** {summary.invariant_blockers}",
    ]
    if summary.notes:
        lines.append("")
        lines.append("## Notes")
        lines.append("")
        for note in summary.notes:
            lines.append(f"- {note}")
    lines.append("")
    return "\n".join(lines)
