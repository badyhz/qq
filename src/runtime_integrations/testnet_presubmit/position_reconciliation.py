"""Position reconciliation types."""
from __future__ import annotations
import json, pathlib
from dataclasses import dataclass

@dataclass(frozen=True)
class PositionSnapshot:
    symbol: str
    side: str
    quantity: float
    entry_price: float
    simulated: bool
    def to_dict(self) -> dict:
        return {"symbol": self.symbol, "side": self.side, "quantity": self.quantity, "entry_price": self.entry_price, "simulated": self.simulated}

@dataclass(frozen=True)
class ReconciliationResult:
    symbol: str
    status: str  # MATCH, WARN, BLOCKED
    checks: tuple[str, ...]
    def to_dict(self) -> dict:
        return {"symbol": self.symbol, "status": self.status, "checks": list(self.checks)}

def reconcile_position(expected: PositionSnapshot, reported: PositionSnapshot | None) -> ReconciliationResult:
    checks = []
    if reported is None:
        return ReconciliationResult(expected.symbol, "BLOCKED", ("MISSING_SYMBOL",))
    if expected.quantity != reported.quantity:
        checks.append(f"QUANTITY_MISMATCH: expected={expected.quantity}, reported={reported.quantity}")
    else:
        checks.append("quantity_match")
    if expected.side != reported.side:
        checks.append(f"SIDE_MISMATCH: expected={expected.side}, reported={reported.side}")
    else:
        checks.append("side_match")
    status = "MATCH" if not any("MISMATCH" in c for c in checks) else "BLOCKED"
    return ReconciliationResult(expected.symbol, status, tuple(checks))

def write_results(results: list[ReconciliationResult], out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps([r.to_dict() for r in results], indent=2), encoding="utf-8")
