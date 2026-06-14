"""Read-only discovery operator checklist."""
from __future__ import annotations
import json, pathlib, uuid
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class ChecklistItem:
    item_id: str
    category: str
    title: str
    description: str
    required: bool
    status: str  # NOT_STARTED, VERIFIED, PENDING
    def to_dict(self) -> dict:
        return {"item_id": self.item_id, "category": self.category, "title": self.title,
                "description": self.description, "required": self.required, "status": self.status}


@dataclass(frozen=True)
class OperatorChecklist:
    checklist_id: str
    created_at: str
    items: tuple[ChecklistItem, ...]
    final_decision: str
    def to_dict(self) -> dict:
        return {"checklist_id": self.checklist_id, "created_at": self.created_at,
                "items": [i.to_dict() for i in self.items], "final_decision": self.final_decision}


ITEMS = (
    ChecklistItem("OPR_001", "git", "Confirm Current Git Tag", "Verify testnet-readonly-discovery-design-complete tag exists", True, "NOT_STARTED"),
    ChecklistItem("OPR_002", "git", "Confirm Tracked Diff Clean", "Verify no uncommitted tracked changes", True, "NOT_STARTED"),
    ChecklistItem("OPR_003", "git", "Confirm Old High-Risk Untracked Preserved", "Verify core/live_runner.py etc. remain untracked", True, "NOT_STARTED"),
    ChecklistItem("OPR_004", "suite", "Confirm No-Network Suite Pass", "Verify readonly discovery suite passed", True, "NOT_STARTED"),
    ChecklistItem("OPR_005", "credential", "Confirm Credential Policy Stub Pass", "Verify credential policy is PLACEHOLDER_ONLY", True, "NOT_STARTED"),
    ChecklistItem("OPR_006", "capability", "Confirm Capability Inventory Pass", "Verify submit capabilities are PROHIBITED", True, "NOT_STARTED"),
    ChecklistItem("OPR_007", "governance", "Confirm Governance Checklist Pass", "Verify all governance items documented", True, "NOT_STARTED"),
    ChecklistItem("OPR_008", "approval", "Confirm Human Approval Required", "Verify human_review_required=True", True, "NOT_STARTED"),
    ChecklistItem("OPR_009", "safety", "Confirm No Submit Unlock", "Verify no submit gate unlock marker present", True, "NOT_STARTED"),
    ChecklistItem("OPR_010", "safety", "Confirm Rollback Plan Reviewed", "Verify rollback procedure documented", True, "NOT_STARTED"),
    ChecklistItem("OPR_011", "safety", "Confirm Kill Switch Policy Reviewed", "Verify kill switch policy documented", True, "NOT_STARTED"),
)


def create_checklist() -> OperatorChecklist:
    return OperatorChecklist(
        checklist_id=f"OPC_{uuid.uuid4().hex[:12]}",
        created_at=datetime.now(timezone.utc).isoformat(),
        items=ITEMS,
        final_decision="READONLY_DISCOVERY_OPERATOR_CHECKLIST_READY|HUMAN_APPROVAL_REQUIRED|REAL_NETWORK_NOT_ALLOWED|TESTNET_SUBMIT_NOT_ALLOWED",
    )


def write_checklist(checklist: OperatorChecklist, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(checklist.to_dict(), indent=2), encoding="utf-8")


def render_report(checklist: OperatorChecklist) -> str:
    lines = ["# Read-Only Discovery Operator Checklist", "",
        f"**checklist_id={checklist.checklist_id}**",
        f"**final_decision={checklist.final_decision}**",
        "**HUMAN_APPROVAL_REQUIRED**",
        "**REAL_NETWORK_NOT_ALLOWED**",
        "**TESTNET_SUBMIT_NOT_ALLOWED**", "",
        "## Items", "",
        "| ID | Category | Title | Status | Required |",
        "|----|----------|-------|--------|----------|"]
    for item in checklist.items:
        lines.append(f"| {item.item_id} | {item.category} | {item.title} | {item.status} | {item.required} |")
    lines.extend(["", "## Conclusion", "",
        "READONLY_DISCOVERY_OPERATOR_CHECKLIST_READY",
        "HUMAN_APPROVAL_REQUIRED",
        "REAL_NETWORK_NOT_ALLOWED",
        "TESTNET_SUBMIT_NOT_ALLOWED",
        ""])
    return "\n".join(lines)
