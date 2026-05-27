"""PRD backlog schema — pure dataclasses for 500+ task backlogs.

T873. Pure deterministic, no I/O, no timestamps, no random.
"""

from dataclasses import dataclass
from typing import Any, Dict, List

from core.prd_task_model import VALID_RISK_LEVELS, VALID_STATUSES

# --- Dataclasses ---


@dataclass(frozen=True)
class PrdBacklogItem:
    task_id: str
    title: str
    milestone_id: str
    wave_id: str
    batch_id: str
    risk_level: str
    status: str
    dependencies: List[str]
    allowed_file_patterns: List[str]
    forbidden_file_patterns: List[str]
    acceptance_command_ids: List[str]
    notes: List[str]


@dataclass(frozen=True)
class PrdBacklog:
    backlog_id: str
    items: List[PrdBacklogItem]
    total_expected_tasks: int
    status: str
    notes: List[str]


# --- Factory ---


def build_backlog_item(
    task_id: str,
    title: str,
    milestone_id: str,
    wave_id: str,
    batch_id: str,
    risk_level: str,
    status: str,
    dependencies: List[str],
    allowed_file_patterns: List[str],
    forbidden_file_patterns: List[str],
    acceptance_command_ids: List[str],
    notes: List[str],
) -> PrdBacklogItem:
    """Build a PrdBacklogItem. Validates risk_level and status."""
    if risk_level not in VALID_RISK_LEVELS:
        raise ValueError(
            f"Invalid risk_level {risk_level!r}, must be one of {sorted(VALID_RISK_LEVELS)}"
        )
    if status not in VALID_STATUSES:
        raise ValueError(
            f"Invalid status {status!r}, must be one of {sorted(VALID_STATUSES)}"
        )
    return PrdBacklogItem(
        task_id=task_id,
        title=title,
        milestone_id=milestone_id,
        wave_id=wave_id,
        batch_id=batch_id,
        risk_level=risk_level,
        status=status,
        dependencies=list(dependencies),
        allowed_file_patterns=list(allowed_file_patterns),
        forbidden_file_patterns=list(forbidden_file_patterns),
        acceptance_command_ids=list(acceptance_command_ids),
        notes=list(notes),
    )


# --- Serializers ---


def backlog_item_to_dict(item: PrdBacklogItem) -> Dict[str, Any]:
    return {
        "task_id": item.task_id,
        "title": item.title,
        "milestone_id": item.milestone_id,
        "wave_id": item.wave_id,
        "batch_id": item.batch_id,
        "risk_level": item.risk_level,
        "status": item.status,
        "dependencies": list(item.dependencies),
        "allowed_file_patterns": list(item.allowed_file_patterns),
        "forbidden_file_patterns": list(item.forbidden_file_patterns),
        "acceptance_command_ids": list(item.acceptance_command_ids),
        "notes": list(item.notes),
    }


def backlog_to_dict(backlog: PrdBacklog) -> Dict[str, Any]:
    return {
        "backlog_id": backlog.backlog_id,
        "items": [backlog_item_to_dict(i) for i in backlog.items],
        "total_expected_tasks": backlog.total_expected_tasks,
        "status": backlog.status,
        "notes": list(backlog.notes),
    }


# --- Markdown ---


def backlog_item_to_markdown(item: PrdBacklogItem) -> str:
    lines: List[str] = []
    lines.append(f"## {item.task_id}: {item.title}")
    lines.append("")
    lines.append(f"- **Milestone:** {item.milestone_id}")
    lines.append(f"- **Wave:** {item.wave_id}")
    lines.append(f"- **Batch:** {item.batch_id}")
    lines.append(f"- **Status:** {item.status}")
    lines.append(f"- **Risk:** {item.risk_level}")
    if item.dependencies:
        lines.append(f"- **Dependencies:** {', '.join(item.dependencies)}")
    if item.allowed_file_patterns:
        lines.append(f"- **Allowed file patterns:** {', '.join(item.allowed_file_patterns)}")
    if item.forbidden_file_patterns:
        lines.append(f"- **Forbidden file patterns:** {', '.join(item.forbidden_file_patterns)}")
    if item.acceptance_command_ids:
        lines.append("- **Acceptance commands:**")
        for cmd_id in item.acceptance_command_ids:
            lines.append(f"  - `{cmd_id}`")
    if item.notes:
        lines.append("- **Notes:**")
        for note in item.notes:
            lines.append(f"  - {note}")
    lines.append("")
    return "\n".join(lines)


def backlog_to_markdown(backlog: PrdBacklog) -> str:
    lines: List[str] = []
    lines.append(f"# Backlog: {backlog.backlog_id}")
    lines.append(f"**Expected tasks:** {backlog.total_expected_tasks}")
    lines.append(f"**Actual items:** {len(backlog.items)}")
    lines.append(f"**Status:** {backlog.status}")
    lines.append("")
    if backlog.notes:
        lines.append("**Backlog notes:**")
        for note in backlog.notes:
            lines.append(f"- {note}")
        lines.append("")
    for item in backlog.items:
        lines.append(backlog_item_to_markdown(item))
    return "\n".join(lines)


# --- Summary ---


def summarize_backlog(backlog: PrdBacklog) -> Dict[str, Any]:
    status_counts: Dict[str, int] = {}
    risk_counts: Dict[str, int] = {}
    milestone_counts: Dict[str, int] = {}
    wave_counts: Dict[str, int] = {}
    for item in backlog.items:
        status_counts[item.status] = status_counts.get(item.status, 0) + 1
        risk_counts[item.risk_level] = risk_counts.get(item.risk_level, 0) + 1
        milestone_counts[item.milestone_id] = milestone_counts.get(item.milestone_id, 0) + 1
        wave_counts[item.wave_id] = wave_counts.get(item.wave_id, 0) + 1
    return {
        "backlog_id": backlog.backlog_id,
        "total_expected_tasks": backlog.total_expected_tasks,
        "actual_items": len(backlog.items),
        "status": backlog.status,
        "status_counts": status_counts,
        "risk_counts": risk_counts,
        "milestone_counts": milestone_counts,
        "wave_counts": wave_counts,
    }


# --- Validation ---


def validate_backlog_item_basic(item: PrdBacklogItem) -> List[str]:
    """Return list of validation issues. Empty list means valid."""
    issues: List[str] = []
    if not item.task_id:
        issues.append("task_id is empty")
    if not item.title:
        issues.append("title is empty")
    if not item.milestone_id:
        issues.append("milestone_id is empty")
    if not item.wave_id:
        issues.append("wave_id is empty")
    if not item.batch_id:
        issues.append("batch_id is empty")
    if item.risk_level not in VALID_RISK_LEVELS:
        issues.append(f"Invalid risk_level: {item.risk_level!r}")
    if item.status not in VALID_STATUSES:
        issues.append(f"Invalid status: {item.status!r}")
    return issues
