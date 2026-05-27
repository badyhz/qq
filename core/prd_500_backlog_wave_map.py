"""PRD 500 backlog wave map — group backlog items into execution waves.

T906. Pure deterministic, no I/O, no timestamps, no random.
"""

from dataclasses import dataclass, asdict
from typing import Any, Dict, List

from core.prd_backlog_schema import PrdBacklog, PrdBacklogItem


# --- Dataclass ---


@dataclass(frozen=True)
class Prd500WaveMapEntry:
    wave_id: str
    milestone_id: str
    start_task_id: str
    end_task_id: str
    task_count: int
    risk_level: str
    max_parallel_agents: int
    recommended_route: str
    notes: List[str]


# --- Internal helpers ---


def _resolve_parallel_agents(risk_level: str) -> int:
    if risk_level == "FROZEN":
        return 0
    if risk_level == "HIGH":
        return 3
    return 8  # LOW / MEDIUM


def _resolve_recommended_route(risk_level: str) -> str:
    if risk_level == "FROZEN":
        return "HUMAN_ONLY"
    if risk_level == "HIGH":
        return "mimo2.5pro with human review"
    if risk_level == "MEDIUM":
        return "mimo2.5pro"
    return "mimo2.5pro or mimo2.5"  # LOW


def _dominant_risk(items: List[PrdBacklogItem]) -> str:
    """Return highest risk level present in the item list."""
    priority = {"FROZEN": 3, "HIGH": 2, "MEDIUM": 1, "LOW": 0}
    best = "LOW"
    for item in items:
        if priority.get(item.risk_level, 0) > priority.get(best, 0):
            best = item.risk_level
    return best


# --- Core function ---


def build_prd_500_wave_map(
    backlog: PrdBacklog, max_tasks_per_wave: int = 25
) -> List[Prd500WaveMapEntry]:
    """Group backlog items by milestone, split into waves of max_tasks_per_wave."""
    # Group by milestone_id preserving order
    milestone_groups: Dict[str, List[PrdBacklogItem]] = {}
    milestone_order: List[str] = []
    for item in backlog.items:
        if item.milestone_id not in milestone_groups:
            milestone_groups[item.milestone_id] = []
            milestone_order.append(item.milestone_id)
        milestone_groups[item.milestone_id].append(item)

    entries: List[Prd500WaveMapEntry] = []
    for ms_id in milestone_order:
        items = milestone_groups[ms_id]
        risk = _dominant_risk(items)
        for chunk_start in range(0, len(items), max_tasks_per_wave):
            chunk = items[chunk_start : chunk_start + max_tasks_per_wave]
            wave_index = chunk_start // max_tasks_per_wave
            wave_id = f"{ms_id}-W{wave_index}"
            start_tid = chunk[0].task_id
            end_tid = chunk[-1].task_id
            count = len(chunk)
            parallel = _resolve_parallel_agents(risk)
            route = _resolve_recommended_route(risk)
            wave_notes: List[str] = []
            if risk == "FROZEN":
                wave_notes.append("FROZEN: human-only, no agent execution")
            entries.append(
                Prd500WaveMapEntry(
                    wave_id=wave_id,
                    milestone_id=ms_id,
                    start_task_id=start_tid,
                    end_task_id=end_tid,
                    task_count=count,
                    risk_level=risk,
                    max_parallel_agents=parallel,
                    recommended_route=route,
                    notes=wave_notes,
                )
            )

    return entries


# --- Serializers ---


def wave_map_to_dict(entry: Prd500WaveMapEntry) -> Dict[str, Any]:
    return {
        "wave_id": entry.wave_id,
        "milestone_id": entry.milestone_id,
        "start_task_id": entry.start_task_id,
        "end_task_id": entry.end_task_id,
        "task_count": entry.task_count,
        "risk_level": entry.risk_level,
        "max_parallel_agents": entry.max_parallel_agents,
        "recommended_route": entry.recommended_route,
        "notes": list(entry.notes),
    }


def wave_map_to_markdown(entry: Prd500WaveMapEntry) -> str:
    lines: List[str] = []
    lines.append(f"## {entry.wave_id}")
    lines.append("")
    lines.append(f"- **Milestone:** {entry.milestone_id}")
    lines.append(f"- **Task range:** {entry.start_task_id} .. {entry.end_task_id}")
    lines.append(f"- **Task count:** {entry.task_count}")
    lines.append(f"- **Risk:** {entry.risk_level}")
    lines.append(f"- **Max parallel agents:** {entry.max_parallel_agents}")
    lines.append(f"- **Route:** {entry.recommended_route}")
    if entry.notes:
        lines.append("- **Notes:**")
        for note in entry.notes:
            lines.append(f"  - {note}")
    lines.append("")
    return "\n".join(lines)


# --- Summary ---


def summarize_wave_map(entries: List[Prd500WaveMapEntry]) -> Dict[str, Any]:
    total_tasks = 0
    risk_counts: Dict[str, int] = {}
    milestone_set: set = set()
    for e in entries:
        total_tasks += e.task_count
        risk_counts[e.risk_level] = risk_counts.get(e.risk_level, 0) + 1
        milestone_set.add(e.milestone_id)
    return {
        "wave_count": len(entries),
        "total_tasks": total_tasks,
        "milestone_count": len(milestone_set),
        "risk_counts": risk_counts,
    }
