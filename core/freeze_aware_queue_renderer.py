"""T1129 - Freeze-Aware Queue Renderer."""
from __future__ import annotations

from core.freeze_aware_queue import FreezeAwareQueue
from core.freeze_aware_task_state import FreezeAwareTaskState
from core.freeze_aware_admission_result import FreezeAwareAdmissionResult
from core.freeze_aware_denial_reason import FreezeAwareDenialReason


def render_freeze_aware_queue_md(queue: FreezeAwareQueue) -> str:
    lines: list[str] = []
    lines.append("## Freeze-Aware Queue")
    lines.append("")
    lines.append(f"- **Queue ID:** {queue.queue_id}")
    lines.append(f"- **Release Hold:** {queue.release_hold}")
    lines.append(f"- **Task Count:** {len(queue.tasks)}")
    lines.append(f"- **Frozen File Count:** {len(queue.frozen_files)}")
    lines.append("")
    if queue.tasks:
        lines.append("### Tasks")
        for task in queue.tasks:
            lines.append(f"- {task}")
        lines.append("")
    if queue.frozen_files:
        lines.append("### Frozen Files")
        for f in queue.frozen_files:
            lines.append(f"- {f}")
        lines.append("")
    return "\n".join(lines)


def render_task_state_md(state: FreezeAwareTaskState) -> str:
    lines: list[str] = []
    lines.append("## Task States")
    lines.append("")
    lines.append(f"- NOT_STARTED: {state.NOT_STARTED}")
    lines.append(f"- IN_PROGRESS: {state.IN_PROGRESS}")
    lines.append(f"- COMPLETED: {state.COMPLETED}")
    lines.append(f"- HUMAN_REVIEW_REQUIRED: {state.HUMAN_REVIEW_REQUIRED}")
    lines.append(f"- BLOCKED: {state.BLOCKED}")
    lines.append(f"- PARTIAL: {state.PARTIAL}")
    lines.append(f"- PASS: {state.PASS}")
    lines.append(f"- DENIED: {state.DENIED}")
    lines.append("")
    return "\n".join(lines)


def render_admission_result_md(result: FreezeAwareAdmissionResult) -> str:
    lines: list[str] = []
    lines.append("## Admission Result")
    lines.append("")
    lines.append(f"- **Admitted:** {result.admitted}")
    lines.append(f"- **Task ID:** {result.task_id}")
    lines.append(f"- **Reason:** {result.reason}")
    lines.append("")
    if result.blocking_freeze_files:
        lines.append("### Blocking Freeze Files")
        for f in result.blocking_freeze_files:
            lines.append(f"- {f}")
        lines.append("")
    return "\n".join(lines)


def render_denial_reason_md(reason: FreezeAwareDenialReason) -> str:
    lines: list[str] = []
    lines.append("## Denial Reason")
    lines.append("")
    lines.append(f"- **Reason ID:** {reason.reason_id}")
    lines.append(f"- **Category:** {reason.category}")
    lines.append(f"- **Message:** {reason.message}")
    lines.append(f"- **Related Task ID:** {reason.related_task_id}")
    lines.append(f"- **Related Freeze File:** {reason.related_freeze_file}")
    lines.append("")
    return "\n".join(lines)
