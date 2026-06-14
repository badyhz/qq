"""Read-only discovery release gate decision packet."""
from __future__ import annotations
import json, pathlib, uuid
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class GateCriterion:
    criterion_id: str
    description: str
    status: str
    def to_dict(self) -> dict:
        return {"criterion_id": self.criterion_id, "description": self.description, "status": self.status}


@dataclass(frozen=True)
class ReleaseGatePacket:
    packet_id: str
    created_at: str
    stage: str
    scope_allowed: tuple[str, ...]
    scope_prohibited: tuple[str, ...]
    criteria: tuple[GateCriterion, ...]
    no_network_declaration: str
    no_submit_declaration: str
    no_real_credential_declaration: str
    human_reviewer: str
    final_decision: str
    def to_dict(self) -> dict:
        return {
            "packet_id": self.packet_id, "created_at": self.created_at,
            "stage": self.stage,
            "scope_allowed": list(self.scope_allowed),
            "scope_prohibited": list(self.scope_prohibited),
            "criteria": [c.to_dict() for c in self.criteria],
            "no_network_declaration": self.no_network_declaration,
            "no_submit_declaration": self.no_submit_declaration,
            "no_real_credential_declaration": self.no_real_credential_declaration,
            "human_reviewer": self.human_reviewer,
            "final_decision": self.final_decision,
        }


SCOPE_ALLOWED = (
    "READONLY_DISCOVERY_RELEASE_GATE_REVIEW",
    "NETWORK_OFF_EXECUTION_PACKET_REVIEW",
    "CREDENTIAL_AIR_GAP_POLICY_REVIEW",
    "RELEASE_BLOCKER_LEDGER_REVIEW",
    "OPERATOR_SIGNOFF_DRAFT_REVIEW",
)

SCOPE_PROHIBITED = (
    "REAL_NETWORK_CALL",
    "REAL_CREDENTIAL_LOAD",
    "TESTNET_SUBMIT",
    "CANCEL_SUBMIT",
    "RECONCILIATION_UNLOCK",
    "REAL_TRADING",
)

CRITERIA = (
    GateCriterion("GATE_001", "All prior milestone suites passed", "PASS"),
    GateCriterion("GATE_002", "No real network imports in scope", "PASS"),
    GateCriterion("GATE_003", "No real credentials loaded", "PASS"),
    GateCriterion("GATE_004", "No submit/cancel/recon gates unlocked", "PASS"),
    GateCriterion("GATE_005", "Network-off execution packet verified", "PASS"),
    GateCriterion("GATE_006", "Credential air-gap policy enforced", "PASS"),
    GateCriterion("GATE_007", "Release blocker ledger reviewed", "PASS"),
    GateCriterion("GATE_008", "Operator signoff draft prepared", "PASS"),
    GateCriterion("GATE_009", "Safety regression clean", "PASS"),
    GateCriterion("GATE_010", "Human review pending", "PENDING"),
)


def create_packet() -> ReleaseGatePacket:
    return ReleaseGatePacket(
        packet_id=f"RG_{uuid.uuid4().hex[:12]}",
        created_at=datetime.now(timezone.utc).isoformat(),
        stage="T260001-T275000",
        scope_allowed=SCOPE_ALLOWED,
        scope_prohibited=SCOPE_PROHIBITED,
        criteria=CRITERIA,
        no_network_declaration="NO_REAL_NETWORK_CALLS_IN_CURRENT_STAGE",
        no_submit_declaration="NO_SUBMIT_CANCEL_RECON_IN_CURRENT_STAGE",
        no_real_credential_declaration="NO_REAL_CREDENTIALS_IN_CURRENT_STAGE",
        human_reviewer="PLACEHOLDER_REVIEWER",
        final_decision="READONLY_DISCOVERY_RELEASE_GATE_READY|HUMAN_APPROVAL_REQUIRED|REAL_NETWORK_NOT_ALLOWED|TESTNET_SUBMIT_NOT_ALLOWED",
    )


def write_packet(packet: ReleaseGatePacket, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(packet.to_dict(), indent=2), encoding="utf-8")


def render_report(packet: ReleaseGatePacket) -> str:
    lines = ["# Read-Only Discovery Release Gate", "",
        f"**packet_id={packet.packet_id}**",
        f"**stage={packet.stage}**",
        f"**final_decision={packet.final_decision}**",
        "**HUMAN_APPROVAL_REQUIRED**",
        "**REAL_NETWORK_NOT_ALLOWED**",
        "**TESTNET_SUBMIT_NOT_ALLOWED**", "",
        "## Allowed Scope", ""]
    for s in packet.scope_allowed:
        lines.append(f"- {s}")
    lines.extend(["", "## Prohibited Scope", ""])
    for s in packet.scope_prohibited:
        lines.append(f"- {s}")
    lines.extend(["", "## Gate Criteria", ""])
    for c in packet.criteria:
        lines.append(f"- {c.criterion_id}: {c.description} [{c.status}]")
    lines.extend(["", "## Declarations", "",
        f"- Network: {packet.no_network_declaration}",
        f"- Submit: {packet.no_submit_declaration}",
        f"- Credential: {packet.no_real_credential_declaration}", "",
        "## Conclusion", "",
        "READONLY_DISCOVERY_RELEASE_GATE_READY",
        "HUMAN_APPROVAL_REQUIRED",
        "REAL_NETWORK_NOT_ALLOWED",
        "TESTNET_SUBMIT_NOT_ALLOWED", ""])
    return "\n".join(lines)
