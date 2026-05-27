"""PRD milestone planner — group backlog items into milestones.

T874. Pure deterministic, no I/O, no timestamps, no random.
"""

from dataclasses import dataclass
from typing import Any, Dict, List

from core.prd_backlog_schema import PrdBacklogItem
from core.prd_task_model import parse_task_number


# --- Dataclass ---


@dataclass(frozen=True)
class PrdMilestone:
    milestone_id: str
    title: str
    task_ids: List[str]
    risk_level: str
    status: str
    dependencies: List[str]
    recommended_execution_mode: str
    notes: List[str]


# --- Internal helpers ---


def _compute_risk_level(items: List[PrdBacklogItem]) -> str:
    """FROZEN > HIGH > MEDIUM > LOW."""
    has_frozen = any(i.risk_level == "FROZEN" for i in items)
    if has_frozen:
        return "FROZEN"
    has_high = any(i.risk_level == "HIGH" for i in items)
    if has_high:
        return "HIGH"
    has_medium = any(i.risk_level == "MEDIUM" for i in items)
    if has_medium:
        return "MEDIUM"
    return "LOW"


def _compute_execution_mode(task_count: int, risk_level: str) -> str:
    if risk_level == "FROZEN":
        return "HUMAN_REVIEW_REQUIRED"
    if task_count <= 15:
        return "SMALL_BATCH"
    return "PRO_MULTI_WAVE"


# --- Core function ---


def plan_milestones_from_backlog(
    items: List[PrdBacklogItem], max_tasks_per_milestone: int = 50
) -> List[PrdMilestone]:
    """Split backlog items into milestones respecting order and max size.

    Items are sorted by task number before grouping.
    """
    if not items:
        return []

    sorted_items = sorted(items, key=lambda i: parse_task_number(i.task_id))
    milestones: List[PrdMilestone] = []

    for chunk_start in range(0, len(sorted_items), max_tasks_per_milestone):
        chunk = sorted_items[chunk_start : chunk_start + max_tasks_per_milestone]
        task_ids = [i.task_id for i in chunk]
        risk = _compute_risk_level(chunk)
        mode = _compute_execution_mode(len(chunk), risk)
        first_id = task_ids[0]
        last_id = task_ids[-1]
        ms_id = f"MS-{first_id}-{last_id}"
        title = f"Milestone {first_id}..{last_id} ({len(chunk)} tasks)"

        # Collect unique dependencies not satisfied within this milestone
        internal_set = set(task_ids)
        deps: List[str] = []
        seen_deps: set = set()
        for item in chunk:
            for dep in item.dependencies:
                if dep not in internal_set and dep not in seen_deps:
                    deps.append(dep)
                    seen_deps.add(dep)

        notes = [
            f"Contains {len(chunk)} tasks",
            f"Risk level: {risk}",
            f"Execution mode: {mode}",
        ]

        milestones.append(
            PrdMilestone(
                milestone_id=ms_id,
                title=title,
                task_ids=task_ids,
                risk_level=risk,
                status="NOT_STARTED",
                dependencies=deps,
                recommended_execution_mode=mode,
                notes=notes,
            )
        )

    return milestones


# --- Serializers ---


def milestone_to_dict(milestone: PrdMilestone) -> Dict[str, Any]:
    return {
        "milestone_id": milestone.milestone_id,
        "title": milestone.title,
        "task_ids": list(milestone.task_ids),
        "risk_level": milestone.risk_level,
        "status": milestone.status,
        "dependencies": list(milestone.dependencies),
        "recommended_execution_mode": milestone.recommended_execution_mode,
        "notes": list(milestone.notes),
    }


def milestones_to_dict(milestones: List[PrdMilestone]) -> List[Dict[str, Any]]:
    return [milestone_to_dict(m) for m in milestones]


# --- Markdown ---


def milestone_to_markdown(milestone: PrdMilestone) -> str:
    lines: List[str] = []
    lines.append(f"## {milestone.milestone_id}: {milestone.title}")
    lines.append("")
    lines.append(f"- **Risk:** {milestone.risk_level}")
    lines.append(f"- **Status:** {milestone.status}")
    lines.append(f"- **Execution mode:** {milestone.recommended_execution_mode}")
    lines.append(f"- **Task count:** {len(milestone.task_ids)}")
    if milestone.dependencies:
        lines.append(f"- **Dependencies:** {', '.join(milestone.dependencies)}")
    if milestone.notes:
        lines.append("- **Notes:**")
        for note in milestone.notes:
            lines.append(f"  - {note}")
    lines.append("")
    lines.append("**Tasks:**")
    for tid in milestone.task_ids:
        lines.append(f"- {tid}")
    lines.append("")
    return "\n".join(lines)


def milestones_to_markdown(milestones: List[PrdMilestone]) -> str:
    lines: List[str] = []
    lines.append(f"# Milestones ({len(milestones)} total)")
    lines.append("")
    for ms in milestones:
        lines.append(milestone_to_markdown(ms))
    return "\n".join(lines)


# --- Summary ---


def summarize_milestones(milestones: List[PrdMilestone]) -> Dict[str, Any]:
    risk_counts: Dict[str, int] = {}
    mode_counts: Dict[str, int] = {}
    total_tasks = 0
    for ms in milestones:
        risk_counts[ms.risk_level] = risk_counts.get(ms.risk_level, 0) + 1
        mode_counts[ms.recommended_execution_mode] = (
            mode_counts.get(ms.recommended_execution_mode, 0) + 1
        )
        total_tasks += len(ms.task_ids)
    return {
        "total_milestones": len(milestones),
        "total_tasks": total_tasks,
        "risk_counts": risk_counts,
        "execution_mode_counts": mode_counts,
    }
