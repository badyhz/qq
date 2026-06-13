"""Human approval freeze packet. Freezes no-submit state."""
from __future__ import annotations
import json, pathlib, uuid
from dataclasses import dataclass
from datetime import datetime, timezone

@dataclass(frozen=True)
class FrozenGate:
    gate_id: str
    state: str
    submit_allowed: bool = False
    def to_dict(self) -> dict:
        return {"gate_id": self.gate_id, "state": self.state, "submit_allowed": self.submit_allowed}

@dataclass(frozen=True)
class FreezePacket:
    packet_id: str
    created_at: str
    baseline_commit: str
    baseline_tag: str
    current_status: str
    frozen_gates: tuple[FrozenGate, ...]
    submit_gate_state: str
    cancel_gate_state: str
    reconciliation_gate_state: str
    real_trading_allowed: bool
    testnet_submit_allowed: bool
    required_human_approvals: tuple[str, ...]
    next_phase_scope: str
    forbidden_actions: tuple[str, ...]
    operator_ack_required: bool
    @property
    def trading_enabled(self) -> bool:
        return self.real_trading_allowed
    @property
    def submit_allowed(self) -> bool:
        return self.testnet_submit_allowed
    def to_dict(self) -> dict:
        d = {k: getattr(self, k) for k in self.__dataclass_fields__}
        d["frozen_gates"] = [gate.to_dict() for gate in d["frozen_gates"]]
        d["required_human_approvals"] = list(d["required_human_approvals"])
        d["forbidden_actions"] = list(d["forbidden_actions"])
        return d

def create_freeze_packet() -> FreezePacket:
    return FreezePacket(
        packet_id=f"FREEZE_{uuid.uuid4().hex[:12]}",
        created_at=datetime.now(timezone.utc).isoformat(),
        baseline_commit="f0a44fe", baseline_tag="exchange-sandbox-final-gate-review-complete",
        current_status="EXCHANGE_SANDBOX_FINAL_GATE_SUITE_PASS",
        frozen_gates=(
            FrozenGate("submit_gate", "LOCKED", False),
            FrozenGate("cancel_gate", "LOCKED", False),
            FrozenGate("reconciliation_gate", "LOCKED", False),
        ),
        submit_gate_state="LOCKED", cancel_gate_state="LOCKED", reconciliation_gate_state="LOCKED",
        real_trading_allowed=False, testnet_submit_allowed=False,
        required_human_approvals=("operator_ack", "reviewer_approval", "security_review"),
        next_phase_scope="External sandbox adapter dry-run with real testnet endpoints",
        forbidden_actions=("real_submit", "real_credentials", "live_trading", "auto_submit", "gate_unlock"),
        operator_ack_required=True,
    )

def write_packet(packet: FreezePacket, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(packet.to_dict(), indent=2), encoding="utf-8")

def render_report(packet: FreezePacket) -> str:
    lines = ["# Human Approval Freeze Packet", "", "## Frozen State", ""]
    for k, v in packet.to_dict().items():
        lines.append(f"- {k}: {v}")
    lines.extend(["", "## Conclusion", "", "HUMAN_APPROVAL_FREEZE_PACKET_VALID", ""])
    return "\n".join(lines)
