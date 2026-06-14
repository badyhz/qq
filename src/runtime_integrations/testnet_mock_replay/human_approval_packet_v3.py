"""Human approval packet v3."""
from __future__ import annotations
import json, pathlib, uuid
from dataclasses import dataclass
from datetime import datetime, timezone

@dataclass(frozen=True)
class ChecklistItem:
    item_id: str
    category: str
    title: str
    status: str  # DOCUMENTED, STUB_ONLY, BLOCKED, NOT_IMPLEMENTED
    required: bool
    def to_dict(self) -> dict:
        return {"item_id": self.item_id, "category": self.category, "title": self.title, "status": self.status, "required": self.required}

@dataclass(frozen=True)
class ApprovalPacketV3:
    packet_id: str
    created_at: str
    requested_scope: str
    allowed_scope: str
    prohibited_scope: str
    checklists: tuple[ChecklistItem, ...]
    evidence_bundle_id: str
    operator_ack: bool
    human_approval_required: bool
    submit_unlock_blocked: bool
    decision: str
    def to_dict(self) -> dict:
        d = {k: getattr(self, k) for k in self.__dataclass_fields__}
        d["checklists"] = [c.to_dict() for c in self.checklists]
        return d

CHECKLISTS = (
    ChecklistItem("cred_vault", "credential", "Credential Vault Ready", "STUB_ONLY", True),
    ChecklistItem("exchange_perm", "permission", "Exchange Permission Reviewed", "DOCUMENTED", True),
    ChecklistItem("risk_limit", "risk", "Risk Limit Placeholder", "DOCUMENTED", True),
    ChecklistItem("kill_switch", "safety", "Kill Switch Armed", "DOCUMENTED", True),
    ChecklistItem("rollback", "safety", "Rollback Procedure Tested", "DOCUMENTED", True),
    ChecklistItem("evidence", "evidence", "Evidence Bundle Complete", "DOCUMENTED", True),
    ChecklistItem("signing", "signing", "Request Signing Reviewed", "STUB_ONLY", True),
    ChecklistItem("transport", "transport", "Network Transport Reviewed", "STUB_ONLY", True),
    ChecklistItem("audit", "audit", "Audit Log Verified", "DOCUMENTED", True),
    ChecklistItem("operator", "approval", "Operator Acknowledgement", "NOT_IMPLEMENTED", True),
)

def create_packet(evidence_bundle_id: str) -> ApprovalPacketV3:
    return ApprovalPacketV3(
        packet_id=f"APPROVAL_V3_{uuid.uuid4().hex[:12]}",
        created_at=datetime.now(timezone.utc).isoformat(),
        requested_scope="External testnet adapter field-test with mock transport",
        allowed_scope="Mock-only replay, no real network, no real submit",
        prohibited_scope="Real submit, real credentials, real network, gate unlock",
        checklists=CHECKLISTS,
        evidence_bundle_id=evidence_bundle_id,
        operator_ack=False,
        human_approval_required=True,
        submit_unlock_blocked=True,
        decision="APPROVAL_PACKET_GENERATED",
    )

def write_packet(packet: ApprovalPacketV3, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(packet.to_dict(), indent=2), encoding="utf-8")

def render_report(packet: ApprovalPacketV3) -> str:
    lines = ["# Human Approval Packet v3", "",
        f"**packet_id={packet.packet_id}**",
        f"**decision={packet.decision}**",
        "**SUBMIT_UNLOCK_BLOCKED**",
        "**HUMAN_APPROVAL_REQUIRED**",
        "**TESTNET_SUBMIT_NOT_ALLOWED**", "",
        "## Scope", "",
        f"- Requested: {packet.requested_scope}",
        f"- Allowed: {packet.allowed_scope}",
        f"- Prohibited: {packet.prohibited_scope}", "",
        "## Checklists", "",
        "| Item | Category | Status | Required |",
        "|------|----------|--------|----------|"]
    for c in packet.checklists:
        lines.append(f"| {c.title} | {c.category} | {c.status} | {c.required} |")
    lines.extend(["", "## Conclusion", "",
        "HUMAN_APPROVAL_PACKET_V3_READY",
        "SUBMIT_UNLOCK_BLOCKED",
        "TESTNET_SUBMIT_NOT_ALLOWED",
        ""])
    return "\n".join(lines)
