"""Next-stage prerequisite checklist."""
from __future__ import annotations
import json, pathlib, uuid
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class PrerequisiteItem:
    item_id: str
    category: str
    title: str
    description: str
    required: bool
    status: str  # NOT_STARTED, BLOCKED, DOCUMENTED
    unlock_dependency: str
    def to_dict(self) -> dict:
        return {"item_id": self.item_id, "category": self.category, "title": self.title, "description": self.description, "required": self.required, "status": self.status, "unlock_dependency": self.unlock_dependency}


@dataclass(frozen=True)
class NextStageChecklist:
    checklist_id: str
    created_at: str
    next_stage: str
    items: tuple[PrerequisiteItem, ...]
    def to_dict(self) -> dict:
        return {"checklist_id": self.checklist_id, "created_at": self.created_at, "next_stage": self.next_stage, "items": [i.to_dict() for i in self.items]}


ITEMS = (
    PrerequisiteItem("PRE_001", "approval", "Required Manual Approval", "Human operator must sign off on read-only testnet discovery scope", True, "NOT_STARTED", "read_only_discovery"),
    PrerequisiteItem("PRE_002", "credential", "Required Credential Handling Policy", "Define how testnet credentials are stored, rotated, and audited", True, "NOT_STARTED", "read_only_discovery"),
    PrerequisiteItem("PRE_003", "permission", "Required Exchange Account Permission Review", "Audit exchange account permissions for read-only access", True, "NOT_STARTED", "read_only_discovery"),
    PrerequisiteItem("PRE_004", "network", "Required IP Allowlist Review", "Review and document IP allowlist for testnet endpoints", True, "NOT_STARTED", "read_only_discovery"),
    PrerequisiteItem("PRE_005", "endpoint", "Required Testnet-Only Endpoint Review", "Validate all endpoints point to testnet, not production", True, "NOT_STARTED", "read_only_discovery"),
    PrerequisiteItem("PRE_006", "capability", "Required Read-Only Capability Validation", "Validate adapter can only perform read operations (GET, no POST/DELETE)", True, "NOT_STARTED", "read_only_discovery"),
    PrerequisiteItem("PRE_007", "safety", "Required Rollback Plan", "Document rollback procedure if read-only discovery reveals issues", True, "NOT_STARTED", "read_only_discovery"),
    PrerequisiteItem("PRE_008", "safety", "Required Kill Switch Validation", "Validate kill switch works in read-only testnet context", True, "NOT_STARTED", "read_only_discovery"),
    PrerequisiteItem("PRE_009", "audit", "Required Audit Log Validation", "Validate all read operations are logged for audit", True, "NOT_STARTED", "read_only_discovery"),
    PrerequisiteItem("PRE_010", "fallback", "Required Dry-Run Fallback", "Ensure dry-run fallback works if read-only discovery fails", True, "NOT_STARTED", "read_only_discovery"),
)


def create_checklist() -> NextStageChecklist:
    return NextStageChecklist(
        checklist_id=f"NXT_{uuid.uuid4().hex[:12]}",
        created_at=datetime.now(timezone.utc).isoformat(),
        next_stage="READ_ONLY_TESTNET_DISCOVERY",
        items=ITEMS,
    )


def count_by_status(checklist: NextStageChecklist) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in checklist.items:
        counts[item.status] = counts.get(item.status, 0) + 1
    return counts


def write_checklist(checklist: NextStageChecklist, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(checklist.to_dict(), indent=2), encoding="utf-8")


def render_report(checklist: NextStageChecklist) -> str:
    lines = ["# Next-Stage Prerequisite Checklist", "",
        f"**checklist_id={checklist.checklist_id}**",
        f"**next_stage={checklist.next_stage}**",
        "**TESTNET_SUBMIT_NOT_ALLOWED**", "",
        "## Prerequisites", "",
        "| ID | Category | Title | Status | Required |",
        "|----|----------|-------|--------|----------|"]
    for item in checklist.items:
        lines.append(f"| {item.item_id} | {item.category} | {item.title} | {item.status} | {item.required} |")
    by_status = count_by_status(checklist)
    lines.extend(["", "## Status Summary", ""])
    for status, count in sorted(by_status.items()):
        lines.append(f"- {status}: {count}")
    lines.extend(["", "## Allowed Next Stages", "",
        "- READ_ONLY_TESTNET_DISCOVERY",
        "- EXCHANGE_CAPABILITY_DISCOVERY",
        "- CREDENTIAL_PLACEHOLDER_REVIEW",
        "- NO_SUBMIT_ADAPTER_DESIGN", "",
        "## Still Prohibited", "",
        "- TESTNET_SUBMIT",
        "- REAL_SUBMIT",
        "- CANCEL_SUBMIT",
        "- LIVE_RECONCILIATION_UNLOCK", "",
        "## Conclusion", "",
        "NEXT_STAGE_PREREQUISITE_CHECKLIST_READY",
        "TESTNET_SUBMIT_NOT_ALLOWED",
        "REAL_TRADING_NOT_ALLOWED",
        ""])
    return "\n".join(lines)
