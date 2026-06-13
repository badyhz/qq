"""Cancel safety types and validation."""
from __future__ import annotations
import json, pathlib
from dataclasses import dataclass

@dataclass(frozen=True)
class CancelIntent:
    cancel_id: str
    order_id: str
    symbol: str
    reason: str
    def to_dict(self) -> dict:
        return {"cancel_id": self.cancel_id, "order_id": self.order_id, "symbol": self.symbol, "reason": self.reason}

@dataclass(frozen=True)
class CancelValidation:
    cancel_id: str
    valid: bool
    checks: tuple[str, ...]
    def to_dict(self) -> dict:
        return {"cancel_id": self.cancel_id, "valid": self.valid, "checks": list(self.checks)}

def validate_cancel(intent: CancelIntent, known_orders: set[str], terminal_orders: set[str], approved: bool, kill_switch_blocking: bool) -> CancelValidation:
    checks = []
    ok = True
    if intent.order_id in known_orders:
        checks.append("order_known")
    else:
        checks.append("ORDER_UNKNOWN"); ok = False
    if intent.order_id in terminal_orders:
        checks.append("ORDER_ALREADY_TERMINAL")
        checks.append("terminal_order_blocked")
        ok = False
    else:
        checks.append("order_not_terminal")
    if approved:
        checks.append("cancel_approved")
    else:
        checks.append("CANCEL_NOT_APPROVED"); ok = False
    if kill_switch_blocking:
        checks.append("KILL_SWITCH_BLOCKS_CANCEL"); ok = False
    else:
        checks.append("kill_switch_not_blocking")
    return CancelValidation(intent.cancel_id, ok, tuple(checks))

def write_validation(val: CancelValidation, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(val.to_dict(), indent=2), encoding="utf-8")
