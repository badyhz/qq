"""PRD Backlog Milestone 6 Seed — T886.

M6: read-only hook implementation review.

Frozen dataclass + factory + serializers.
Pure deterministic, no I/O, no timestamps, no random.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class PrdMilestone6Seed:
    milestone_id: str
    title: str
    task_items: List[Dict[str, object]]
    notes: List[str]


MILESTONE6_TASK_ITEMS: List[Dict[str, object]] = [
    {
        "task_id": "T961",
        "title": "hook implementation review spec",
        "status": "NOT_STARTED",
        "risk_level": "HIGH",
        "dependencies": [],
    },
    {
        "task_id": "T964",
        "title": "hook code audit checklist",
        "status": "NOT_STARTED",
        "risk_level": "HIGH",
        "dependencies": ["T961"],
    },
    {
        "task_id": "T966",
        "title": "hook test coverage review",
        "status": "NOT_STARTED",
        "risk_level": "HIGH",
        "dependencies": ["T964"],
    },
    {
        "task_id": "T968",
        "title": "hook safety boundary verification",
        "status": "NOT_STARTED",
        "risk_level": "HIGH",
        "dependencies": ["T966"],
    },
    {
        "task_id": "T970",
        "title": "hook integration test plan",
        "status": "NOT_STARTED",
        "risk_level": "HIGH",
        "dependencies": ["T968"],
    },
    {
        "task_id": "T973",
        "title": "hook performance review",
        "status": "NOT_STARTED",
        "risk_level": "HIGH",
        "dependencies": ["T970"],
    },
    {
        "task_id": "T976",
        "title": "hook rollback verification",
        "status": "NOT_STARTED",
        "risk_level": "HIGH",
        "dependencies": ["T973"],
    },
    {
        "task_id": "T980",
        "title": "hook review closeout",
        "status": "NOT_STARTED",
        "risk_level": "HIGH",
        "dependencies": ["T976"],
    },
]


DEFAULT_MILESTONE6_NOTES: List[str] = [
    "M6 covers T961-T980: read-only hook implementation review",
    "all tasks NOT_STARTED, risk_level HIGH",
    "dependency chain: T961 -> T964 -> T966 -> T968 -> T970 -> T973 -> T976 -> T980",
    "frozen seed — no live execution",
]


def build_milestone6_seed(
    milestone_id: str = "M6",
    title: str = "M6: read-only hook implementation review",
    task_items: List[Dict[str, object]] | None = None,
    notes: List[str] | None = None,
) -> PrdMilestone6Seed:
    if task_items is None:
        task_items = [dict(item) for item in MILESTONE6_TASK_ITEMS]
    if notes is None:
        notes = list(DEFAULT_MILESTONE6_NOTES)
    return PrdMilestone6Seed(
        milestone_id=milestone_id,
        title=title,
        task_items=task_items,
        notes=notes,
    )


def milestone6_seed_to_dict(seed: PrdMilestone6Seed) -> Dict:
    return {
        "milestone_id": seed.milestone_id,
        "title": seed.title,
        "task_items": [dict(t) for t in seed.task_items],
        "notes": list(seed.notes),
    }


def milestone6_seed_to_markdown(seed: PrdMilestone6Seed) -> str:
    task_lines = "\n".join(
        f"| {t['task_id']} | {t['title']} | {t['status']} | "
        f"{t['risk_level']} | {', '.join(t['dependencies']) if t['dependencies'] else '-'} |"
        for t in seed.task_items
    )
    notes_lines = "\n".join(f"- {n}" for n in seed.notes)
    return (
        f"# {seed.milestone_id}: {seed.title}\n\n"
        f"**Milestone ID:** {seed.milestone_id}\n\n"
        f"## Task Items\n\n"
        f"| Task ID | Title | Status | Risk | Dependencies |\n"
        f"|---------|-------|--------|------|-------------|\n"
        f"{task_lines}\n\n"
        f"## Notes\n\n{notes_lines}\n"
    )
