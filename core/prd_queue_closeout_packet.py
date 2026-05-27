"""PRD Queue Closeout Packet — T871."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(frozen=True)
class PrdQueueCloseoutPacket:
    queue_range: str
    completed_tasks: List[str]
    expected_artifacts: int
    validation_verdict: str
    safety_verdict: str
    final_status: str
    hard_stop_task: str
    next_task_allowed: bool
    notes: List[str]


def build_prd_queue_closeout_packet(
    queue_range: str = "T865-T872",
    completed_tasks: List[str] | None = None,
    expected_artifacts: int = 8,
    validation_verdict: str = "PASS",
    safety_verdict: str = "PASS",
    final_status: str = "COMPLETED",
    hard_stop_task: str = "T872",
    next_task_allowed: bool = False,
    notes: List[str] | None = None,
) -> PrdQueueCloseoutPacket:
    if completed_tasks is None:
        completed_tasks = [
            "T865", "T866", "T867", "T868",
            "T869", "T870", "T871", "T872",
        ]
    if notes is None:
        notes = [
            "hard stop at T872 — no next task without human instruction",
            "all artifacts validated",
        ]
    return PrdQueueCloseoutPacket(
        queue_range=queue_range,
        completed_tasks=list(completed_tasks),
        expected_artifacts=expected_artifacts,
        validation_verdict=validation_verdict,
        safety_verdict=safety_verdict,
        final_status=final_status,
        hard_stop_task=hard_stop_task,
        next_task_allowed=next_task_allowed,
        notes=list(notes),
    )


def queue_closeout_packet_to_dict(packet: PrdQueueCloseoutPacket) -> Dict:
    return {
        "queue_range": packet.queue_range,
        "completed_tasks": list(packet.completed_tasks),
        "expected_artifacts": packet.expected_artifacts,
        "validation_verdict": packet.validation_verdict,
        "safety_verdict": packet.safety_verdict,
        "final_status": packet.final_status,
        "hard_stop_task": packet.hard_stop_task,
        "next_task_allowed": packet.next_task_allowed,
        "notes": list(packet.notes),
    }


def queue_closeout_packet_to_markdown(packet: PrdQueueCloseoutPacket) -> str:
    tasks_str = ", ".join(packet.completed_tasks)
    notes_lines = "\n".join(f"- {n}" for n in packet.notes)
    return (
        f"# PRD Queue Closeout Packet\n\n"
        f"**Queue Range:** {packet.queue_range}\n"
        f"**Completed Tasks:** {tasks_str}\n"
        f"**Expected Artifacts:** {packet.expected_artifacts}\n"
        f"**Validation Verdict:** {packet.validation_verdict}\n"
        f"**Safety Verdict:** {packet.safety_verdict}\n"
        f"**Final Status:** {packet.final_status}\n"
        f"**Hard Stop Task:** {packet.hard_stop_task}\n"
        f"**Next Task Allowed:** {packet.next_task_allowed}\n\n"
        f"## Notes\n\n{notes_lines}\n"
    )
