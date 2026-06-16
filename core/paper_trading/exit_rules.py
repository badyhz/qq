"""Paper trading exit rules — local simulation only, no real orders."""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional

from core.paper_trading.order_plan import OrderPlan, OrderSide, OrderStatus, ExitReason


@dataclass
class ExitRuleConfig:
    stop_loss_pct: float = 2.0           # % from entry
    take_profit_pct: float = 6.0         # % from entry
    trailing_stop_pct: float = 1.5       # % from high-water mark
    time_stop_bars: int = 50             # max bars to hold
    partial_tp_pcts: tuple = (3.0, 6.0)  # partial TP levels
    partial_tp_sizes: tuple = (0.5, 0.5) # fraction to close at each level


@dataclass
class ExitSignal:
    should_exit: bool
    reason: Optional[ExitReason]
    exit_price: float
    pnl: float
    partial: bool = False
    partial_fraction: float = 0.0


def check_stop_loss(
    plan: OrderPlan,
    current_price: float,
) -> Optional[ExitSignal]:
    """Check if stop loss is hit."""
    if plan.side == OrderSide.BUY:
        if current_price <= plan.stop_loss:
            pnl = (current_price - plan.entry_price) * plan.position_size
            return ExitSignal(True, ExitReason.STOP_LOSS, current_price, pnl)
    else:
        if current_price >= plan.stop_loss:
            pnl = (plan.entry_price - current_price) * plan.position_size
            return ExitSignal(True, ExitReason.STOP_LOSS, current_price, pnl)
    return None


def check_take_profit(
    plan: OrderPlan,
    current_price: float,
) -> Optional[ExitSignal]:
    """Check if take profit is hit."""
    if plan.side == OrderSide.BUY:
        if current_price >= plan.take_profit:
            pnl = (current_price - plan.entry_price) * plan.position_size
            return ExitSignal(True, ExitReason.TAKE_PROFIT, current_price, pnl)
    else:
        if current_price <= plan.take_profit:
            pnl = (plan.entry_price - current_price) * plan.position_size
            return ExitSignal(True, ExitReason.TAKE_PROFIT, current_price, pnl)
    return None


def check_trailing_stop(
    plan: OrderPlan,
    current_price: float,
    high_water_mark: float,
    trailing_pct: float,
) -> Optional[ExitSignal]:
    """Check if trailing stop is hit."""
    if plan.side == OrderSide.BUY:
        trail_price = high_water_mark * (1 - trailing_pct / 100)
        if current_price <= trail_price and current_price > plan.stop_loss:
            pnl = (current_price - plan.entry_price) * plan.position_size
            return ExitSignal(True, ExitReason.TRAILING_STOP, current_price, pnl)
    else:
        trail_price = high_water_mark * (1 + trailing_pct / 100)
        if current_price >= trail_price and current_price < plan.stop_loss:
            pnl = (plan.entry_price - current_price) * plan.position_size
            return ExitSignal(True, ExitReason.TRAILING_STOP, current_price, pnl)
    return None


def check_time_stop(
    plan: OrderPlan,
    bars_held: int,
    current_price: float,
    max_bars: int,
) -> Optional[ExitSignal]:
    """Check if time stop is hit."""
    if bars_held >= max_bars:
        pnl = (current_price - plan.entry_price) * plan.position_size
        if plan.side == OrderSide.SELL:
            pnl = (plan.entry_price - current_price) * plan.position_size
        return ExitSignal(True, ExitReason.TIME_STOP, current_price, pnl)
    return None


def check_invalidation(
    plan: OrderPlan,
    current_price: float,
) -> Optional[ExitSignal]:
    """Check if invalidation price is hit (signal invalidated)."""
    if plan.side == OrderSide.BUY:
        if current_price <= plan.invalidation_price:
            pnl = (current_price - plan.entry_price) * plan.position_size
            return ExitSignal(True, ExitReason.SIGNAL_INVALIDATED, current_price, pnl)
    else:
        if current_price >= plan.invalidation_price:
            pnl = (plan.entry_price - current_price) * plan.position_size
            return ExitSignal(True, ExitReason.SIGNAL_INVALIDATED, current_price, pnl)
    return None


def evaluate_exits(
    plan: OrderPlan,
    current_price: float,
    high_water_mark: float,
    bars_held: int,
    config: ExitRuleConfig,
) -> Optional[ExitSignal]:
    """Evaluate all exit rules in priority order. Returns first triggered exit."""
    if plan.status in (OrderStatus.CANCELLED, OrderStatus.SIMULATED_CLOSED):
        return None

    # Priority: invalidation > stop_loss > trailing > time > take_profit
    inv = check_invalidation(plan, current_price)
    if inv:
        return inv

    sl = check_stop_loss(plan, current_price)
    if sl:
        return sl

    ts = check_trailing_stop(plan, current_price, high_water_mark, config.trailing_stop_pct)
    if ts:
        return ts

    tm = check_time_stop(plan, bars_held, current_price, config.time_stop_bars)
    if tm:
        return tm

    tp = check_take_profit(plan, current_price)
    if tp:
        return tp

    return None
