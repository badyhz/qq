"""PRD Backlog Seed Packet — T880."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class PrdBacklogSeedPacket:
    backlog_id: str
    target_task_count: int
    proposed_milestones: List[str]
    proposed_task_ranges: List[str]
    frozen_ranges: List[str]
    next_safe_range: str
    notes: List[str]


DEFAULT_MILESTONES = [
    "M1: PRD automation control plane",
    "M2: 500-task planning layer",
    "M3: read-only hook prototype design",
    "M4: offline evidence writer design",
    "M5: manual review CLI design",
    "M6: read-only hook implementation review",
    "M7: runtime integration review",
    "M8: live execution frozen",
]

DEFAULT_TASK_RANGES = [
    "T881-T888: M1 seed tasks",
    "T889-T900: M2 seed tasks",
    "T901-T920: M3 seed tasks",
    "T921-T940: M4 seed tasks",
    "T941-T960: M5 seed tasks",
    "T961-T980: M6 seed tasks",
    "T981-T1000: M7 seed tasks",
    "T1001-T1200: M8 seed tasks (frozen — no live execution)",
]

FROZEN_RANGES = [
    "M8: live execution frozen",
]


def build_prd_backlog_seed_packet(
    target_task_count: int = 500,
    backlog_id: str = "BSEED-001",
    proposed_milestones: List[str] | None = None,
    proposed_task_ranges: List[str] | None = None,
    frozen_ranges: List[str] | None = None,
    next_safe_range: str = "T881-T900 — HUMAN_REVIEW_REQUIRED",
    notes: List[str] | None = None,
) -> PrdBacklogSeedPacket:
    if target_task_count < 500:
        raise ValueError(
            f"target_task_count must be >= 500, got {target_task_count}"
        )
    if proposed_milestones is None:
        proposed_milestones = list(DEFAULT_MILESTONES)
    if proposed_task_ranges is None:
        proposed_task_ranges = list(DEFAULT_TASK_RANGES)
    if frozen_ranges is None:
        frozen_ranges = list(FROZEN_RANGES)
    if notes is None:
        notes = [
            "seed packet for 500+ task backlog",
            "M8 live execution is frozen — no authorization for live trading",
            "next_safe_range requires human review",
        ]
    return PrdBacklogSeedPacket(
        backlog_id=backlog_id,
        target_task_count=target_task_count,
        proposed_milestones=list(proposed_milestones),
        proposed_task_ranges=list(proposed_task_ranges),
        frozen_ranges=list(frozen_ranges),
        next_safe_range=next_safe_range,
        notes=list(notes),
    )


def backlog_seed_packet_to_dict(packet: PrdBacklogSeedPacket) -> Dict:
    return {
        "backlog_id": packet.backlog_id,
        "target_task_count": packet.target_task_count,
        "proposed_milestones": list(packet.proposed_milestones),
        "proposed_task_ranges": list(packet.proposed_task_ranges),
        "frozen_ranges": list(packet.frozen_ranges),
        "next_safe_range": packet.next_safe_range,
        "notes": list(packet.notes),
    }


def backlog_seed_packet_to_markdown(packet: PrdBacklogSeedPacket) -> str:
    milestones_lines = "\n".join(
        f"- {m}" for m in packet.proposed_milestones
    )
    ranges_lines = "\n".join(
        f"- {r}" for r in packet.proposed_task_ranges
    )
    frozen_lines = "\n".join(f"- {f}" for f in packet.frozen_ranges)
    notes_lines = "\n".join(f"- {n}" for n in packet.notes)
    return (
        f"# PRD Backlog Seed Packet\n\n"
        f"**Backlog ID:** {packet.backlog_id}\n"
        f"**Target Task Count:** {packet.target_task_count}\n"
        f"**Next Safe Range:** {packet.next_safe_range}\n\n"
        f"## Proposed Milestones\n\n{milestones_lines}\n\n"
        f"## Proposed Task Ranges\n\n{ranges_lines}\n\n"
        f"## Frozen Ranges\n\n{frozen_lines}\n\n"
        f"## Notes\n\n{notes_lines}\n"
    )
