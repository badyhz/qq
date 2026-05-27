"""PRD task model — pure dataclasses for task queue items.

T865. Pure deterministic, no I/O, no timestamps, no random.
"""

from dataclasses import dataclass
from typing import Any, Dict, List

# --- Constants ---

VALID_STATUSES = frozenset({
    "COMPLETED",
    "NOT_STARTED",
    "HUMAN_REVIEW_REQUIRED",
    "IN_PROGRESS",
    "BLOCKED",
    "PARTIAL",
})

VALID_RISK_LEVELS = frozenset({
    "LOW",
    "MEDIUM",
    "HIGH",
    "FROZEN",
})


# --- Dataclasses ---


@dataclass(frozen=True)
class PrdTask:
    task_id: str
    title: str
    status: str
    allowed_files: List[str]
    dependencies: List[str]
    acceptance_commands: List[str]
    risk_level: str
    notes: List[str]


@dataclass(frozen=True)
class PrdTaskRange:
    start_task_id: str
    end_task_id: str
    tasks: List[PrdTask]
    hard_stop_task_id: str
    notes: List[str]


# --- Helpers ---


def parse_task_number(task_id: str) -> int:
    """Extract numeric part from task_id (e.g. 'T865' -> 865)."""
    if not validate_task_id(task_id):
        raise ValueError(f"Invalid task_id format: {task_id!r}")
    return int(task_id[1:])


def validate_task_id(task_id: str) -> bool:
    """Return True if task_id matches T<digits>."""
    if not isinstance(task_id, str) or len(task_id) < 2:
        return False
    if task_id[0] != "T":
        return False
    return task_id[1:].isdigit()


# --- Serializers ---


def task_to_dict(task: PrdTask) -> Dict[str, Any]:
    return {
        "task_id": task.task_id,
        "title": task.title,
        "status": task.status,
        "allowed_files": list(task.allowed_files),
        "dependencies": list(task.dependencies),
        "acceptance_commands": list(task.acceptance_commands),
        "risk_level": task.risk_level,
        "notes": list(task.notes),
    }


def task_range_to_dict(task_range: PrdTaskRange) -> Dict[str, Any]:
    return {
        "start_task_id": task_range.start_task_id,
        "end_task_id": task_range.end_task_id,
        "tasks": [task_to_dict(t) for t in task_range.tasks],
        "hard_stop_task_id": task_range.hard_stop_task_id,
        "notes": list(task_range.notes),
    }


# --- Markdown ---


def task_to_markdown(task: PrdTask) -> str:
    lines: List[str] = []
    lines.append(f"## {task.task_id}: {task.title}")
    lines.append("")
    lines.append(f"- **Status:** {task.status}")
    lines.append(f"- **Risk:** {task.risk_level}")
    if task.allowed_files:
        lines.append(f"- **Allowed files:** {', '.join(task.allowed_files)}")
    if task.dependencies:
        lines.append(f"- **Dependencies:** {', '.join(task.dependencies)}")
    if task.acceptance_commands:
        lines.append("- **Acceptance commands:**")
        for cmd in task.acceptance_commands:
            lines.append(f"  - `{cmd}`")
    if task.notes:
        lines.append("- **Notes:**")
        for note in task.notes:
            lines.append(f"  - {note}")
    lines.append("")
    return "\n".join(lines)


def task_range_to_markdown(task_range: PrdTaskRange) -> str:
    lines: List[str] = []
    lines.append(
        f"# Task Range: {task_range.start_task_id} .. {task_range.end_task_id}"
    )
    lines.append(f"**Hard stop:** {task_range.hard_stop_task_id}")
    lines.append("")
    if task_range.notes:
        lines.append("**Range notes:**")
        for note in task_range.notes:
            lines.append(f"- {note}")
        lines.append("")
    for task in task_range.tasks:
        lines.append(task_to_markdown(task))
    return "\n".join(lines)


# --- Summary ---


def summarize_task_range(task_range: PrdTaskRange) -> Dict[str, Any]:
    status_counts: Dict[str, int] = {}
    risk_counts: Dict[str, int] = {}
    for task in task_range.tasks:
        status_counts[task.status] = status_counts.get(task.status, 0) + 1
        risk_counts[task.risk_level] = risk_counts.get(task.risk_level, 0) + 1
    return {
        "total": len(task_range.tasks),
        "status_counts": status_counts,
        "risk_counts": risk_counts,
        "start_task_id": task_range.start_task_id,
        "end_task_id": task_range.end_task_id,
        "hard_stop_task_id": task_range.hard_stop_task_id,
    }
