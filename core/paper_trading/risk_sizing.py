"""Paper trading risk sizing — local calculation only."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

from core.paper_trading.order_plan import OrderPlan, OrderSide, OrderStatus


@dataclass
class RiskSizingConfig:
    max_risk_per_trade_pct: float = 1.0       # % of equity per trade
    max_position_pct: float = 10.0             # % of equity max position
    min_rr_ratio: float = 1.5                  # minimum reward:risk
    max_margin_cap: float = 10000.0            # max notional value
    equity: float = 100000.0                   # simulated equity


@dataclass
class RiskSizingResult:
    approved: bool
    position_size: float
    risk_amount: float
    rr_ratio: float
    rejection_reason: str = ""


def calculate_risk(
    entry: float,
    stop_loss: float,
    take_profit: float,
    config: RiskSizingConfig,
    side: OrderSide = OrderSide.BUY,
) -> RiskSizingResult:
    """Calculate position size and validate risk constraints."""
    if entry <= 0 or stop_loss <= 0 or take_profit <= 0:
        return RiskSizingResult(False, 0, 0, 0, "Prices must be positive")

    # Risk per unit
    if side == OrderSide.BUY:
        risk_per_unit = abs(entry - stop_loss)
        reward_per_unit = abs(take_profit - entry)
    else:
        risk_per_unit = abs(stop_loss - entry)
        reward_per_unit = abs(entry - take_profit)

    if risk_per_unit == 0:
        return RiskSizingResult(False, 0, 0, 0, "Stop loss equals entry")

    # RR ratio
    rr_ratio = reward_per_unit / risk_per_unit

    if rr_ratio < config.min_rr_ratio:
        return RiskSizingResult(
            False, 0, 0, rr_ratio,
            f"RR {rr_ratio:.2f} below minimum {config.min_rr_ratio}",
        )

    # Max risk amount
    max_risk = config.equity * config.max_risk_per_trade_pct / 100.0

    # Position size by risk
    position_size = max_risk / risk_per_unit

    # Position value cap
    position_value = position_size * entry
    max_position_value = config.equity * config.max_position_pct / 100.0

    if position_value > max_position_value:
        position_size = max_position_value / entry
        position_value = position_size * entry

    # Margin cap
    if position_value > config.max_margin_cap:
        position_size = config.max_margin_cap / entry
        position_value = position_size * entry

    risk_amount = position_size * risk_per_unit

    return RiskSizingResult(
        approved=True,
        position_size=round(position_size, 8),
        risk_amount=round(risk_amount, 2),
        rr_ratio=round(rr_ratio, 2),
    )


def apply_risk_sizing(
    plan: OrderPlan,
    config: RiskSizingConfig,
) -> OrderPlan:
    """Apply risk sizing to an order plan. Returns new plan with sizing applied."""
    result = calculate_risk(
        entry=plan.entry_price,
        stop_loss=plan.stop_loss,
        take_profit=plan.take_profit,
        config=config,
        side=plan.side,
    )

    if not result.approved:
        return plan.with_status(OrderStatus.CANCELLED)

    return OrderPlan(
        plan_id=plan.plan_id,
        symbol=plan.symbol,
        side=plan.side,
        entry_price=plan.entry_price,
        stop_loss=plan.stop_loss,
        take_profit=plan.take_profit,
        invalidation_price=plan.invalidation_price,
        risk_amount=result.risk_amount,
        position_size=result.position_size,
        status=OrderStatus.WAITING_FOR_HUMAN_APPROVAL,
        signal_source=plan.signal_source,
        rr_ratio=result.rr_ratio,
    )
