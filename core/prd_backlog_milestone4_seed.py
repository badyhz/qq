"""PRD Backlog Milestone 4 Seed — T884.

M4: offline evidence writer design.
Pure deterministic, no I/O, no timestamps, no random.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


# --- Dataclass ---


@dataclass(frozen=True)
class PrdMilestone4Seed:
    milestone_id: str
    title: str
    task_items: List[Dict[str, Any]]
    notes: List[str]


# --- Default task items ---


_DEFAULT_TASK_ITEMS: List[Dict[str, Any]] = [
    {
        "task_id": "T921",
        "title": "evidence writer schema",
        "status": "NOT_STARTED",
        "risk_level": "LOW",
        "dependencies": [],
    },
    {
        "task_id": "T922",
        "title": "evidence collector",
        "status": "NOT_STARTED",
        "risk_level": "LOW",
        "dependencies": ["T921"],
    },
    {
        "task_id": "T923",
        "title": "evidence validator",
        "status": "NOT_STARTED",
        "risk_level": "LOW",
        "dependencies": ["T922"],
    },
    {
        "task_id": "T924",
        "title": "evidence serializer",
        "status": "NOT_STARTED",
        "risk_level": "LOW",
        "dependencies": ["T923"],
    },
    {
        "task_id": "T925",
        "title": "evidence markdown renderer",
        "status": "NOT_STARTED",
        "risk_level": "LOW",
        "dependencies": ["T924"],
    },
    {
        "task_id": "T926",
        "title": "evidence storage design",
        "status": "NOT_STARTED",
        "risk_level": "LOW",
        "dependencies": ["T925"],
    },
    {
        "task_id": "T927",
        "title": "evidence retrieval design",
        "status": "NOT_STARTED",
        "risk_level": "LOW",
        "dependencies": ["T926"],
    },
    {
        "task_id": "T928",
        "title": "evidence closeout report",
        "status": "NOT_STARTED",
        "risk_level": "LOW",
        "dependencies": ["T927"],
    },
]


# --- Factory ---


def build_milestone4_seed(
    milestone_id: str = "M4",
    title: str = "offline evidence writer design",
    task_items: List[Dict[str, Any]] | None = None,
    notes: List[str] | None = None,
) -> PrdMilestone4Seed:
    if task_items is None:
        task_items = [dict(item) for item in _DEFAULT_TASK_ITEMS]
    if notes is None:
        notes = [
            "M4 covers offline evidence writer design tasks T921-T940",
            "all tasks NOT_STARTED, risk LOW",
            "dependencies form a chain within the milestone",
        ]
    return PrdMilestone4Seed(
        milestone_id=milestone_id,
        title=title,
        task_items=[dict(t) for t in task_items],
        notes=list(notes),
    )


# --- Serializers ---


def milestone4_seed_to_dict(seed: PrdMilestone4Seed) -> Dict[str, Any]:
    return {
        "milestone_id": seed.milestone_id,
        "title": seed.title,
        "task_items": [dict(t) for t in seed.task_items],
        "notes": list(seed.notes),
    }


def milestone4_seed_to_markdown(seed: PrdMilestone4Seed) -> str:
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
