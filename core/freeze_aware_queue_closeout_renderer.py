"""T1130 - Freeze-Aware Queue Closeout Renderer."""
from __future__ import annotations

from core.freeze_aware_dependency_result import FreezeAwareDependencyResult
from core.freeze_aware_handoff_packet import FreezeAwareHandoffPacket
from core.freeze_aware_hold_state import FreezeAwareHoldState
from core.freeze_aware_transition_guard import FreezeAwareTransitionGuard
from core.freeze_aware_queue_verdict import FreezeAwareQueueVerdict
from core.freeze_aware_queue_model_closeout import FreezeAwareQueueModelCloseout


def render_dependency_result_md(result: FreezeAwareDependencyResult) -> str:
    lines: list[str] = []
    lines.append("## Dependency Result")
    lines.append("")
    lines.append(f"- **Valid:** {result.valid}")
    lines.append(f"- **Cycle Detected:** {result.cycle_detected}")
    lines.append("")
    if result.missing_deps:
        lines.append("### Missing Dependencies")
        for dep in result.missing_deps:
            lines.append(f"- {dep}")
        lines.append("")
    if result.orphans:
        lines.append("### Orphans")
        for o in result.orphans:
            lines.append(f"- {o}")
        lines.append("")
    return "\n".join(lines)


def render_handoff_packet_md(packet: FreezeAwareHandoffPacket) -> str:
    lines: list[str] = []
    lines.append("## Handoff Packet")
    lines.append("")
    lines.append(f"- **From Agent:** {packet.from_agent}")
    lines.append(f"- **To Agent:** {packet.to_agent}")
    lines.append(f"- **Task ID:** {packet.task_id}")
    lines.append(f"- **Verification Command:** `{packet.verification_command}`")
    if packet.notes:
        lines.append(f"- **Notes:** {packet.notes}")
    lines.append("")
    if packet.explicit_files:
        lines.append("### Explicit Files")
        for f in packet.explicit_files:
            lines.append(f"- {f}")
        lines.append("")
    return "\n".join(lines)


def render_hold_state_md(state: FreezeAwareHoldState) -> str:
    lines: list[str] = []
    lines.append("## Hold State")
    lines.append("")
    lines.append(f"- **Hold Active:** {state.hold_active}")
    lines.append(f"- **Hold Reason:** {state.hold_reason}")
    lines.append(f"- **Release Requires Human:** {state.release_requires_human}")
    lines.append("")
    if state.blocked_task_ids:
        lines.append("### Blocked Task IDs")
        for tid in state.blocked_task_ids:
            lines.append(f"- {tid}")
        lines.append("")
    return "\n".join(lines)


def render_transition_guard_md(guard: FreezeAwareTransitionGuard) -> str:
    lines: list[str] = []
    lines.append("## Transition Guard")
    lines.append("")
    lines.append(f"- **From State:** {guard.from_state}")
    lines.append(f"- **To State:** {guard.to_state}")
    lines.append(f"- **Guard Condition:** {guard.guard_condition}")
    lines.append(f"- **Requires Human Approval:** {guard.requires_human_approval}")
    lines.append("")
    return "\n".join(lines)


def render_queue_verdict_md(verdict: FreezeAwareQueueVerdict) -> str:
    lines: list[str] = []
    lines.append("## Queue Verdict")
    lines.append("")
    lines.append(f"- **Verdict:** {verdict.verdict}")
    lines.append(f"- **Admitted:** {verdict.admitted_count}")
    lines.append(f"- **Denied:** {verdict.denied_count}")
    lines.append(f"- **Blocked:** {verdict.blocked_count}")
    if verdict.notes:
        lines.append(f"- **Notes:** {verdict.notes}")
    lines.append("")
    return "\n".join(lines)


def render_queue_closeout_md(closeout: FreezeAwareQueueModelCloseout) -> str:
    lines: list[str] = []
    lines.append("## Queue Model Closeout")
    lines.append("")
    lines.append(f"- **Model Count:** {closeout.model_count}")
    lines.append(f"- **Verdict:** {closeout.verdict}")
    lines.append("")
    if closeout.models:
        lines.append("### Models")
        for model in closeout.models:
            lines.append(f"- {model}")
        lines.append("")
    return "\n".join(lines)
