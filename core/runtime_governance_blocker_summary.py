"""Runtime governance blocker summary — summarize blockers to phase advancement.

Pure. No I/O. No network. No random. Deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class RuntimeGovernanceBlocker:
    """Single blocker item."""

    blocker_id: str
    action: str  # "BLOCK" or "WARN"
    message: str
    severity: str  # "critical", "warning", "info"


@dataclass(frozen=True)
class RuntimeGovernanceBlockerSummary:
    """Immutable blocker summary for runtime governance."""

    blockers: List[RuntimeGovernanceBlocker]
    action: str  # "BLOCK" if any blocker is BLOCK, else "PROCEED"
    total: int
    blocks: int
    warns: int
    notes: List[str] = field(default_factory=list)


def summarize_runtime_governance_blockers(
    *,
    blockers: List[RuntimeGovernanceBlocker] | None = None,
    notes: List[str] | None = None,
) -> RuntimeGovernanceBlockerSummary:
    """Summarize blockers. Pure. No I/O."""
    effective_blockers: List[RuntimeGovernanceBlocker] = list(blockers) if blockers else []
    effective_notes: List[str] = list(notes) if notes else []

    total = len(effective_blockers)
    blocks = sum(1 for b in effective_blockers if b.action == "BLOCK")
    warns = total - blocks
    action = "BLOCK" if blocks > 0 else "PROCEED"

    return RuntimeGovernanceBlockerSummary(
        blockers=effective_blockers,
        action=action,
        total=total,
        blocks=blocks,
        warns=warns,
        notes=effective_notes,
    )


def blocker_summary_to_dict(summary: RuntimeGovernanceBlockerSummary) -> Dict[str, Any]:
    """Serialize to dict. Pure."""
    return {
        "blockers": [
            {"blocker_id": b.blocker_id, "action": b.action, "message": b.message, "severity": b.severity}
            for b in summary.blockers
        ],
        "action": summary.action,
        "total": summary.total,
        "blocks": summary.blocks,
        "warns": summary.warns,
        "notes": list(summary.notes),
    }


def blocker_summary_to_markdown(summary: RuntimeGovernanceBlockerSummary) -> str:
    """Render as deterministic markdown. No timestamps."""
    lines: List[str] = ["# Runtime Governance Blocker Summary", ""]
    lines.append(f"**Action:** {summary.action}")
    lines.append(f"**Total:** {summary.total}")
    lines.append(f"**Blocks:** {summary.blocks}")
    lines.append(f"**Warns:** {summary.warns}")
    lines.append("")
    if summary.blockers:
        lines.append("| # | blocker_id | action | severity | message |")
        lines.append("|---|---|---|---|---|")
        for idx, b in enumerate(summary.blockers, 1):
            lines.append(f"| {idx} | {b.blocker_id} | {b.action} | {b.severity} | {b.message} |")
        lines.append("")
    if summary.notes:
        lines.append("## Notes")
        lines.append("")
        for note in summary.notes:
            lines.append(f"- {note}")
        lines.append("")
    return "\n".join(lines)
