"""Submit intent validator. Validates intent packets for safety."""
from __future__ import annotations
import json, pathlib
from dataclasses import dataclass

@dataclass(frozen=True)
class IntentValidation:
    intent_id: str
    valid: bool
    checks: tuple[str, ...]
    def to_dict(self) -> dict:
        return {"intent_id": self.intent_id, "valid": self.valid, "checks": list(self.checks)}

REQUIRED_FIELDS = ("intent_id", "symbol", "side", "order_type", "quantity", "price_policy", "risk_summary", "source_signal_id", "approval_status", "simulated", "real_submit", "testnet_submit", "no_submit_enforced")

def validate_intent(packet: dict) -> IntentValidation:
    checks = []
    ok = True
    for f in REQUIRED_FIELDS:
        if f in packet:
            checks.append(f"required_present: {f}")
        else:
            checks.append(f"REQUIRED_MISSING: {f}")
            ok = False
    if packet.get("simulated") is not True:
        checks.append("SIMULATED_MUST_BE_TRUE"); ok = False
    if packet.get("real_submit") is not False:
        checks.append("REAL_SUBMIT_MUST_BE_FALSE"); ok = False
    if packet.get("testnet_submit") is not False:
        checks.append("TESTNET_SUBMIT_MUST_BE_FALSE"); ok = False
    if packet.get("no_submit_enforced") is not True:
        checks.append("NO_SUBMIT_ENFORCED_MUST_BE_TRUE"); ok = False
    if packet.get("approval_status") != "DENIED":
        checks.append("APPROVAL_STATUS_MUST_BE_DENIED"); ok = False
    return IntentValidation(packet.get("intent_id", "unknown"), ok, tuple(checks))

def write_validations(vals: list[IntentValidation], out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps([v.to_dict() for v in vals], indent=2), encoding="utf-8")
