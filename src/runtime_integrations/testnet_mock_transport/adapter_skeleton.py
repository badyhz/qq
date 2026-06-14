"""External adapter skeleton — no network, mock only."""
from __future__ import annotations
import json, pathlib, uuid
from dataclasses import dataclass
from datetime import datetime, timezone

@dataclass(frozen=True)
class OrderRequest:
    request_id: str
    symbol: str
    side: str  # BUY, SELL
    order_type: str  # LIMIT, MARKET
    quantity: str
    price: str
    time_in_force: str  # GTC, IOC, FOK
    def to_dict(self) -> dict:
        return {"request_id": self.request_id, "symbol": self.symbol, "side": self.side, "order_type": self.order_type, "quantity": self.quantity, "price": self.price, "time_in_force": self.time_in_force}

@dataclass(frozen=True)
class DryRunResult:
    result_id: str
    operation: str  # submit_order_dry_run, cancel_order_dry_run, reconcile_balance_dry_run, reconcile_position_dry_run
    simulated: bool
    real_submit: bool
    testnet_submit: bool
    no_submit_enforced: bool
    mock_fixture: str
    timestamp: str
    def to_dict(self) -> dict:
        return {"result_id": self.result_id, "operation": self.operation, "simulated": self.simulated, "real_submit": self.real_submit, "testnet_submit": self.testnet_submit, "no_submit_enforced": self.no_submit_enforced, "mock_fixture": self.mock_fixture, "timestamp": self.timestamp}

def build_order_request(symbol: str, side: str, order_type: str, quantity: str, price: str, time_in_force: str = "GTC") -> OrderRequest:
    return OrderRequest(
        request_id=f"ORD_{uuid.uuid4().hex[:12]}",
        symbol=symbol, side=side, order_type=order_type,
        quantity=quantity, price=price, time_in_force=time_in_force,
    )

def validate_order_request(req: OrderRequest) -> dict:
    errors = []
    if req.symbol not in ("BTCUSDT", "ETHUSDT", "BNBUSDT"):
        errors.append(f"Symbol {req.symbol} not in allowlist")
    if req.side not in ("BUY", "SELL"):
        errors.append(f"Invalid side: {req.side}")
    if req.order_type not in ("LIMIT", "MARKET"):
        errors.append(f"Invalid order type: {req.order_type}")
    try:
        qty = float(req.quantity)
        if qty <= 0:
            errors.append("Quantity must be positive")
    except ValueError:
        errors.append("Invalid quantity")
    if req.order_type == "LIMIT":
        try:
            price = float(req.price)
            if price <= 0:
                errors.append("Price must be positive")
        except ValueError:
            errors.append("Invalid price")
    return {"valid": len(errors) == 0, "errors": errors}

def submit_order_dry_run(req: OrderRequest, fixture: str = "order_accepted") -> DryRunResult:
    return DryRunResult(
        result_id=f"DRY_{uuid.uuid4().hex[:12]}",
        operation="submit_order_dry_run",
        simulated=True, real_submit=False, testnet_submit=False, no_submit_enforced=True,
        mock_fixture=fixture,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

def cancel_order_dry_run(order_id: str, fixture: str = "cancel_success") -> DryRunResult:
    return DryRunResult(
        result_id=f"DRY_{uuid.uuid4().hex[:12]}",
        operation="cancel_order_dry_run",
        simulated=True, real_submit=False, testnet_submit=False, no_submit_enforced=True,
        mock_fixture=fixture,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

def reconcile_balance_dry_run(fixture: str = "balance_mock") -> DryRunResult:
    return DryRunResult(
        result_id=f"DRY_{uuid.uuid4().hex[:12]}",
        operation="reconcile_balance_dry_run",
        simulated=True, real_submit=False, testnet_submit=False, no_submit_enforced=True,
        mock_fixture=fixture,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

def reconcile_position_dry_run(fixture: str = "position_mock") -> DryRunResult:
    return DryRunResult(
        result_id=f"DRY_{uuid.uuid4().hex[:12]}",
        operation="reconcile_position_dry_run",
        simulated=True, real_submit=False, testnet_submit=False, no_submit_enforced=True,
        mock_fixture=fixture,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

def write_skeleton(data: dict, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2), encoding="utf-8")

def render_report() -> str:
    lines = ["# Adapter Implementation Skeleton", "",
        "**adapter_mode=DRY_RUN_MOCK_ONLY**",
        "**network_client_implemented=false**",
        "**real_submit=false**",
        "**testnet_submit=false**",
        "**submit_allowed=false**", "",
        "## Available Operations", "",
        "- build_order_request",
        "- validate_order_request",
        "- submit_order_dry_run",
        "- cancel_order_dry_run",
        "- reconcile_balance_dry_run",
        "- reconcile_position_dry_run",
        "", "## Conclusion", "",
        "ADAPTER_SKELETON_NO_NETWORK_READY",
        "TESTNET_SUBMIT_NOT_ALLOWED",
        ""]
    return "\n".join(lines)
