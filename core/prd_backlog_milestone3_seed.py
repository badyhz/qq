"""Milestone 3 seed tasks — read-only hook prototype design (T826-T857).

T883. Pure deterministic, no I/O, no timestamps, no random.
Groups 32 completed design tasks into 8 logical sub-ranges.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


# --- Dataclasses ---


@dataclass(frozen=True)
class PrdMilestone3Seed:
    milestone_id: str
    title: str
    task_items: List[Dict[str, Any]]
    notes: List[str]


# --- Constants ---

MILESTONE3_ID = "M3"
MILESTONE3_TITLE = "read-only hook prototype design"

_TASK_ITEMS: List[Dict[str, Any]] = [
    {
        "task_id": "T826-T829",
        "title": "hook specs + adapter contracts",
        "status": "COMPLETED",
        "risk_level": "LOW",
        "dependencies": [],
    },
    {
        "task_id": "T830-T833",
        "title": "permission envelopes + sanitized views",
        "status": "COMPLETED",
        "risk_level": "LOW",
        "dependencies": ["T826-T829"],
    },
    {
        "task_id": "T834-T837",
        "title": "side-effect declarations + scenario catalogs",
        "status": "COMPLETED",
        "risk_level": "LOW",
        "dependencies": ["T830-T833"],
    },
    {
        "task_id": "T838-T840",
        "title": "invariant checkers + stack manifests",
        "status": "COMPLETED",
        "risk_level": "LOW",
        "dependencies": ["T834-T837"],
    },
    {
        "task_id": "T841-T844",
        "title": "scenario evaluators + regression packets + readiness scores",
        "status": "COMPLETED",
        "risk_level": "LOW",
        "dependencies": ["T838-T840"],
    },
    {
        "task_id": "T845-T849",
        "title": "blocker summaries + phase control reports + evidence packets + transition checklists + closeout bundles",
        "status": "COMPLETED",
        "risk_level": "LOW",
        "dependencies": ["T841-T844"],
    },
    {
        "task_id": "T850-T853",
        "title": "manual review packets + implementation boundaries + approval forms + rollback plans",
        "status": "COMPLETED",
        "risk_level": "LOW",
        "dependencies": ["T845-T849"],
    },
    {
        "task_id": "T854-T857",
        "title": "observability designs + threat models + future task queues + engineering closeouts + final status reports",
        "status": "COMPLETED",
        "risk_level": "LOW",
        "dependencies": ["T850-T853"],
    },
]

_NOTES: List[str] = [
    "M3 covers T826-T857 (32 tasks), all design-only, no runtime code",
    "all items COMPLETED — read-only integration design layer is frozen",
    "risk LOW — no live trading artifacts, pure design documentation",
    "groups abbreviated to 8 logical sub-ranges per T883 spec",
]


# --- Factory ---


def build_milestone3_seed(
    milestone_id: str = MILESTONE3_ID,
    title: str = MILESTONE3_TITLE,
    task_items: List[Dict[str, Any]] | None = None,
    notes: List[str] | None = None,
) -> PrdMilestone3Seed:
    """Build M3 seed. Validates all items are COMPLETED / LOW."""
    if task_items is None:
        task_items = [dict(t) for t in _TASK_ITEMS]
    if notes is None:
        notes = list(_NOTES)
    for item in task_items:
        if item.get("status") != "COMPLETED":
            raise ValueError(
                f"Task {item.get('task_id')!r} has status {item.get('status')!r}, "
                "expected COMPLETED"
            )
        if item.get("risk_level") != "LOW":
            raise ValueError(
                f"Task {item.get('task_id')!r} has risk_level {item.get('risk_level')!r}, "
                "expected LOW"
            )
    return PrdMilestone3Seed(
        milestone_id=milestone_id,
        title=title,
        task_items=[dict(t) for t in task_items],
        notes=list(notes),
    )


# --- Serializers ---


def milestone3_seed_to_dict(seed: PrdMilestone3Seed) -> Dict[str, Any]:
    return {
        "milestone_id": seed.milestone_id,
        "title": seed.title,
        "task_items": [dict(t) for t in seed.task_items],
        "notes": list(seed.notes),
    }


def milestone3_seed_to_markdown(seed: PrdMilestone3Seed) -> str:
    lines: List[str] = []
    lines.append(f"# Milestone {seed.milestone_id}: {seed.title}")
    lines.append("")
    lines.append("## Task Items")
    lines.append("")
    for item in seed.task_items:
        deps = item.get("dependencies", [])
        dep_str = f" (deps: {', '.join(deps)})" if deps else ""
        lines.append(
            f"- **{item['task_id']}** — {item['title']} "
            f"[{item['status']}] [{item['risk_level']}]{dep_str}"
        )
    lines.append("")
    if seed.notes:
        lines.append("## Notes")
        lines.append("")
        for note in seed.notes:
            lines.append(f"- {note}")
        lines.append("")
    return "\n".join(lines)
