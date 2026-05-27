"""PRD Backlog Milestone 7 Seed — T887.

M7: runtime integration review.

Frozen dataclass + factory + serializers.
Pure deterministic, no I/O, no timestamps, no random.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class PrdMilestone7Seed:
    milestone_id: str
    title: str
    task_items: List[Dict[str, object]]
    notes: List[str]


MILESTONE7_TASK_ITEMS: List[Dict[str, object]] = [
    {
        "task_id": "T981",
        "title": "runtime integration review spec",
        "status": "NOT_STARTED",
        "risk_level": "HIGH",
        "dependencies": [],
    },
    {
        "task_id": "T984",
        "title": "runtime adapter audit",
        "status": "NOT_STARTED",
        "risk_level": "HIGH",
        "dependencies": ["T981"],
    },
    {
        "task_id": "T986",
        "title": "runtime permission verification",
        "status": "NOT_STARTED",
        "risk_level": "HIGH",
        "dependencies": ["T984"],
    },
    {
        "task_id": "T989",
        "title": "runtime safety boundary test",
        "status": "NOT_STARTED",
        "risk_level": "HIGH",
        "dependencies": ["T986"],
    },
    {
        "task_id": "T991",
        "title": "runtime integration test plan",
        "status": "NOT_STARTED",
        "risk_level": "HIGH",
        "dependencies": ["T989"],
    },
    {
        "task_id": "T994",
        "title": "runtime performance review",
        "status": "NOT_STARTED",
        "risk_level": "HIGH",
        "dependencies": ["T991"],
    },
    {
        "task_id": "T997",
        "title": "runtime rollback verification",
        "status": "NOT_STARTED",
        "risk_level": "HIGH",
        "dependencies": ["T994"],
    },
    {
        "task_id": "T1000",
        "title": "runtime review closeout",
        "status": "NOT_STARTED",
        "risk_level": "HIGH",
        "dependencies": ["T997"],
    },
]


DEFAULT_MILESTONE7_NOTES: List[str] = [
    "M7 covers T981-T1000: runtime integration review",
    "all tasks NOT_STARTED, risk_level HIGH",
    "dependency chain: T981 -> T984 -> T986 -> T989 -> T991 -> T994 -> T997 -> T1000",
    "frozen seed — no live execution",
]


def build_milestone7_seed(
    milestone_id: str = "M7",
    title: str = "M7: runtime integration review",
    task_items: List[Dict[str, object]] | None = None,
    notes: List[str] | None = None,
) -> PrdMilestone7Seed:
    if task_items is None:
        task_items = [dict(item) for item in MILESTONE7_TASK_ITEMS]
    if notes is None:
        notes = list(DEFAULT_MILESTONE7_NOTES)
    return PrdMilestone7Seed(
        milestone_id=milestone_id,
        title=title,
        task_items=task_items,
        notes=notes,
    )


def milestone7_seed_to_dict(seed: PrdMilestone7Seed) -> Dict:
    return {
        "milestone_id": seed.milestone_id,
        "title": seed.title,
        "task_items": [dict(t) for t in seed.task_items],
        "notes": list(seed.notes),
    }


def milestone7_seed_to_markdown(seed: PrdMilestone7Seed) -> str:
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
