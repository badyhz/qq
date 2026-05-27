"""PRD wave planner — split milestones into execution waves.

T875. Pure deterministic, no I/O, no timestamps, no random.
"""

from dataclasses import dataclass
from typing import Any, Dict, List

from core.prd_milestone_planner import PrdMilestone


# --- Dataclass ---


@dataclass(frozen=True)
class PrdWave:
    wave_id: str
    milestone_id: str
    task_ids: List[str]
    max_parallel_agents: int
    dependency_notes: List[str]
    risk_level: str
    recommended_route: str
    notes: List[str]


# --- Internal helpers ---


def _resolve_parallelism(risk_level: str) -> int:
    """Max parallel agents based on risk level."""
    if risk_level == "FROZEN":
        return 0
    if risk_level == "HIGH":
        return 3
    # LOW / MEDIUM
    return 8


def _resolve_route(risk_level: str, task_count: int, has_external_deps: bool) -> str:
    """Recommended execution route."""
    if risk_level == "FROZEN":
        return "HUMAN_ONLY"
    if risk_level == "HIGH" or has_external_deps:
        return "mimo2.5pro"
    # LOW/MEDIUM small wave
    return "mimo2.5"


# --- Core function ---


def plan_waves_for_milestone(
    milestone: PrdMilestone, max_tasks_per_wave: int = 10
) -> List[PrdWave]:
    """Split milestone tasks into waves respecting max size.

    Preserves task ordering from the milestone.
    """
    task_ids = list(milestone.task_ids)
    if not task_ids:
        return []

    risk = milestone.risk_level
    waves: List[PrdWave] = []
    has_ext_deps = len(milestone.dependencies) > 0

    for chunk_start in range(0, len(task_ids), max_tasks_per_wave):
        chunk = task_ids[chunk_start : chunk_start + max_tasks_per_wave]
        wave_index = len(waves)
        wave_id = f"{milestone.milestone_id}-W{wave_index}"
        parallel = _resolve_parallelism(risk)
        route = _resolve_route(risk, len(chunk), has_ext_deps)

        # Dependency notes: external deps on first wave only
        dep_notes: List[str] = []
        if wave_index == 0 and milestone.dependencies:
            dep_notes.append(
                f"External dependencies: {', '.join(milestone.dependencies)}"
            )

        notes = [
            f"Wave {wave_index} of {milestone.milestone_id}",
            f"Tasks: {len(chunk)}",
            f"Risk: {risk}",
            f"Parallel agents: {parallel}",
            f"Route: {route}",
        ]

        waves.append(
            PrdWave(
                wave_id=wave_id,
                milestone_id=milestone.milestone_id,
                task_ids=chunk,
                max_parallel_agents=parallel,
                dependency_notes=dep_notes,
                risk_level=risk,
                recommended_route=route,
                notes=notes,
            )
        )

    return waves


# --- Serializers ---


def wave_to_dict(wave: PrdWave) -> Dict[str, Any]:
    return {
        "wave_id": wave.wave_id,
        "milestone_id": wave.milestone_id,
        "task_ids": list(wave.task_ids),
        "max_parallel_agents": wave.max_parallel_agents,
        "dependency_notes": list(wave.dependency_notes),
        "risk_level": wave.risk_level,
        "recommended_route": wave.recommended_route,
        "notes": list(wave.notes),
    }


def waves_to_dict(waves: List[PrdWave]) -> List[Dict[str, Any]]:
    return [wave_to_dict(w) for w in waves]


# --- Markdown ---


def wave_to_markdown(wave: PrdWave) -> str:
    lines: List[str] = []
    lines.append(f"### {wave.wave_id}")
    lines.append("")
    lines.append(f"- **Milestone:** {wave.milestone_id}")
    lines.append(f"- **Risk:** {wave.risk_level}")
    lines.append(f"- **Parallel agents:** {wave.max_parallel_agents}")
    lines.append(f"- **Route:** {wave.recommended_route}")
    lines.append(f"- **Task count:** {len(wave.task_ids)}")
    if wave.dependency_notes:
        lines.append("- **Dependencies:**")
        for dep in wave.dependency_notes:
            lines.append(f"  - {dep}")
    if wave.notes:
        lines.append("- **Notes:**")
        for note in wave.notes:
            lines.append(f"  - {note}")
    lines.append("")
    lines.append("**Tasks:**")
    for tid in wave.task_ids:
        lines.append(f"- {tid}")
    lines.append("")
    return "\n".join(lines)


def waves_to_markdown(waves: List[PrdWave]) -> str:
    lines: List[str] = []
    lines.append(f"# Execution Waves ({len(waves)} total)")
    lines.append("")
    for w in waves:
        lines.append(wave_to_markdown(w))
    return "\n".join(lines)


# --- Summary ---


def summarize_waves(waves: List[PrdWave]) -> Dict[str, Any]:
    risk_counts: Dict[str, int] = {}
    route_counts: Dict[str, int] = {}
    total_tasks = 0
    for w in waves:
        risk_counts[w.risk_level] = risk_counts.get(w.risk_level, 0) + 1
        route_counts[w.recommended_route] = (
            route_counts.get(w.recommended_route, 0) + 1
        )
        total_tasks += len(w.task_ids)
    return {
        "total_waves": len(waves),
        "total_tasks": total_tasks,
        "risk_counts": risk_counts,
        "route_counts": route_counts,
    }
