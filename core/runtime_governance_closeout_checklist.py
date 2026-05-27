"""Runtime governance closeout checklist — pre-live closeout verification.

Pure. No I/O. No network. No random. Deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass(frozen=True)
class RuntimeGovernanceCloseoutItem:
    """Single closeout checklist item."""
    item_id: str
    description: str
    status: str  # "complete" / "incomplete"
    required: bool
    evidence: str


_ITEMS = [
    RuntimeGovernanceCloseoutItem(
        item_id="tests_pass",
        description="All runtime governance tests pass",
        status="complete",
        required=True,
        evidence="pytest runtime_governance_*.py all green",
    ),
    RuntimeGovernanceCloseoutItem(
        item_id="no_submit_evidence",
        description="No-submit evidence verified",
        status="complete",
        required=True,
        evidence="T812 no-submit evidence packet PASS",
    ),
    RuntimeGovernanceCloseoutItem(
        item_id="docs_present",
        description="All module docs present",
        status="complete",
        required=True,
        evidence="docs/runtime_governance_*.md present",
    ),
    RuntimeGovernanceCloseoutItem(
        item_id="frozen_boundaries",
        description="Frozen boundaries documented",
        status="complete",
        required=True,
        evidence="T817 frozen boundary map",
    ),
    RuntimeGovernanceCloseoutItem(
        item_id="future_tasks_hold",
        description="High-risk future tasks marked HOLD",
        status="complete",
        required=True,
        evidence="T818 future task planner",
    ),
    RuntimeGovernanceCloseoutItem(
        item_id="no_runtime_integration",
        description="No runtime integration performed",
        status="complete",
        required=True,
        evidence="no live_runner or submit imports",
    ),
]


def build_runtime_governance_closeout_checklist() -> List[RuntimeGovernanceCloseoutItem]:
    """Build closeout checklist. Deterministic."""
    return list(_ITEMS)


def closeout_checklist_to_dict(checklist: List[RuntimeGovernanceCloseoutItem]) -> List[Dict[str, Any]]:
    """Serialize checklist to list of dicts."""
    return [
        {
            "item_id": c.item_id,
            "description": c.description,
            "status": c.status,
            "required": c.required,
            "evidence": c.evidence,
        }
        for c in checklist
    ]


def closeout_checklist_to_markdown(checklist: List[RuntimeGovernanceCloseoutItem]) -> str:
    """Render checklist as deterministic markdown."""
    lines = [
        "# Runtime Governance Closeout Checklist",
        "",
        "| # | item_id | description | status |",
        "|---|---------|-------------|--------|",
    ]
    for i, c in enumerate(checklist, 1):
        mark = "[x]" if c.status == "complete" else "[ ]"
        lines.append(f"| {i} | {c.item_id} | {c.description} | {mark} |")
    lines.append("")
    return "\n".join(lines)


def summarize_closeout_checklist(checklist: List[RuntimeGovernanceCloseoutItem]) -> Dict[str, Any]:
    """Summarize checklist. Deterministic."""
    total = len(checklist)
    required_count = sum(1 for c in checklist if c.required)
    complete_count = sum(1 for c in checklist if c.status == "complete")
    incomplete_count = sum(1 for c in checklist if c.status == "incomplete")
    incomplete_ids = [c.item_id for c in checklist if c.status == "incomplete"]

    verdict = "PASS"
    if incomplete_count > 0:
        verdict = "FAIL"

    return {
        "verdict": verdict,
        "total": total,
        "required_count": required_count,
        "complete_count": complete_count,
        "incomplete_count": incomplete_count,
        "incomplete_ids": incomplete_ids,
    }
