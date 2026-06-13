"""Simulated exchange adapter. No network, no real keys, no real submit."""
from __future__ import annotations
import json, pathlib, uuid
from .adapter_contract import SandboxAdapterContract
from .sandbox_types import OrderIntent, SimulatedSubmitResult, SimulatedBalance, SimulatedPosition, ConnectionConfig, ValidationResult

class SimulatedExchangeAdapter(SandboxAdapterContract):
    def __init__(self) -> None:
        self._orders: dict[str, SimulatedSubmitResult] = {}
        self._balances: dict[str, SimulatedBalance] = {
            "USDT": SimulatedBalance("USDT", 10000.0, 0.0, 10000.0, True),
            "BTC": SimulatedBalance("BTC", 0.5, 0.0, 0.5, True),
            "ETH": SimulatedBalance("ETH", 5.0, 0.0, 5.0, True),
        }
        self._positions: list[SimulatedPosition] = []

    def validate_connection_config(self, config: ConnectionConfig) -> ValidationResult:
        errors = []
        if "REPLACE" in config.api_key or "placeholder" in config.api_key.lower():
            pass  # expected for stub
        else:
            errors.append("config must use placeholder credentials only")
        if not config.testnet:
            errors.append("testnet must be True")
        return ValidationResult(len(errors) == 0, tuple(errors))

    def build_order_intent(self, symbol: str, side: str, order_type: str, quantity: float, price: float | None, source_signal_id: str) -> OrderIntent:
        return OrderIntent(symbol=symbol, side=side, order_type=order_type, quantity=quantity, price=price, price_policy=order_type, source_signal_id=source_signal_id)

    def validate_order_intent(self, intent: OrderIntent) -> ValidationResult:
        errors = []
        if not intent.symbol:
            errors.append("symbol required")
        if intent.side not in ("BUY", "SELL"):
            errors.append(f"invalid side: {intent.side}")
        if intent.quantity <= 0:
            errors.append("quantity must be positive")
        if intent.order_type == "LIMIT" and (intent.price is None or intent.price <= 0):
            errors.append("LIMIT order requires positive price")
        return ValidationResult(len(errors) == 0, tuple(errors))

    def simulate_submit(self, intent: OrderIntent) -> SimulatedSubmitResult:
        order_id = f"SIM_{uuid.uuid4().hex[:12]}"
        result = SimulatedSubmitResult(
            simulated=True, real_submit=False, testnet_submit=False, no_submit_enforced=True,
            order_id=order_id, status="SIMULATED_NEW", symbol=intent.symbol, side=intent.side, quantity=intent.quantity,
            fill_price=intent.price if intent.price else 0.0,
        )
        self._orders[order_id] = result
        return result

    def simulate_cancel(self, order_id: str, symbol: str) -> SimulatedSubmitResult:
        if order_id in self._orders:
            orig = self._orders[order_id]
            cancelled = SimulatedSubmitResult(
                simulated=True, real_submit=False, testnet_submit=False, no_submit_enforced=True,
                order_id=order_id, status="SIMULATED_CANCELLED", symbol=symbol, side=orig.side, quantity=orig.quantity, fill_price=None,
            )
            self._orders[order_id] = cancelled
            return cancelled
        return SimulatedSubmitResult(
            simulated=True, real_submit=False, testnet_submit=False, no_submit_enforced=True,
            order_id=order_id, status="SIMULATED_NOT_FOUND", symbol=symbol, side="UNKNOWN", quantity=0.0, fill_price=None,
        )

    def get_simulated_balance(self, asset: str) -> SimulatedBalance:
        return self._balances.get(asset, SimulatedBalance(asset, 0.0, 0.0, 0.0, True))

    def get_simulated_positions(self) -> tuple[SimulatedPosition, ...]:
        return tuple(self._positions)

def write_adapter_report(adapter: SimulatedExchangeAdapter, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Simulated Exchange Adapter Report", "", "All operations are simulation-only.", "", "- simulated: true", "- real_submit: false", "- testnet_submit: false", "- no_submit_enforced: true", ""]
    out.write_text("\n".join(lines), encoding="utf-8")
