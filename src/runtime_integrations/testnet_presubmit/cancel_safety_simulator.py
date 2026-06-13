"""Cancel safety simulator. Simulates cancel flow without real API calls."""
from __future__ import annotations
import json, pathlib, uuid
from dataclasses import dataclass
from .cancel_safety import CancelIntent, CancelValidation, validate_cancel

@dataclass(frozen=True)
class SimulatedCancelRecord:
    simulated: bool
    real_cancel: bool
    testnet_cancel: bool
    network_called: bool
    no_submit_enforced: bool
    cancel_id: str
    order_id: str
    symbol: str
    validation: CancelValidation
    def to_dict(self) -> dict:
        return {"simulated": self.simulated, "real_cancel": self.real_cancel, "testnet_cancel": self.testnet_cancel, "network_called": self.network_called, "no_submit_enforced": self.no_submit_enforced, "cancel_id": self.cancel_id, "order_id": self.order_id, "symbol": self.symbol, "validation": self.validation.to_dict()}

def simulate_cancel_flow(order_id: str, symbol: str, reason: str, known_orders: set[str], terminal_orders: set[str], approved: bool, kill_switch_blocking: bool) -> SimulatedCancelRecord:
    cancel_id = f"CXL_{uuid.uuid4().hex[:12]}"
    intent = CancelIntent(cancel_id, order_id, symbol, reason)
    validation = validate_cancel(intent, known_orders, terminal_orders, approved, kill_switch_blocking)
    return SimulatedCancelRecord(True, False, False, False, True, cancel_id, order_id, symbol, validation)

def run_cancel_safety_suite() -> list[SimulatedCancelRecord]:
    known = {"ORD_001", "ORD_002", "ORD_003"}
    terminal = {"ORD_003"}
    return [
        simulate_cancel_flow("ORD_001", "BTCUSDT", "user_request", known, terminal, True, False),
        simulate_cancel_flow("ORD_002", "ETHUSDT", "risk_limit", known, terminal, True, False),
        simulate_cancel_flow("ORD_999", "BTCUSDT", "unknown_order", known, terminal, True, False),
        simulate_cancel_flow("ORD_003", "BTCUSDT", "terminal_order", known, terminal, True, False),
        simulate_cancel_flow("ORD_001", "BTCUSDT", "not_approved", known, terminal, False, False),
        simulate_cancel_flow("ORD_001", "BTCUSDT", "kill_switch", known, terminal, True, True),
    ]

def write_records(records: list[SimulatedCancelRecord], out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(json.dumps(r.to_dict()) for r in records) + ("\n" if records else ""), encoding="utf-8")
