"""PRD frozen milestone guard — validates FROZEN tasks stay inside M8.

T888. Pure deterministic, no I/O, no timestamps, no random.
Blocks live execution if any FROZEN-risk task exists outside the frozen
milestone prefix or has a status other than NOT_STARTED.
"""

from dataclasses import dataclass
from typing import Dict, List

from core.prd_backlog_schema import PrdBacklogItem


# --- Dataclasses ---


@dataclass(frozen=True)
class PrdFrozenMilestoneGuard:
    guard_id: str
    blocked_task_count: int
    allowed_task_count: int
    verdict: str  # "PASS" or "BLOCKED"
    blocked_tasks: List[str]  # task_id strings
    notes: List[str]


# --- Core logic ---


def check_frozen_milestone(
    items: List[PrdBacklogItem],
    frozen_milestone_prefix: str = "M8",
) -> PrdFrozenMilestoneGuard:
    """Validate that no FROZEN-risk task leaks outside the frozen milestone.

    Rules:
    - A task with risk_level="FROZEN" and milestone_id != frozen_milestone_prefix is blocked.
    - A task with risk_level="FROZEN" and status != "NOT_STARTED" is blocked
      (frozen tasks must not be completed or in-progress).

    Pure, deterministic.
    """
    blocked_tasks: List[str] = []
    notes: List[str] = []

    for item in items:
        if item.risk_level != "FROZEN":
            continue
        # Rule 1: FROZEN tasks must belong to the frozen milestone
        if item.milestone_id != frozen_milestone_prefix:
            blocked_tasks.append(item.task_id)
            notes.append(
                f"FROZEN task {item.task_id} is outside frozen milestone "
                f"(milestone={item.milestone_id}, expected={frozen_milestone_prefix})"
            )
        # Rule 2: FROZEN tasks must have status NOT_STARTED
        if item.status != "NOT_STARTED":
            if item.task_id not in blocked_tasks:
                blocked_tasks.append(item.task_id)
            notes.append(
                f"FROZEN task {item.task_id} has active status "
                f"(status={item.status}, expected=NOT_STARTED)"
            )

    verdict = "BLOCKED" if blocked_tasks else "PASS"
    allowed_count = len(items) - len(blocked_tasks)

    if not notes:
        notes.append("All FROZEN tasks are inside the frozen milestone and NOT_STARTED")

    return PrdFrozenMilestoneGuard(
        guard_id="frozen-milestone-guard",
        blocked_task_count=len(blocked_tasks),
        allowed_task_count=allowed_count,
        verdict=verdict,
        blocked_tasks=tuple(blocked_tasks),  # type: ignore[arg-type]
        notes=tuple(notes),  # type: ignore[arg-type]
    )


# --- Serializers ---


def frozen_guard_to_dict(guard: PrdFrozenMilestoneGuard) -> Dict:
    """Convert guard result to plain dict."""
    return {
        "guard_id": guard.guard_id,
        "blocked_task_count": guard.blocked_task_count,
        "allowed_task_count": guard.allowed_task_count,
        "verdict": guard.verdict,
        "blocked_tasks": list(guard.blocked_tasks),
        "notes": list(guard.notes),
    }


def frozen_guard_to_markdown(guard: PrdFrozenMilestoneGuard) -> str:
    """Convert guard result to markdown string."""
    lines: List[str] = []
    lines.append("# PRD Frozen Milestone Guard Report")
    lines.append("")
    lines.append(f"- **Guard ID:** {guard.guard_id}")
    lines.append(f"- **Blocked tasks:** {guard.blocked_task_count}")
    lines.append(f"- **Allowed tasks:** {guard.allowed_task_count}")
    lines.append(f"- **Verdict:** {guard.verdict}")
    lines.append("")
    if guard.notes:
        lines.append("## Notes")
        for note in guard.notes:
            lines.append(f"- {note}")
        lines.append("")
    if guard.blocked_tasks:
        lines.append("## Blocked Tasks")
        for tid in guard.blocked_tasks:
            lines.append(f"- {tid}")
        lines.append("")
    return "\n".join(lines)
