"""PRD 500 backlog batch map — deterministic batch splitting.

T907. Pure deterministic. No I/O. No timestamps. No random.
"""

from dataclasses import dataclass
from typing import Any, Dict, List

from core.prd_backlog_schema import PrdBacklog, PrdBacklogItem

# --- Dataclass ---


@dataclass(frozen=True)
class Prd500BatchMapEntry:
    batch_id: str
    wave_id: str
    start_task_id: str
    end_task_id: str
    task_count: int
    risk_level: str
    recommended_agent_count: int
    hard_stop_task_id: str
    notes: List[str]


# --- Constants ---

_MAX_BATCH_SIZE = 10

_AGENT_COUNT_MAP = {
    "LOW": 8,
    "MEDIUM": 8,
    "HIGH": 3,
    "FROZEN": 0,
}


# --- Builder ---


def build_prd_500_batch_map(
    backlog: PrdBacklog, max_tasks_per_batch: int = _MAX_BATCH_SIZE
) -> List[Prd500BatchMapEntry]:
    """Split backlog items into batches grouped by milestone_id.

    Each batch has at most max_tasks_per_batch items.
    Preserves original item order within each milestone group.
    """
    if max_tasks_per_batch < 1:
        raise ValueError("max_tasks_per_batch must be >= 1")

    # Group by milestone_id, preserving order
    milestone_groups: Dict[str, List[PrdBacklogItem]] = {}
    milestone_order: List[str] = []
    for item in backlog.items:
        if item.milestone_id not in milestone_groups:
            milestone_groups[item.milestone_id] = []
            milestone_order.append(item.milestone_id)
        milestone_groups[item.milestone_id].append(item)

    entries: List[Prd500BatchMapEntry] = []
    global_batch_idx = 0

    for milestone_id in milestone_order:
        items = milestone_groups[milestone_id]
        # Split into chunks of max_tasks_per_batch
        for chunk_start in range(0, len(items), max_tasks_per_batch):
            chunk = items[chunk_start : chunk_start + max_tasks_per_batch]
            global_batch_idx += 1

            # Determine dominant risk level: highest risk wins
            risk_priority = {"FROZEN": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3}
            dominant_risk = max(
                (risk_priority.get(it.risk_level, 0) for it in chunk),
                default=0,
            )
            risk_level = next(
                k for k, v in risk_priority.items() if v == dominant_risk
            )

            entry = Prd500BatchMapEntry(
                batch_id=f"B{global_batch_idx:04d}",
                wave_id=chunk[0].wave_id,
                start_task_id=chunk[0].task_id,
                end_task_id=chunk[-1].task_id,
                task_count=len(chunk),
                risk_level=risk_level,
                recommended_agent_count=_AGENT_COUNT_MAP.get(risk_level, 0),
                hard_stop_task_id=chunk[-1].task_id,
                notes=[],
            )
            entries.append(entry)

    return entries


# --- Serializers ---


def batch_map_to_dict(entry: Prd500BatchMapEntry) -> Dict[str, Any]:
    return {
        "batch_id": entry.batch_id,
        "wave_id": entry.wave_id,
        "start_task_id": entry.start_task_id,
        "end_task_id": entry.end_task_id,
        "task_count": entry.task_count,
        "risk_level": entry.risk_level,
        "recommended_agent_count": entry.recommended_agent_count,
        "hard_stop_task_id": entry.hard_stop_task_id,
        "notes": list(entry.notes),
    }


def batch_map_to_markdown(entry: Prd500BatchMapEntry) -> str:
    lines: List[str] = []
    lines.append(f"### Batch {entry.batch_id}")
    lines.append("")
    lines.append(f"- **Wave:** {entry.wave_id}")
    lines.append(f"- **Tasks:** {entry.start_task_id} .. {entry.end_task_id} ({entry.task_count})")
    lines.append(f"- **Risk:** {entry.risk_level}")
    lines.append(f"- **Recommended agents:** {entry.recommended_agent_count}")
    lines.append(f"- **Hard stop:** {entry.hard_stop_task_id}")
    if entry.notes:
        lines.append("- **Notes:**")
        for note in entry.notes:
            lines.append(f"  - {note}")
    lines.append("")
    return "\n".join(lines)


# --- Summary ---


def summarize_batch_map(entries: List[Prd500BatchMapEntry]) -> Dict[str, Any]:
    total_tasks = sum(e.task_count for e in entries)
    risk_counts: Dict[str, int] = {}
    for e in entries:
        risk_counts[e.risk_level] = risk_counts.get(e.risk_level, 0) + 1
    return {
        "total_batches": len(entries),
        "total_tasks": total_tasks,
        "risk_counts": risk_counts,
        "max_batch_size": max((e.task_count for e in entries), default=0),
    }
