"""T848: Runtime governance read-only future task queue.

Generate future tasks as data only. Pure, deterministic, no I/O,
no timestamps, no random.
"""

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(frozen=True)
class RuntimeGovernanceReadOnlyFutureTask:
    task_id: str
    title: str
    risk_level: str  # "low", "medium", "high", "critical"
    status: str  # "queued", "blocked", "ready"
    dependencies: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)


def build_readonly_future_task_queue() -> List[RuntimeGovernanceReadOnlyFutureTask]:
    """Build deterministic future task queue."""
    return [
        RuntimeGovernanceReadOnlyFutureTask(
            task_id="FUTURE-RO-001",
            title="implement read-only hook prototype",
            risk_level="high",
            status="blocked",
            dependencies=["manual approval", "readiness score >= B"],
            notes=[],
        ),
        RuntimeGovernanceReadOnlyFutureTask(
            task_id="FUTURE-RO-002",
            title="add pure adapter facade",
            risk_level="medium",
            status="blocked",
            dependencies=["read-only hook prototype"],
            notes=[],
        ),
        RuntimeGovernanceReadOnlyFutureTask(
            task_id="FUTURE-RO-003",
            title="add manual review CLI",
            risk_level="low",
            status="queued",
            dependencies=["pure adapter facade"],
            notes=[],
        ),
        RuntimeGovernanceReadOnlyFutureTask(
            task_id="FUTURE-RO-004",
            title="add observability hooks",
            risk_level="medium",
            status="queued",
            dependencies=["read-only hook prototype"],
            notes=[],
        ),
        RuntimeGovernanceReadOnlyFutureTask(
            task_id="FUTURE-RO-005",
            title="add threat model validation",
            risk_level="high",
            status="queued",
            dependencies=["observability hooks"],
            notes=[],
        ),
    ]


def readonly_future_task_queue_to_dict(
    tasks: List[RuntimeGovernanceReadOnlyFutureTask],
) -> List[Dict]:
    """Convert task list to list of dicts."""
    return [
        {
            "task_id": t.task_id,
            "title": t.title,
            "risk_level": t.risk_level,
            "status": t.status,
            "dependencies": list(t.dependencies),
            "notes": list(t.notes),
        }
        for t in tasks
    ]


def readonly_future_task_queue_to_markdown(
    tasks: List[RuntimeGovernanceReadOnlyFutureTask],
) -> str:
    """Convert task list to markdown table."""
    lines = [
        "# Runtime Governance Read-Only Future Task Queue",
        "",
        "| task_id | title | risk_level | status | dependencies | notes |",
        "|---------|-------|------------|--------|--------------|-------|",
    ]
    for t in tasks:
        deps = ", ".join(t.dependencies) if t.dependencies else "-"
        notes = ", ".join(t.notes) if t.notes else "-"
        lines.append(
            f"| {t.task_id} | {t.title} | {t.risk_level} | {t.status} | {deps} | {notes} |"
        )
    lines.append("")
    return "\n".join(lines)
