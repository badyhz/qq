"""Paper trading order plan — local simulation only, no real orders."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(str, Enum):
    PLANNED_ONLY = "PLANNED_ONLY"
    WAITING_FOR_HUMAN_APPROVAL = "WAITING_FOR_HUMAN_APPROVAL"
    CANCELLED = "CANCELLED"
    SIMULATED_CLOSED = "SIMULATED_CLOSED"


class ExitReason(str, Enum):
    STOP_LOSS = "STOP_LOSS"
    TAKE_PROFIT = "TAKE_PROFIT"
    PARTIAL_TP = "PARTIAL_TP"
    TRAILING_STOP = "TRAILING_STOP"
    TIME_STOP = "TIME_STOP"
    SIGNAL_INVALIDATED = "SIGNAL_INVALIDATED"
    MANUAL_CANCEL = "MANUAL_CANCEL"


@dataclass(frozen=True)
class OrderPlan:
    """Immutable paper order plan. All fields set at creation."""
    plan_id: str
    symbol: str
    side: OrderSide
    entry_price: float
    stop_loss: float
    take_profit: float
    invalidation_price: float
    risk_amount: float
    position_size: float
    status: OrderStatus = OrderStatus.PLANNED_ONLY
    signal_source: str = ""
    rr_ratio: float = 0.0
    exit_reason: Optional[ExitReason] = None
    closed_pnl: float = 0.0

    def __post_init__(self):
        if self.status not in (
            OrderStatus.PLANNED_ONLY,
            OrderStatus.WAITING_FOR_HUMAN_APPROVAL,
            OrderStatus.CANCELLED,
            OrderStatus.SIMULATED_CLOSED,
        ):
            raise ValueError(f"Invalid status: {self.status}")
        if self.side not in (OrderSide.BUY, OrderSide.SELL):
            raise ValueError(f"Invalid side: {self.side}")
        if self.entry_price <= 0:
            raise ValueError("entry_price must be positive")
        if self.risk_amount < 0:
            raise ValueError("risk_amount must be non-negative")
        if self.position_size < 0:
            raise ValueError("position_size must be non-negative")

    def with_status(self, status: OrderStatus, exit_reason: Optional[ExitReason] = None, closed_pnl: float = 0.0) -> OrderPlan:
        return OrderPlan(
            plan_id=self.plan_id,
            symbol=self.symbol,
            side=self.side,
            entry_price=self.entry_price,
            stop_loss=self.stop_loss,
            take_profit=self.take_profit,
            invalidation_price=self.invalidation_price,
            risk_amount=self.risk_amount,
            position_size=self.position_size,
            status=status,
            signal_source=self.signal_source,
            rr_ratio=self.rr_ratio,
            exit_reason=exit_reason or self.exit_reason,
            closed_pnl=closed_pnl,
        )

    def to_dict(self):
        return {
            "plan_id": self.plan_id,
            "symbol": self.symbol,
            "side": self.side.value,
            "entry_price": self.entry_price,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "invalidation_price": self.invalidation_price,
            "risk_amount": self.risk_amount,
            "position_size": self.position_size,
            "status": self.status.value,
            "signal_source": self.signal_source,
            "rr_ratio": self.rr_ratio,
            "exit_reason": self.exit_reason.value if self.exit_reason else None,
            "closed_pnl": self.closed_pnl,
        }
