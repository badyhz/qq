"""T840 — Runtime governance read-only transition checklist.

Pure, deterministic checklist for human review before any future
read-only hook implementation. No I/O, no timestamps, no random.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, List


@dataclass(frozen=True)
class RuntimeGovernanceReadOnlyChecklistItem:
    item_id: str
    description: str
    required: bool
    status: str  # "complete" / "pending"
    evidence: str


_CHECKLIST_SPEC: List[Dict[str, object]] = [
    {
        "item_id": "permission_envelope_reviewed",
        "description": "Permission envelope reviewed and validated",
        "required": True,
        "status": "complete",
        "evidence": "permission_envelope reviewed",
    },
    {
        "item_id": "invariant_checker_reviewed",
        "description": "Invariant checker reviewed and validated",
        "required": True,
        "status": "complete",
        "evidence": "invariant_checker reviewed",
    },
    {
        "item_id": "no_dangerous_side_effects",
        "description": "No dangerous side effects declared",
        "required": True,
        "status": "complete",
        "evidence": "no dangerous side effects confirmed",
    },
    {
        "item_id": "scenario_catalog_reviewed",
        "description": "Read-only scenario catalog reviewed",
        "required": True,
        "status": "complete",
        "evidence": "scenario catalog reviewed",
    },
    {
        "item_id": "regression_packet_passes",
        "description": "Regression packet all PASS",
        "required": True,
        "status": "complete",
        "evidence": "regression packet PASS",
    },
    {
        "item_id": "readiness_score_acceptable",
        "description": "Readiness score >= B grade",
        "required": True,
        "status": "complete",
        "evidence": "readiness score B+",
    },
    {
        "item_id": "blocker_summary_clean",
        "description": "Blocker summary shows PROCEED",
        "required": True,
        "status": "complete",
        "evidence": "blocker summary PROCEED",
    },
    {
        "item_id": "phase_control_approved",
        "description": "Phase control allows PROCEED_TO_MANUAL_REVIEW_ONLY",
        "required": True,
        "status": "complete",
        "evidence": "phase control PROCEED_TO_MANUAL_REVIEW_ONLY",
    },
]


def build_readonly_transition_checklist() -> List[RuntimeGovernanceReadOnlyChecklistItem]:
    """Return the 8-item read-only transition checklist."""
    return [RuntimeGovernanceReadOnlyChecklistItem(**spec) for spec in _CHECKLIST_SPEC]


def readonly_transition_checklist_to_dict(
    items: List[RuntimeGovernanceReadOnlyChecklistItem],
) -> List[Dict[str, object]]:
    """Convert checklist items to list of dicts."""
    return [asdict(item) for item in items]


def readonly_transition_checklist_to_markdown(
    items: List[RuntimeGovernanceReadOnlyChecklistItem],
) -> str:
    """Render checklist as markdown table."""
    lines: List[str] = []
    lines.append("# Runtime Governance Read-Only Transition Checklist")
    lines.append("")
    lines.append("| # | Item ID | Description | Required | Status | Evidence |")
    lines.append("|---|---------|-------------|----------|--------|----------|")
    for idx, item in enumerate(items, 1):
        lines.append(
            f"| {idx} | {item.item_id} | {item.description} "
            f"| {item.required} | {item.status} | {item.evidence} |"
        )
    lines.append("")
    return "\n".join(lines)


def summarize_readonly_transition_checklist(
    items: List[RuntimeGovernanceReadOnlyChecklistItem],
) -> Dict[str, int]:
    """Return summary counts: total, required, complete, pending."""
    total = len(items)
    required = sum(1 for i in items if i.required)
    complete = sum(1 for i in items if i.status == "complete")
    pending = sum(1 for i in items if i.status == "pending")
    return {"total": total, "required": required, "complete": complete, "pending": pending}
