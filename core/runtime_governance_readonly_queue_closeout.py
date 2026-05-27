"""T857 — Runtime governance read-only queue closeout.

Final hard-stop marker for the runtime governance read-only queue.
Pure, deterministic, no I/O, no timestamps, no random.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class RuntimeGovernanceReadOnlyQueueCloseout:
    """Immutable closeout record for the read-only governance queue."""

    queue_range: str
    completed: int
    hard_stop_task: str
    next_task_allowed: bool
    final_message: str
    frozen_boundaries: List[str]


_DEFAULT_FROZEN_BOUNDARIES: List[str] = [
    "no live trading",
    "no real execution",
    "no secret access",
    "no network call",
    "no planner integration",
    "no file write",
]


def build_readonly_queue_closeout() -> RuntimeGovernanceReadOnlyQueueCloseout:
    """Build the default closeout record. Pure, no I/O."""
    return RuntimeGovernanceReadOnlyQueueCloseout(
        queue_range="T826-T857",
        completed=32,
        hard_stop_task="T857",
        next_task_allowed=False,
        final_message=(
            "HARD STOP after T857. Do not continue to T858. "
            "Next task requires human/manual instruction."
        ),
        frozen_boundaries=list(_DEFAULT_FROZEN_BOUNDARIES),
    )


def readonly_queue_closeout_to_dict(
    closeout: RuntimeGovernanceReadOnlyQueueCloseout,
) -> Dict[str, object]:
    """Convert closeout to a plain dict. Pure, no I/O."""
    return {
        "queue_range": closeout.queue_range,
        "completed": closeout.completed,
        "hard_stop_task": closeout.hard_stop_task,
        "next_task_allowed": closeout.next_task_allowed,
        "final_message": closeout.final_message,
        "frozen_boundaries": list(closeout.frozen_boundaries),
    }


def readonly_queue_closeout_to_markdown(
    closeout: RuntimeGovernanceReadOnlyQueueCloseout,
) -> str:
    """Render closeout as markdown. Pure, no I/O."""
    boundaries_lines = "\n".join(
        f"- {b}" for b in closeout.frozen_boundaries
    )
    return (
        f"# Runtime Governance Read-Only Queue Closeout\n\n"
        f"**Queue range:** {closeout.queue_range}\n"
        f"**Completed:** {closeout.completed}\n"
        f"**Hard stop task:** {closeout.hard_stop_task}\n"
        f"**Next task allowed:** {closeout.next_task_allowed}\n\n"
        f"## Final Message\n\n{closeout.final_message}\n\n"
        f"## Frozen Boundaries\n\n{boundaries_lines}\n"
    )
