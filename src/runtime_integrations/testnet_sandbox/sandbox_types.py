"""Sandbox types for testnet sandbox adapter."""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class OrderIntent:
    symbol: str
    side: str  # BUY, SELL
    order_type: str  # LIMIT, MARKET
    quantity: float
    price: float | None
    price_policy: str  # LIMIT, MARKET, BEST_EFFORT
    source_signal_id: str
    def to_dict(self) -> dict:
        return {"symbol": self.symbol, "side": self.side, "order_type": self.order_type, "quantity": self.quantity, "price": self.price, "price_policy": self.price_policy, "source_signal_id": self.source_signal_id}

@dataclass(frozen=True)
class SimulatedSubmitResult:
    simulated: bool
    real_submit: bool
    testnet_submit: bool
    no_submit_enforced: bool
    order_id: str
    status: str  # SIMULATED_NEW, SIMULATED_FILLED, SIMULATED_CANCELLED, SIMULATED_REJECTED
    symbol: str
    side: str
    quantity: float
    fill_price: float | None
    def to_dict(self) -> dict:
        return {"simulated": self.simulated, "real_submit": self.real_submit, "testnet_submit": self.testnet_submit, "no_submit_enforced": self.no_submit_enforced, "order_id": self.order_id, "status": self.status, "symbol": self.symbol, "side": self.side, "quantity": self.quantity, "fill_price": self.fill_price}

@dataclass(frozen=True)
class SimulatedBalance:
    asset: str
    free: float
    locked: float
    total: float
    simulated: bool
    def to_dict(self) -> dict:
        return {"asset": self.asset, "free": self.free, "locked": self.locked, "total": self.total, "simulated": self.simulated}

@dataclass(frozen=True)
class SimulatedPosition:
    symbol: str
    side: str
    quantity: float
    entry_price: float
    unrealized_pnl: float
    simulated: bool
    def to_dict(self) -> dict:
        return {"symbol": self.symbol, "side": self.side, "quantity": self.quantity, "entry_price": self.entry_price, "unrealized_pnl": self.unrealized_pnl, "simulated": self.simulated}

@dataclass(frozen=True)
class ConnectionConfig:
    api_key: str  # placeholder only, never real
    api_secret: str  # placeholder only, never real
    base_url: str  # placeholder only, never real
    testnet: bool
    def to_dict(self) -> dict:
        return {"api_key": "***REDACTED***", "api_secret": "***REDACTED***", "base_url": self.base_url, "testnet": self.testnet}

@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    errors: tuple[str, ...]
    def to_dict(self) -> dict:
        return {"valid": self.valid, "errors": list(self.errors)}
