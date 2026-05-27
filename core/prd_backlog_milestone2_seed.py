"""PRD Backlog Milestone 2 Seed — T882.

Frozen seed for M2 (500-task planning layer) tasks T873-T880.
All items COMPLETED. Pure deterministic, no I/O, no timestamps, no random.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class PrdMilestone2Seed:
    milestone_id: str
    title: str
    task_items: List[Dict[str, str]]
    notes: List[str]


DEFAULT_TASK_ITEMS = [
    {
        "task_id": "T873",
        "title": "backlog schema",
        "status": "COMPLETED",
        "risk_level": "LOW",
        "dependencies": "[]",
    },
    {
        "task_id": "T874",
        "title": "milestone planner",
        "status": "COMPLETED",
        "risk_level": "MEDIUM",
        "dependencies": '["T873"]',
    },
    {
        "task_id": "T875",
        "title": "wave planner",
        "status": "COMPLETED",
        "risk_level": "MEDIUM",
        "dependencies": '["T874"]',
    },
    {
        "task_id": "T876",
        "title": "batch planner",
        "status": "COMPLETED",
        "risk_level": "MEDIUM",
        "dependencies": '["T875"]',
    },
    {
        "task_id": "T877",
        "title": "dependency graph validator",
        "status": "COMPLETED",
        "risk_level": "MEDIUM",
        "dependencies": '["T873"]',
    },
    {
        "task_id": "T878",
        "title": "task risk classifier",
        "status": "COMPLETED",
        "risk_level": "MEDIUM",
        "dependencies": '["T873"]',
    },
    {
        "task_id": "T879",
        "title": "execution window recommender",
        "status": "COMPLETED",
        "risk_level": "MEDIUM",
        "dependencies": '["T873", "T877"]',
    },
    {
        "task_id": "T880",
        "title": "seed packet",
        "status": "COMPLETED",
        "risk_level": "LOW",
        "dependencies": '["T873", "T874", "T875", "T876", "T877", "T878", "T879"]',
    },
]


def build_milestone2_seed(
    milestone_id: str = "M2",
    title: str = "500-task planning layer",
    task_items: List[Dict[str, str]] | None = None,
    notes: List[str] | None = None,
) -> PrdMilestone2Seed:
    if task_items is None:
        task_items = [dict(t) for t in DEFAULT_TASK_ITEMS]
    if notes is None:
        notes = [
            "M2 covers T873-T880 — all planning layer infrastructure",
            "all tasks COMPLETED",
            "DAG: T873 <- T874 <- T875 <- T876; T877, T878 depend on T873; T879 depends on T873+T877; T880 depends on all prior",
        ]
    return PrdMilestone2Seed(
        milestone_id=milestone_id,
        title=title,
        task_items=[dict(t) for t in task_items],
        notes=list(notes),
    )


def milestone2_seed_to_dict(seed: PrdMilestone2Seed) -> Dict:
    return {
        "milestone_id": seed.milestone_id,
        "title": seed.title,
        "task_items": [dict(t) for t in seed.task_items],
        "notes": list(seed.notes),
    }


def milestone2_seed_to_markdown(seed: PrdMilestone2Seed) -> str:
    header = (
        f"# Milestone {seed.milestone_id}: {seed.title}\n\n"
        f"**Total tasks:** {len(seed.task_items)}\n\n"
        f"## Task Items\n\n"
    )
    task_lines = []
    for t in seed.task_items:
        task_lines.append(
            f"- **{t['task_id']}** — {t['title']} "
            f"[{t['status']}] risk={t['risk_level']} deps={t['dependencies']}"
        )
    notes_lines = "\n".join(f"- {n}" for n in seed.notes)
    return (
        header
        + "\n".join(task_lines)
        + "\n\n## Notes\n\n"
        + notes_lines
        + "\n"
    )
