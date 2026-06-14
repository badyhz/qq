"""Discovery governance checklist."""
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
    status: str  # NOT_STARTED, BLOCKED, DOCUMENTED
    def to_dict(self) -> dict:
        return {"item_id": self.item_id, "category": self.category, "title": self.title,
                "description": self.description, "required": self.required, "status": self.status}


@dataclass(frozen=True)
class GovernanceChecklist:
    checklist_id: str
    created_at: str
    items: tuple[ChecklistItem, ...]
    final_decision: str
    def to_dict(self) -> dict:
        return {"checklist_id": self.checklist_id, "created_at": self.created_at,
                "items": [i.to_dict() for i in self.items], "final_decision": self.final_decision}


ITEMS = (
    ChecklistItem("GOV_001", "approval", "Manual Approval Required", "Human operator must approve read-only discovery scope", True, "NOT_STARTED"),
    ChecklistItem("GOV_002", "credential", "Credential Policy Review Required", "Credential policy stub must be reviewed and approved", True, "NOT_STARTED"),
    ChecklistItem("GOV_003", "permission", "Read-Only Permission Review Required", "Exchange read-only permissions must be validated", True, "NOT_STARTED"),
    ChecklistItem("GOV_004", "network", "IP Allowlist Review Required", "IP allowlist for testnet endpoints must be reviewed", True, "NOT_STARTED"),
    ChecklistItem("GOV_005", "endpoint", "Testnet-Only Endpoint Review Required", "All endpoints must be verified as testnet-only", True, "NOT_STARTED"),
    ChecklistItem("GOV_006", "audit", "No-Submit Audit Review Required", "Audit log must confirm no submit attempts", True, "NOT_STARTED"),
    ChecklistItem("GOV_007", "safety", "Rollback Plan Required", "Rollback procedure must be documented", True, "NOT_STARTED"),
    ChecklistItem("GOV_008", "safety", "Kill Switch Required", "Kill switch must be validated for read-only context", True, "NOT_STARTED"),
    ChecklistItem("GOV_009", "fallback", "Dry-Run Fallback Required", "Dry-run fallback must work if discovery fails", True, "NOT_STARTED"),
    ChecklistItem("GOV_010", "logging", "Logging Redaction Required", "All sensitive data must be redacted in logs", True, "NOT_STARTED"),
)


def create_checklist() -> GovernanceChecklist:
    return GovernanceChecklist(
        checklist_id=f"DGC_{uuid.uuid4().hex[:12]}",
        created_at=datetime.now(timezone.utc).isoformat(),
        items=ITEMS,
        final_decision="DISCOVERY_GOVERNANCE_CHECKLIST_READY",
    )


def count_by_status(checklist: GovernanceChecklist) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in checklist.items:
        counts[item.status] = counts.get(item.status, 0) + 1
    return counts


def write_checklist(checklist: GovernanceChecklist, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(checklist.to_dict(), indent=2), encoding="utf-8")


def render_report(checklist: GovernanceChecklist) -> str:
    lines = ["# Discovery Governance Checklist", "",
        f"**checklist_id={checklist.checklist_id}**",
        f"**final_decision={checklist.final_decision}**",
        "**HUMAN_APPROVAL_REQUIRED**",
        "**SUBMIT_UNLOCK_BLOCKED**", "",
        "## Items", "",
        "| ID | Category | Title | Status | Required |",
        "|----|----------|-------|--------|----------|"]
    for item in checklist.items:
        lines.append(f"| {item.item_id} | {item.category} | {item.title} | {item.status} | {item.required} |")
    lines.extend(["", "## Conclusion", "",
        "DISCOVERY_GOVERNANCE_CHECKLIST_READY",
        "HUMAN_APPROVAL_REQUIRED",
        "SUBMIT_UNLOCK_BLOCKED",
        "TESTNET_SUBMIT_NOT_ALLOWED",
        ""])
    return "\n".join(lines)
