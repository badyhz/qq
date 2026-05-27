"""Runtime governance future task planner — pure data, no I/O."""

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass(frozen=True)
class RuntimeGovernanceFutureTask:
    task_id: str
    title: str
    risk_level: str  # "low", "medium", "high", "critical"
    dependencies: List[str]
    allowed_files_hint: List[str]
    notes: str


_TASKS = [
    {
        "task_id": "runtime_readonly_hook",
        "title": "Runtime read-only hook design",
        "risk_level": "high",
        "dependencies": [],
        "allowed_files_hint": [],
        "notes": "HOLD — requires manual approval",
    },
    {
        "task_id": "no_submit_assertion",
        "title": "No-submit assertion wrapper",
        "risk_level": "high",
        "dependencies": [],
        "allowed_files_hint": [],
        "notes": "HOLD — requires manual approval",
    },
    {
        "task_id": "dry_run_evidence_writer",
        "title": "Dry-run evidence writer design",
        "risk_level": "medium",
        "dependencies": [],
        "allowed_files_hint": [],
        "notes": "",
    },
    {
        "task_id": "manual_approval_cli",
        "title": "Manual approval CLI design",
        "risk_level": "high",
        "dependencies": [],
        "allowed_files_hint": [],
        "notes": "HOLD — requires manual approval",
    },
    {
        "task_id": "planner_integration_review",
        "title": "Planner integration review only",
        "risk_level": "high",
        "dependencies": [],
        "allowed_files_hint": [],
        "notes": "HOLD — requires manual approval",
    },
    {
        "task_id": "live_submit_frozen",
        "title": "Live submit remains frozen",
        "risk_level": "critical",
        "dependencies": [],
        "allowed_files_hint": [],
        "notes": "HOLD — requires manual approval",
    },
]


def build_runtime_governance_future_task_plan() -> List[RuntimeGovernanceFutureTask]:
    """Return 6 future task candidates as data only."""
    return [RuntimeGovernanceFutureTask(**t) for t in _TASKS]


def future_task_plan_to_dict(
    tasks: List[RuntimeGovernanceFutureTask],
) -> List[Dict[str, Any]]:
    """Serialize task list to list of dicts."""
    return [
        {
            "task_id": t.task_id,
            "title": t.title,
            "risk_level": t.risk_level,
            "dependencies": t.dependencies,
            "allowed_files_hint": t.allowed_files_hint,
            "notes": t.notes,
        }
        for t in tasks
    ]


def future_task_plan_to_markdown(
    tasks: List[RuntimeGovernanceFutureTask],
) -> str:
    """Deterministic markdown table of future tasks."""
    lines = [
        "# Runtime Governance Future Task Plan",
        "",
        "| # | Task ID | Title | Risk | Dependencies | Allowed Files | Notes |",
        "|---|---------|-------|------|--------------|---------------|-------|",
    ]
    for idx, t in enumerate(tasks, 1):
        deps = ", ".join(t.dependencies) if t.dependencies else "—"
        files = ", ".join(t.allowed_files_hint) if t.allowed_files_hint else "—"
        notes = t.notes if t.notes else "—"
        lines.append(
            f"| {idx} | {t.task_id} | {t.title} | {t.risk_level} | {deps} | {files} | {notes} |"
        )
    lines.append("")
    return "\n".join(lines)
