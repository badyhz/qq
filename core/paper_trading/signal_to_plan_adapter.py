"""Adapter: convert signal envelope to paper order plan. No real orders."""
from __future__ import annotations
from typing import Dict, Any, Optional

from core.paper_trading.order_plan import OrderPlan, OrderSide, OrderStatus


def signal_envelope_to_order_plan(
    envelope: Dict[str, Any],
    plan_id_prefix: str = "S2P",
    plan_counter: int = 0,
) -> Optional[OrderPlan]:
    """Convert a signal envelope dict to a paper OrderPlan.

    Expected envelope keys:
        symbol, side, entry_price, stop_loss, take_profit,
        invalidation_price (optional, defaults to stop_loss),
        signal_source (optional)

    Returns None if envelope is invalid.
    """
    required = ("symbol", "side", "entry_price", "stop_loss", "take_profit")
    for key in required:
        if key not in envelope:
            return None

    try:
        side = OrderSide(envelope["side"])
    except ValueError:
        return None

    entry = float(envelope["entry_price"])
    sl = float(envelope["stop_loss"])
    tp = float(envelope["take_profit"])
    inv = float(envelope.get("invalidation_price", sl))

    if entry <= 0 or sl <= 0 or tp <= 0:
        return None

    # Basic sanity: SL must be on correct side
    if side == OrderSide.BUY and sl >= entry:
        return None
    if side == OrderSide.SELL and sl <= entry:
        return None

    # TP must be on correct side
    if side == OrderSide.BUY and tp <= entry:
        return None
    if side == OrderSide.SELL and tp >= entry:
        return None

    plan_id = f"{plan_id_prefix}-{plan_counter:04d}"

    return OrderPlan(
        plan_id=plan_id,
        symbol=envelope["symbol"],
        side=side,
        entry_price=entry,
        stop_loss=sl,
        take_profit=tp,
        invalidation_price=inv,
        risk_amount=0.0,   # filled by risk_sizing
        position_size=0.0,  # filled by risk_sizing
        status=OrderStatus.PLANNED_ONLY,
        signal_source=envelope.get("signal_source", ""),
    )
