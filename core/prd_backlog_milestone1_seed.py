"""PRD Backlog Milestone 1 Seed — T881.

Defines M1 (PRD automation control plane) seed tasks as frozen dataclasses.
Covers T858-T880. All items COMPLETED. Pure deterministic, no I/O.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


# --- Dataclasses ---


@dataclass(frozen=True)
class PrdMilestone1Seed:
    milestone_id: str
    title: str
    task_items: List[Dict[str, Any]]
    notes: List[str]


# --- Defaults ---

DEFAULT_M1_TASKS: List[Dict[str, Any]] = [
    {
        "task_id": "T858",
        "title": "PRD task model — define core dataclass schema",
        "status": "COMPLETED",
        "risk_level": "LOW",
        "dependencies": [],
    },
    {
        "task_id": "T859",
        "title": "PRD task model — status/risk enums and validation",
        "status": "COMPLETED",
        "risk_level": "MEDIUM",
        "dependencies": ["T858"],
    },
    {
        "task_id": "T860",
        "title": "PRD task model — to_dict and to_markdown serializers",
        "status": "COMPLETED",
        "risk_level": "LOW",
        "dependencies": ["T858"],
    },
    {
        "task_id": "T861",
        "title": "PRD task model — factory function with validation",
        "status": "COMPLETED",
        "risk_level": "LOW",
        "dependencies": ["T858", "T859"],
    },
    {
        "task_id": "T862",
        "title": "PRD backlog schema — PrdBacklogItem frozen dataclass",
        "status": "COMPLETED",
        "risk_level": "LOW",
        "dependencies": ["T858"],
    },
    {
        "task_id": "T863",
        "title": "PRD backlog schema — PrdBacklog container dataclass",
        "status": "COMPLETED",
        "risk_level": "LOW",
        "dependencies": ["T862"],
    },
    {
        "task_id": "T864",
        "title": "PRD backlog schema — backlog serializers",
        "status": "COMPLETED",
        "risk_level": "LOW",
        "dependencies": ["T862", "T863"],
    },
    {
        "task_id": "T865",
        "title": "PRD backlog schema — summarize and validate functions",
        "status": "COMPLETED",
        "risk_level": "MEDIUM",
        "dependencies": ["T863"],
    },
    {
        "task_id": "T866",
        "title": "PRD validator — cross-field consistency checks",
        "status": "COMPLETED",
        "risk_level": "MEDIUM",
        "dependencies": ["T862", "T865"],
    },
    {
        "task_id": "T867",
        "title": "PRD validator — duplicate task_id detection",
        "status": "COMPLETED",
        "risk_level": "MEDIUM",
        "dependencies": ["T866"],
    },
    {
        "task_id": "T868",
        "title": "PRD validator — dependency cycle detection",
        "status": "COMPLETED",
        "risk_level": "MEDIUM",
        "dependencies": ["T866"],
    },
    {
        "task_id": "T869",
        "title": "PRD parser — markdown-to-backlog parser",
        "status": "COMPLETED",
        "risk_level": "MEDIUM",
        "dependencies": ["T862", "T864"],
    },
    {
        "task_id": "T870",
        "title": "PRD parser — roundtrip test (serialize then parse)",
        "status": "COMPLETED",
        "risk_level": "LOW",
        "dependencies": ["T869"],
    },
    {
        "task_id": "T871",
        "title": "PRD planning — milestone decomposition rules",
        "status": "COMPLETED",
        "risk_level": "LOW",
        "dependencies": ["T862"],
    },
    {
        "task_id": "T872",
        "title": "PRD planning — wave and batch assignment logic",
        "status": "COMPLETED",
        "risk_level": "LOW",
        "dependencies": ["T871"],
    },
    {
        "task_id": "T873",
        "title": "PRD planning — 500+ task backlog expansion schema",
        "status": "COMPLETED",
        "risk_level": "LOW",
        "dependencies": ["T871", "T872"],
    },
    {
        "task_id": "T874",
        "title": "PRD control plane — frozen range registry",
        "status": "COMPLETED",
        "risk_level": "LOW",
        "dependencies": ["T873"],
    },
    {
        "task_id": "T875",
        "title": "PRD control plane — next-safe-range gating logic",
        "status": "COMPLETED",
        "risk_level": "MEDIUM",
        "dependencies": ["T874"],
    },
    {
        "task_id": "T876",
        "title": "PRD control plane — milestone status tracker",
        "status": "COMPLETED",
        "risk_level": "LOW",
        "dependencies": ["T874"],
    },
    {
        "task_id": "T877",
        "title": "PRD automation — task lifecycle state machine",
        "status": "COMPLETED",
        "risk_level": "MEDIUM",
        "dependencies": ["T858", "T859"],
    },
    {
        "task_id": "T878",
        "title": "PRD automation — backlog diff engine",
        "status": "COMPLETED",
        "risk_level": "MEDIUM",
        "dependencies": ["T863", "T864"],
    },
    {
        "task_id": "T879",
        "title": "PRD backlog seed packet — 500-task planning artifact",
        "status": "COMPLETED",
        "risk_level": "LOW",
        "dependencies": ["T873", "T874"],
    },
    {
        "task_id": "T880",
        "title": "PRD backlog seed packet — milestone/range/freeze registry",
        "status": "COMPLETED",
        "risk_level": "LOW",
        "dependencies": ["T874", "T879"],
    },
]

DEFAULT_M1_NOTES: List[str] = [
    "M1 covers PRD automation control plane, task modeling, and backlog planning",
    "All items COMPLETED — milestone is closed",
    "Follows frozen range rule: M8 live execution remains frozen",
]


# --- Factory ---


def build_milestone1_seed(
    milestone_id: str = "M1",
    title: str = "PRD automation control plane",
    task_items: List[Dict[str, Any]] | None = None,
    notes: List[str] | None = None,
) -> PrdMilestone1Seed:
    """Build PrdMilestone1Seed with defaults for M1 (T858-T880)."""
    if task_items is None:
        task_items = [dict(t) for t in DEFAULT_M1_TASKS]
    if notes is None:
        notes = list(DEFAULT_M1_NOTES)
    return PrdMilestone1Seed(
        milestone_id=milestone_id,
        title=title,
        task_items=list(task_items),
        notes=list(notes),
    )


# --- Serializers ---


def milestone1_seed_to_dict(seed: PrdMilestone1Seed) -> Dict[str, Any]:
    return {
        "milestone_id": seed.milestone_id,
        "title": seed.title,
        "task_items": [dict(t) for t in seed.task_items],
        "notes": list(seed.notes),
    }


def milestone1_seed_to_markdown(seed: PrdMilestone1Seed) -> str:
    lines: List[str] = []
    lines.append(f"# Milestone {seed.milestone_id}: {seed.title}")
    lines.append("")
    lines.append(f"**Tasks:** {len(seed.task_items)}")
    completed = sum(1 for t in seed.task_items if t.get("status") == "COMPLETED")
    lines.append(f"**Completed:** {completed}/{len(seed.task_items)}")
    lines.append("")
    lines.append("## Task Items")
    lines.append("")
    for t in seed.task_items:
        deps = ", ".join(t.get("dependencies", [])) or "none"
        lines.append(
            f"- **{t['task_id']}** [{t['status']}] ({t['risk_level']}) "
            f"{t['title']} — deps: {deps}"
        )
    lines.append("")
    if seed.notes:
        lines.append("## Notes")
        lines.append("")
        for note in seed.notes:
            lines.append(f"- {note}")
        lines.append("")
    return "\n".join(lines)
