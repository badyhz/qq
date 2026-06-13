"""Submit intent packet. Describes what would be submitted, without submitting."""
from __future__ import annotations
import json, pathlib, uuid
from dataclasses import dataclass

@dataclass(frozen=True)
class SubmitIntentPacket:
    intent_id: str
    symbol: str
    side: str
    order_type: str
    quantity: float
    price_policy: str
    risk_summary: str
    source_signal_id: str
    approval_status: str
    simulated: bool
    real_submit: bool
    testnet_submit: bool
    no_submit_enforced: bool
    def to_dict(self) -> dict:
        return {"intent_id": self.intent_id, "symbol": self.symbol, "side": self.side, "order_type": self.order_type, "quantity": self.quantity, "price_policy": self.price_policy, "risk_summary": self.risk_summary, "source_signal_id": self.source_signal_id, "approval_status": self.approval_status, "simulated": self.simulated, "real_submit": self.real_submit, "testnet_submit": self.testnet_submit, "no_submit_enforced": self.no_submit_enforced}

def build_intent_packet(symbol: str, side: str, order_type: str, quantity: float, price_policy: str, risk_summary: str, source_signal_id: str) -> SubmitIntentPacket:
    return SubmitIntentPacket(
        intent_id=f"INT_{uuid.uuid4().hex[:12]}",
        symbol=symbol, side=side, order_type=order_type, quantity=quantity,
        price_policy=price_policy, risk_summary=risk_summary, source_signal_id=source_signal_id,
        approval_status="DENIED", simulated=True, real_submit=False, testnet_submit=False, no_submit_enforced=True,
    )

def write_packets(packets: list[SubmitIntentPacket], out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(json.dumps(p.to_dict()) for p in packets) + ("\n" if packets else ""), encoding="utf-8")
