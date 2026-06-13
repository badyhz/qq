"""Freeze packet validator."""
from __future__ import annotations
import json, pathlib
from dataclasses import dataclass

@dataclass(frozen=True)
class FreezeCheck:
    check_id: str
    passed: bool
    detail: str
    def to_dict(self) -> dict:
        return {"check_id": self.check_id, "passed": self.passed, "detail": self.detail}

def _packet_dict(packet) -> dict:
    if isinstance(packet, dict):
        return packet
    if hasattr(packet, "to_dict"):
        return packet.to_dict()
    return dict(packet)

def validate_freeze_packet(packet: dict) -> list[FreezeCheck]:
    packet = _packet_dict(packet)
    checks = []
    checks.append(FreezeCheck("has_frozen_gates", "frozen_gates" in packet and len(packet.get("frozen_gates", [])) >= 3, "frozen gates present"))
    checks.append(FreezeCheck("submit_gate_locked", packet.get("submit_gate_state") == "LOCKED", f"state={packet.get('submit_gate_state')}"))
    checks.append(FreezeCheck("cancel_gate_locked", packet.get("cancel_gate_state") == "LOCKED", f"state={packet.get('cancel_gate_state')}"))
    checks.append(FreezeCheck("recon_gate_locked", packet.get("reconciliation_gate_state") == "LOCKED", f"state={packet.get('reconciliation_gate_state')}"))
    checks.append(FreezeCheck("no_real_trading", packet.get("real_trading_allowed") is False, f"real_trading_allowed={packet.get('real_trading_allowed')}"))
    checks.append(FreezeCheck("no_testnet_submit", packet.get("testnet_submit_allowed") is False, f"testnet_submit_allowed={packet.get('testnet_submit_allowed')}"))
    checks.append(FreezeCheck("has_approvals", len(packet.get("required_human_approvals", [])) >= 2, "approvals present"))
    checks.append(FreezeCheck("has_forbidden", len(packet.get("forbidden_actions", [])) >= 3, "forbidden actions listed"))
    return checks

def write_checks(checks: list[FreezeCheck], out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps([c.to_dict() for c in checks], indent=2), encoding="utf-8")
