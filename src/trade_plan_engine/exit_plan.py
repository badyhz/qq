"""Exit plan generator for trade plans."""
from __future__ import annotations
from src.trade_plan_engine.models import ExitPlan, new_id


def generate_exit_plan(
    entry_price: float,
    stop_loss: float,
    ma25: float = 0.0,
    max_hold_bars: int = 48,
) -> ExitPlan:
    r = entry_price - stop_loss
    if r <= 0:
        r = entry_price * 0.03

    tp1 = round(entry_price + 1.5 * r, 8)
    tp2 = round(entry_price + 2.5 * r, 8)
    tp3 = round(entry_price + 4.0 * r, 8)

    if ma25 > 0:
        sl_desc = f"stop_loss at {stop_loss:.8f} (min of price*0.97={entry_price*0.97:.8f}, ma25*0.995={ma25*0.995:.8f})"
    else:
        sl_desc = f"stop_loss at {stop_loss:.8f} (price*0.97)"

    return ExitPlan(
        exit_plan_id=new_id("EP"),
        stop_loss_rule=sl_desc,
        tp1_rule=f"take_profit_1 at {tp1:.8f} (1.5R from entry)",
        tp2_rule=f"take_profit_2 at {tp2:.8f} (2.5R from entry)",
        tp3_rule=f"take_profit_3 at {tp3:.8f} (4R from entry)",
        time_stop_rule=f"exit after {max_hold_bars} bars if TP1 not reached",
        signal_failure_rule="exit if price closes below ma25 or MACD histogram turns negative",
        trailing_stop_rule="after TP1 hit, move stop_loss to entry_price (breakeven)",
        manual_review_required=False,
    )


def compute_stop_loss(price: float, ma25: float = 0.0) -> float:
    if ma25 > 0:
        return round(min(price * 0.97, ma25 * 0.995), 8)
    return round(price * 0.97, 8)


def compute_take_profits(entry_price: float, stop_loss: float) -> tuple[float, float, float]:
    r = entry_price - stop_loss
    if r <= 0:
        r = entry_price * 0.03
    return (
        round(entry_price + 1.5 * r, 8),
        round(entry_price + 2.5 * r, 8),
        round(entry_price + 4.0 * r, 8),
    )
