"""T17501 — Promotion Approval Packet Generator.

Pure deterministic. No I/O. No network.
Generates approval packet for shadow-to-testnet promotion.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

RELEASE_HOLD_REQUIRED = "HOLD"


@dataclass(frozen=True)
class ApprovalPacketItem:
    """Single approval packet item."""
    item_id: str
    section: str
    content: str
    status: str
    simulation_only: bool

    def to_dict(self) -> dict:
        return {
            "item_id": self.item_id,
            "section": self.section,
            "content": self.content,
            "status": self.status,
            "simulation_only": self.simulation_only,
        }


@dataclass(frozen=True)
class ApprovalPacket:
    """Complete approval packet for promotion."""
    packet_id: str
    decision: str
    items: list[ApprovalPacketItem]
    total_items: int
    simulation_only: bool
    release_hold: str

    def to_dict(self) -> dict:
        return {
            "packet_id": self.packet_id,
            "decision": self.decision,
            "items": [i.to_dict() for i in self.items],
            "total_items": self.total_items,
            "simulation_only": self.simulation_only,
            "release_hold": self.release_hold,
        }


def build_approval_packet(
    decision_data: dict,
    release_hold: str = RELEASE_HOLD_REQUIRED,
) -> ApprovalPacket:
    """Build approval packet from promotion decision."""
    if release_hold != RELEASE_HOLD_REQUIRED:
        raise ValueError(f"release_hold={release_hold!r} != HOLD")

    decision = decision_data.get("decision", "BLOCKED")
    items: list[ApprovalPacketItem] = []

    items.append(ApprovalPacketItem(
        item_id="packet_decision",
        section="decision",
        content=f"promotion_decision={decision}",
        status="GENERATED",
        simulation_only=True,
    ))

    items.append(ApprovalPacketItem(
        item_id="packet_evidence_summary",
        section="evidence",
        content=f"passed={len(decision_data.get('evidence_passed', []))}_failed={len(decision_data.get('evidence_failed', []))}",
        status="GENERATED",
        simulation_only=True,
    ))

    items.append(ApprovalPacketItem(
        item_id="packet_denial_reasons",
        section="denials",
        content=f"denial_count={len(decision_data.get('denial_reasons', []))}",
        status="GENERATED",
        simulation_only=True,
    ))

    items.append(ApprovalPacketItem(
        item_id="packet_safety_boundary",
        section="safety",
        content="no_real_submit_authorized_simulation_only",
        status="GENERATED",
        simulation_only=True,
    ))

    items.append(ApprovalPacketItem(
        item_id="packet_rollback_reference",
        section="rollback",
        content="rollback_plan_available",
        status="GENERATED",
        simulation_only=True,
    ))

    return ApprovalPacket(
        packet_id="shadow_to_testnet_approval_packet",
        decision=decision,
        items=items,
        total_items=len(items),
        simulation_only=True,
        release_hold=release_hold,
    )


def compute_packet_hash(packet: ApprovalPacket) -> str:
    raw = json.dumps(packet.to_dict(), sort_keys=True, indent=2)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def render_packet_markdown(packet: ApprovalPacket) -> str:
    lines = [
        "# Shadow-to-Testnet Approval Packet",
        "",
        f"**Packet ID:** {packet.packet_id}",
        f"**Decision:** {packet.decision}",
        f"**Total items:** {packet.total_items}",
        f"**simulation_only:** {packet.simulation_only}",
        f"**release_hold:** {packet.release_hold}",
        "",
        "## Safety Boundary",
        "",
        "- This packet is simulation-only.",
        "- No real submit authorized.",
        "- No real trading authorized.",
        "",
        "## Packet Items",
        "",
    ]

    for item in packet.items:
        lines.append(f"- **{item.section}:** {item.content} [{item.status}]")

    lines.append("")
    lines.append("---")
    lines.append("SIMULATION ONLY. NO SUBMIT AUTHORIZED.")
    lines.append("")

    return "\n".join(lines)


def write_json(packet: ApprovalPacket, out_path) -> None:
    import pathlib
    p = pathlib.Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(packet.to_dict(), indent=2), encoding="utf-8")


def write_manifest(packet: ApprovalPacket, out_path, release_hold: str) -> None:
    import pathlib
    p = pathlib.Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "packet_id": packet.packet_id,
        "decision": packet.decision,
        "total_items": packet.total_items,
        "release_hold": release_hold,
        "simulation_only": True,
        "packet_hash": compute_packet_hash(packet),
    }
    p.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def write_markdown(packet: ApprovalPacket, out_path) -> None:
    import pathlib
    p = pathlib.Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(render_packet_markdown(packet), encoding="utf-8")
