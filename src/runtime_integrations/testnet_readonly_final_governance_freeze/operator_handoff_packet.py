"""Operator handoff packet: comprehensive handoff document for operator review."""
from __future__ import annotations
import json, pathlib, uuid
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class HandoffItem:
    item_id: str
    category: str
    description: str
    status: str
    def to_dict(self) -> dict:
        return {"item_id": self.item_id, "category": self.category,
                "description": self.description, "status": self.status}


@dataclass(frozen=True)
class OperatorHandoffPacket:
    packet_id: str
    created_at: str
    stage: str
    items: tuple[HandoffItem, ...]
    final_verdict: str
    def to_dict(self) -> dict:
        return {"packet_id": self.packet_id, "created_at": self.created_at,
                "stage": self.stage, "items": [i.to_dict() for i in self.items],
                "final_verdict": self.final_verdict}


ITEMS = (
    HandoffItem("HAND_001", "MILESTONE", "External testnet adapter spec complete (T155001-T170000)", "DONE"),
    HandoffItem("HAND_002", "MILESTONE", "External testnet mock transport complete (T170001-T185000)", "DONE"),
    HandoffItem("HAND_003", "MILESTONE", "External testnet mock replay complete (T185001-T200000)", "DONE"),
    HandoffItem("HAND_004", "MILESTONE", "External testnet mock review complete (T200001-T215000)", "DONE"),
    HandoffItem("HAND_005", "MILESTONE", "External testnet mock closeout complete (T215001-T230000)", "DONE"),
    HandoffItem("HAND_006", "MILESTONE", "Read-only discovery design complete (T230001-T245000)", "DONE"),
    HandoffItem("HAND_007", "MILESTONE", "Read-only preapproval evidence complete (T245001-T260000)", "DONE"),
    HandoffItem("HAND_008", "MILESTONE", "Read-only release gate complete (T260001-T275000)", "DONE"),
    HandoffItem("HAND_009", "MILESTONE", "Final approval simulator complete (T275001-T290000)", "DONE"),
    HandoffItem("HAND_010", "MILESTONE", "Dry execution rehearsal complete (T290001-T305000)", "DONE"),
    HandoffItem("HAND_011", "MILESTONE", "Final governance freeze complete (T305001-T320000)", "DONE"),
    HandoffItem("HAND_012", "CONSTRAINT", "Real network permanently blocked", "ACTIVE"),
    HandoffItem("HAND_013", "CONSTRAINT", "Testnet submit permanently blocked", "ACTIVE"),
    HandoffItem("HAND_014", "CONSTRAINT", "Real credentials permanently blocked", "ACTIVE"),
    HandoffItem("HAND_015", "NEXT_STEP", "Requires human review to advance to network-on phase", "PENDING"),
)


def create_packet() -> OperatorHandoffPacket:
    return OperatorHandoffPacket(
        packet_id=f"OHP_{uuid.uuid4().hex[:12]}",
        created_at=datetime.now(timezone.utc).isoformat(),
        stage="T305001-T320000",
        items=ITEMS,
        final_verdict="READONLY_OPERATOR_HANDOFF_PACKET_READY|ALL_MILESTONES_DOCUMENTED|REAL_NETWORK_NOT_ALLOWED|TESTNET_SUBMIT_NOT_ALLOWED",
    )


def write_packet(packet: OperatorHandoffPacket, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(packet.to_dict(), indent=2), encoding="utf-8")


def render_report(packet: OperatorHandoffPacket) -> str:
    lines = ["# Operator Handoff Packet", "",
        f"**packet_id={packet.packet_id}**",
        f"**stage={packet.stage}**",
        f"**verdict={packet.final_verdict}**", "",
        "## Items", "",
        "| Item | Category | Description | Status |",
        "|------|----------|-------------|--------|"]
    for i in packet.items:
        lines.append(f"| {i.item_id} | {i.category} | {i.description} | {i.status} |")
    lines.extend(["", "## Conclusion", "",
        "READONLY_OPERATOR_HANDOFF_PACKET_READY",
        "ALL_MILESTONES_DOCUMENTED",
        "REAL_NETWORK_NOT_ALLOWED",
        "TESTNET_SUBMIT_NOT_ALLOWED", ""])
    return "\n".join(lines)
