"""PRD batch planner — split waves into small batches for safer execution.

T876. Pure deterministic, no I/O, no timestamps, no random.
"""

from dataclasses import dataclass
from typing import Any, Dict, List

from core.prd_wave_planner import PrdWave


# --- Dataclass ---


@dataclass(frozen=True)
class PrdBatch:
    batch_id: str
    wave_id: str
    task_ids: List[str]
    execution_order: int
    risk_level: str
    recommended_agent_count: int
    hard_stop_task_id: str
    notes: List[str]


# --- Internal helpers ---


def _resolve_agent_count(risk_level: str, base_parallel: int) -> int:
    """Max agents for a batch based on risk level."""
    if risk_level == "FROZEN":
        return 0
    if risk_level == "HIGH":
        return min(base_parallel, 2)
    return base_parallel


# --- Core function ---


def plan_batches_for_wave(
    wave: PrdWave, max_tasks_per_batch: int = 5
) -> List[PrdBatch]:
    """Split wave tasks into batches respecting max size.

    Preserves task ordering from the wave.
    """
    task_ids = list(wave.task_ids)
    if not task_ids:
        return []

    risk = wave.risk_level
    batches: List[PrdBatch] = []

    for chunk_start in range(0, len(task_ids), max_tasks_per_batch):
        chunk = task_ids[chunk_start : chunk_start + max_tasks_per_batch]
        batch_index = len(batches)
        batch_id = f"{wave.wave_id}-B{batch_index}"
        agent_count = _resolve_agent_count(risk, wave.max_parallel_agents)
        hard_stop = chunk[-1]

        notes: List[str] = []
        if risk == "FROZEN":
            notes.append("Human approval required before execution")
        notes.append(f"Batch {batch_index} of wave {wave.wave_id}")
        notes.append(f"Tasks: {len(chunk)}")

        batches.append(
            PrdBatch(
                batch_id=batch_id,
                wave_id=wave.wave_id,
                task_ids=chunk,
                execution_order=batch_index,
                risk_level=risk,
                recommended_agent_count=agent_count,
                hard_stop_task_id=hard_stop,
                notes=notes,
            )
        )

    return batches


# --- Serializers ---


def batch_to_dict(batch: PrdBatch) -> Dict[str, Any]:
    return {
        "batch_id": batch.batch_id,
        "wave_id": batch.wave_id,
        "task_ids": list(batch.task_ids),
        "execution_order": batch.execution_order,
        "risk_level": batch.risk_level,
        "recommended_agent_count": batch.recommended_agent_count,
        "hard_stop_task_id": batch.hard_stop_task_id,
        "notes": list(batch.notes),
    }


def batches_to_dict(batches: List[PrdBatch]) -> List[Dict[str, Any]]:
    return [batch_to_dict(b) for b in batches]


# --- Markdown ---


def batch_to_markdown(batch: PrdBatch) -> str:
    lines: List[str] = []
    lines.append(f"### {batch.batch_id}")
    lines.append("")
    lines.append(f"- **Wave:** {batch.wave_id}")
    lines.append(f"- **Execution order:** {batch.execution_order}")
    lines.append(f"- **Risk:** {batch.risk_level}")
    lines.append(f"- **Agents:** {batch.recommended_agent_count}")
    lines.append(f"- **Hard stop task:** {batch.hard_stop_task_id}")
    lines.append(f"- **Task count:** {len(batch.task_ids)}")
    if batch.notes:
        lines.append("- **Notes:**")
        for note in batch.notes:
            lines.append(f"  - {note}")
    lines.append("")
    lines.append("**Tasks:**")
    for tid in batch.task_ids:
        lines.append(f"- {tid}")
    lines.append("")
    return "\n".join(lines)


def batches_to_markdown(batches: List[PrdBatch]) -> str:
    lines: List[str] = []
    lines.append(f"# Execution Batches ({len(batches)} total)")
    lines.append("")
    for b in batches:
        lines.append(batch_to_markdown(b))
    return "\n".join(lines)


# --- Summary ---


def summarize_batches(batches: List[PrdBatch]) -> Dict[str, Any]:
    risk_counts: Dict[str, int] = {}
    total_tasks = 0
    total_agents = 0
    for b in batches:
        risk_counts[b.risk_level] = risk_counts.get(b.risk_level, 0) + 1
        total_tasks += len(b.task_ids)
        total_agents += b.recommended_agent_count
    return {
        "total_batches": len(batches),
        "total_tasks": total_tasks,
        "risk_counts": risk_counts,
        "total_recommended_agents": total_agents,
    }
