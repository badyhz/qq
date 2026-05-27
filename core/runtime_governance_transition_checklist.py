"""Runtime governance transition checklist — pure data, no I/O."""

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass(frozen=True)
class RuntimeGovernanceChecklistItem:
    item_id: str
    title: str
    required: bool
    status: str  # "complete" / "incomplete"
    notes: str


_ITEMS = [
    ("contract_stable", "Runtime governance contract stable"),
    ("dry_run_adapter_stable", "Dry-run adapter stable"),
    ("audit_event_stable", "Audit event model stable"),
    ("preflight_packet_stable", "Preflight packet stable"),
    ("no_submit_guard", "No-submit guard confirmed"),
    ("manual_approval", "Manual approval required for next phase"),
    ("runtime_integration_frozen", "Runtime integration frozen"),
    ("live_submit_frozen", "Live submit frozen"),
]


def build_runtime_governance_transition_checklist() -> List[RuntimeGovernanceChecklistItem]:
    """Return 8-item checklist, all required, default complete."""
    return [
        RuntimeGovernanceChecklistItem(
            item_id=iid,
            title=title,
            required=True,
            status="complete",
            notes="",
        )
        for iid, title in _ITEMS
    ]


def transition_checklist_to_dict(
    checklist: List[RuntimeGovernanceChecklistItem],
) -> List[Dict[str, Any]]:
    """Serialize checklist to list of dicts."""
    return [
        {
            "item_id": c.item_id,
            "title": c.title,
            "required": c.required,
            "status": c.status,
            "notes": c.notes,
        }
        for c in checklist
    ]


def transition_checklist_to_markdown(
    checklist: List[RuntimeGovernanceChecklistItem],
) -> str:
    """Deterministic markdown table of checklist items."""
    lines = [
        "# Runtime Governance Transition Checklist",
        "",
        "| # | ID | Title | Required | Status | Notes |",
        "|---|-----|-------|----------|--------|-------|",
    ]
    for idx, c in enumerate(checklist, 1):
        req = "yes" if c.required else "no"
        mark = "[x]" if c.status == "complete" else "[ ]"
        lines.append(f"| {idx} | {c.item_id} | {c.title} | {req} | {mark} | {c.notes} |")
    lines.append("")
    return "\n".join(lines)


def summarize_transition_checklist(
    checklist: List[RuntimeGovernanceChecklistItem],
) -> Dict[str, Any]:
    """Return summary with verdict: PASS if all required complete, else FAIL."""
    required = [c for c in checklist if c.required]
    complete = [c for c in required if c.status == "complete"]
    incomplete = [c for c in required if c.status != "complete"]
    verdict = "PASS" if not incomplete else "FAIL"
    return {
        "total": len(checklist),
        "required_count": len(required),
        "complete_count": len(complete),
        "incomplete_count": len(incomplete),
        "incomplete_ids": [c.item_id for c in incomplete],
        "verdict": verdict,
    }
