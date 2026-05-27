"""PRD Backlog Milestone 5 Seed — T885.

M5: manual review CLI design.
Pure deterministic, no I/O, no timestamps, no random.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


# --- Dataclass ---


@dataclass(frozen=True)
class PrdMilestone5Seed:
    milestone_id: str
    title: str
    task_items: List[Dict[str, Any]]
    notes: List[str]


# --- Default task items ---


_DEFAULT_TASK_ITEMS: List[Dict[str, Any]] = [
    {
        "task_id": "T941",
        "title": "manual review CLI spec",
        "status": "NOT_STARTED",
        "risk_level": "MEDIUM",
        "dependencies": [],
    },
    {
        "task_id": "T942",
        "title": "review command parser",
        "status": "NOT_STARTED",
        "risk_level": "MEDIUM",
        "dependencies": ["T941"],
    },
    {
        "task_id": "T943",
        "title": "review approval handler",
        "status": "NOT_STARTED",
        "risk_level": "MEDIUM",
        "dependencies": ["T942"],
    },
    {
        "task_id": "T944",
        "title": "review rejection handler",
        "status": "NOT_STARTED",
        "risk_level": "MEDIUM",
        "dependencies": ["T942"],
    },
    {
        "task_id": "T945",
        "title": "review status tracker",
        "status": "NOT_STARTED",
        "risk_level": "MEDIUM",
        "dependencies": ["T943", "T944"],
    },
    {
        "task_id": "T946",
        "title": "review batch handler",
        "status": "NOT_STARTED",
        "risk_level": "MEDIUM",
        "dependencies": ["T945"],
    },
    {
        "task_id": "T947",
        "title": "review report generator",
        "status": "NOT_STARTED",
        "risk_level": "MEDIUM",
        "dependencies": ["T946"],
    },
    {
        "task_id": "T948",
        "title": "review closeout report",
        "status": "NOT_STARTED",
        "risk_level": "MEDIUM",
        "dependencies": ["T947"],
    },
]


# --- Factory ---


def build_milestone5_seed(
    milestone_id: str = "M5",
    title: str = "manual review CLI design",
    task_items: List[Dict[str, Any]] | None = None,
    notes: List[str] | None = None,
) -> PrdMilestone5Seed:
    if task_items is None:
        task_items = [dict(item) for item in _DEFAULT_TASK_ITEMS]
    if notes is None:
        notes = [
            "M5 covers manual review CLI design tasks T941-T960",
            "all tasks NOT_STARTED, risk MEDIUM (CLI execution keyword)",
            "dependencies form a DAG with approval/rejection branching at T943/T944",
        ]
    return PrdMilestone5Seed(
        milestone_id=milestone_id,
        title=title,
        task_items=[dict(t) for t in task_items],
        notes=list(notes),
    )


# --- Serializers ---


def milestone5_seed_to_dict(seed: PrdMilestone5Seed) -> Dict[str, Any]:
    return {
        "milestone_id": seed.milestone_id,
        "title": seed.title,
        "task_items": [dict(t) for t in seed.task_items],
        "notes": list(seed.notes),
    }


def milestone5_seed_to_markdown(seed: PrdMilestone5Seed) -> str:
    lines: List[str] = []
    lines.append(f"# {seed.milestone_id}: {seed.title}")
    lines.append("")
    lines.append(f"**Task count:** {len(seed.task_items)}")
    lines.append("")
    if seed.task_items:
        lines.append("## Task Items")
        lines.append("")
        for item in seed.task_items:
            deps = item.get("dependencies", [])
            dep_str = ", ".join(deps) if deps else "none"
            lines.append(
                f"- **{item['task_id']}** — {item['title']} "
                f"[{item['status']}] risk={item['risk_level']} deps={dep_str}"
            )
        lines.append("")
    if seed.notes:
        lines.append("## Notes")
        lines.append("")
        for note in seed.notes:
            lines.append(f"- {note}")
        lines.append("")
    return "\n".join(lines)
