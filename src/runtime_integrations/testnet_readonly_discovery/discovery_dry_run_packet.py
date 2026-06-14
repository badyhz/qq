"""Read-only discovery dry-run packet."""
from __future__ import annotations
import json, pathlib, uuid
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class DryRunPacket:
    packet_id: str
    created_at: str
    discovery_design_ref: str
    credential_policy_ref: str
    capability_inventory_ref: str
    adapter_contract_ref: str
    governance_checklist_ref: str
    blocker_summary: tuple[str, ...]
    final_recommendation: str
    def to_dict(self) -> dict:
        return {
            "packet_id": self.packet_id, "created_at": self.created_at,
            "discovery_design_ref": self.discovery_design_ref,
            "credential_policy_ref": self.credential_policy_ref,
            "capability_inventory_ref": self.capability_inventory_ref,
            "adapter_contract_ref": self.adapter_contract_ref,
            "governance_checklist_ref": self.governance_checklist_ref,
            "blocker_summary": list(self.blocker_summary),
            "final_recommendation": self.final_recommendation,
        }


BLOCKERS = (
    "No real credential review completed",
    "No exchange permission review completed",
    "No human approval for read-only discovery",
    "No IP allowlist review completed",
    "No testnet-only endpoint validation completed",
    "No kill switch field validation",
    "No rollback plan tested",
)


def create_packet() -> DryRunPacket:
    return DryRunPacket(
        packet_id=f"DRP_{uuid.uuid4().hex[:12]}",
        created_at=datetime.now(timezone.utc).isoformat(),
        discovery_design_ref="discovery_design.json",
        credential_policy_ref="credential_policy_stub.json",
        capability_inventory_ref="exchange_capability_inventory.json",
        adapter_contract_ref="readonly_adapter_contract.json",
        governance_checklist_ref="discovery_governance_checklist.json",
        blocker_summary=BLOCKERS,
        final_recommendation="DESIGN_READY|REAL_NETWORK_STILL_BLOCKED|READ_ONLY_DISCOVERY_REQUIRES_HUMAN_APPROVAL|TESTNET_SUBMIT_NOT_ALLOWED",
    )


def write_packet(packet: DryRunPacket, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(packet.to_dict(), indent=2), encoding="utf-8")


def render_report(packet: DryRunPacket) -> str:
    lines = ["# Read-Only Discovery Dry-Run Packet", "",
        f"**packet_id={packet.packet_id}**",
        f"**final_recommendation={packet.final_recommendation}**",
        "**REAL_NETWORK_STILL_BLOCKED**",
        "**TESTNET_SUBMIT_NOT_ALLOWED**", "",
        "## References", "",
        f"- Discovery Design: {packet.discovery_design_ref}",
        f"- Credential Policy: {packet.credential_policy_ref}",
        f"- Capability Inventory: {packet.capability_inventory_ref}",
        f"- Adapter Contract: {packet.adapter_contract_ref}",
        f"- Governance Checklist: {packet.governance_checklist_ref}", "",
        "## Blockers", ""]
    for b in packet.blocker_summary:
        lines.append(f"- {b}")
    lines.extend(["", "## Conclusion", "",
        "READ_ONLY_DISCOVERY_DRY_RUN_PACKET_READY",
        "DESIGN_READY",
        "REAL_NETWORK_STILL_BLOCKED",
        "READ_ONLY_DISCOVERY_REQUIRES_HUMAN_APPROVAL",
        "TESTNET_SUBMIT_NOT_ALLOWED",
        ""])
    return "\n".join(lines)
