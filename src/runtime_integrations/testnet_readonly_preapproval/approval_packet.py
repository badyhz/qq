"""Read-only discovery approval packet."""
from __future__ import annotations
import json, pathlib, uuid
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class ApprovalBlocker:
    blocker_id: str
    description: str
    status: str
    def to_dict(self) -> dict:
        return {"blocker_id": self.blocker_id, "description": self.description, "status": self.status}


@dataclass(frozen=True)
class ApprovalPacket:
    packet_id: str
    created_at: str
    requested_scope: tuple[str, ...]
    allowed_scope: tuple[str, ...]
    prohibited_scope: tuple[str, ...]
    discovery_design_ref: str
    credential_policy_ref: str
    capability_inventory_ref: str
    governance_checklist_ref: str
    no_network_declaration: str
    no_submit_declaration: str
    human_reviewer: str
    blockers: tuple[ApprovalBlocker, ...]
    final_decision: str
    def to_dict(self) -> dict:
        return {
            "packet_id": self.packet_id, "created_at": self.created_at,
            "requested_scope": list(self.requested_scope),
            "allowed_scope": list(self.allowed_scope),
            "prohibited_scope": list(self.prohibited_scope),
            "discovery_design_ref": self.discovery_design_ref,
            "credential_policy_ref": self.credential_policy_ref,
            "capability_inventory_ref": self.capability_inventory_ref,
            "governance_checklist_ref": self.governance_checklist_ref,
            "no_network_declaration": self.no_network_declaration,
            "no_submit_declaration": self.no_submit_declaration,
            "human_reviewer": self.human_reviewer,
            "blockers": [b.to_dict() for b in self.blockers],
            "final_decision": self.final_decision,
        }


ALLOWED_SCOPE = (
    "READ_ONLY_DISCOVERY_REVIEW",
    "CREDENTIAL_POLICY_REVIEW",
    "EXCHANGE_CAPABILITY_REVIEW",
    "OPERATOR_PREFLIGHT_REVIEW",
    "NO_NETWORK_PREFLIGHT_REVIEW",
)

PROHIBITED_SCOPE = (
    "REAL_NETWORK_CALL",
    "REAL_CREDENTIAL_LOAD",
    "TESTNET_SUBMIT",
    "CANCEL_SUBMIT",
    "RECONCILIATION_UNLOCK",
    "REAL_TRADING",
)

BLOCKERS = (
    ApprovalBlocker("BLK_001", "No human approval signed", "PENDING"),
    ApprovalBlocker("BLK_002", "No real credential review", "PENDING"),
    ApprovalBlocker("BLK_003", "No exchange permission validation", "PENDING"),
    ApprovalBlocker("BLK_004", "No IP allowlist review", "PENDING"),
    ApprovalBlocker("BLK_005", "No kill switch field test", "PENDING"),
    ApprovalBlocker("BLK_006", "No rollback plan tested", "PENDING"),
)


def create_packet() -> ApprovalPacket:
    return ApprovalPacket(
        packet_id=f"APR_{uuid.uuid4().hex[:12]}",
        created_at=datetime.now(timezone.utc).isoformat(),
        requested_scope=ALLOWED_SCOPE,
        allowed_scope=ALLOWED_SCOPE,
        prohibited_scope=PROHIBITED_SCOPE,
        discovery_design_ref="discovery_design.json",
        credential_policy_ref="credential_policy_stub.json",
        capability_inventory_ref="exchange_capability_inventory.json",
        governance_checklist_ref="discovery_governance_checklist.json",
        no_network_declaration="NO_REAL_NETWORK_CALLS_IN_CURRENT_STAGE",
        no_submit_declaration="NO_SUBMIT_CANCEL_RECON_IN_CURRENT_STAGE",
        human_reviewer="PLACEHOLDER_REVIEWER",
        blockers=BLOCKERS,
        final_decision="APPROVAL_PACKET_READY|HUMAN_APPROVAL_REQUIRED|REAL_NETWORK_NOT_ALLOWED|TESTNET_SUBMIT_NOT_ALLOWED",
    )


def write_packet(packet: ApprovalPacket, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(packet.to_dict(), indent=2), encoding="utf-8")


def render_report(packet: ApprovalPacket) -> str:
    lines = ["# Read-Only Discovery Approval Packet", "",
        f"**packet_id={packet.packet_id}**",
        f"**final_decision={packet.final_decision}**",
        "**HUMAN_APPROVAL_REQUIRED**",
        "**REAL_NETWORK_NOT_ALLOWED**",
        "**TESTNET_SUBMIT_NOT_ALLOWED**", "",
        "## Allowed Scope", ""]
    for s in packet.allowed_scope:
        lines.append(f"- {s}")
    lines.extend(["", "## Prohibited Scope", ""])
    for s in packet.prohibited_scope:
        lines.append(f"- {s}")
    lines.extend(["", "## Declarations", "",
        f"- Network: {packet.no_network_declaration}",
        f"- Submit: {packet.no_submit_declaration}", "",
        "## Blockers", ""])
    for b in packet.blockers:
        lines.append(f"- {b.blocker_id}: {b.description} [{b.status}]")
    lines.extend(["", "## Conclusion", "",
        "READONLY_DISCOVERY_APPROVAL_PACKET_READY",
        "HUMAN_APPROVAL_REQUIRED",
        "REAL_NETWORK_NOT_ALLOWED",
        "TESTNET_SUBMIT_NOT_ALLOWED",
        ""])
    return "\n".join(lines)
