"""Paper trading alert explainer — generates text only, no webhook."""
from __future__ import annotations
from typing import Dict, Any

from core.paper_trading.order_plan import OrderPlan, OrderSide, OrderStatus


def explain_alert(plan: OrderPlan) -> Dict[str, Any]:
    """Generate a human-readable alert explanation for a paper order plan.

    Returns a dict with all alert fields. No network calls.
    """
    # Why triggered
    trigger_reason = f"Signal from {plan.signal_source}" if plan.signal_source else "Manual signal"

    # Entry zone
    if plan.side == OrderSide.BUY:
        entry_zone = f"Long entry at {plan.entry_price}"
        direction = "LONG"
    else:
        entry_zone = f"Short entry at {plan.entry_price}"
        direction = "SHORT"

    # Risk/reward
    risk_per_unit = abs(plan.entry_price - plan.stop_loss)
    reward_per_unit = abs(plan.take_profit - plan.entry_price)
    rr = reward_per_unit / risk_per_unit if risk_per_unit > 0 else 0

    # Status text
    status_map = {
        OrderStatus.PLANNED_ONLY: "PLANNED — awaiting risk sizing",
        OrderStatus.WAITING_FOR_HUMAN_APPROVAL: "WAITING_FOR_HUMAN_APPROVAL — needs human confirmation",
        OrderStatus.CANCELLED: "CANCELLED — rejected by risk checks",
        OrderStatus.SIMULATED_CLOSED: "SIMULATED_CLOSED — trade complete",
    }

    return {
        "trigger_reason": trigger_reason,
        "symbol": plan.symbol,
        "direction": direction,
        "entry_zone": entry_zone,
        "entry_price": plan.entry_price,
        "stop_loss": plan.stop_loss,
        "take_profit": plan.take_profit,
        "invalidation_price": plan.invalidation_price,
        "risk_amount": plan.risk_amount,
        "position_size": plan.position_size,
        "rr_ratio": round(rr, 2),
        "status": status_map.get(plan.status, plan.status.value),
        "risk_warning": (
            f"This is a PAPER TRADE simulation. "
            f"Max loss: {plan.risk_amount:.2f} USDT. "
            f"Position size: {plan.position_size:.8f}. "
            f"No real order will be placed."
        ),
    }


def format_alert_text(alert: Dict[str, Any]) -> str:
    """Format alert dict as readable text."""
    lines = [
        f"=== PAPER TRADE ALERT ===",
        f"Symbol: {alert['symbol']}",
        f"Direction: {alert['direction']}",
        f"Trigger: {alert['trigger_reason']}",
        f"",
        f"Entry: {alert['entry_price']}",
        f"Stop Loss: {alert['stop_loss']}",
        f"Take Profit: {alert['take_profit']}",
        f"Invalidation: {alert['invalidation_price']}",
        f"R:R Ratio: {alert['rr_ratio']}",
        f"",
        f"Position Size: {alert['position_size']}",
        f"Risk Amount: {alert['risk_amount']} USDT",
        f"",
        f"Status: {alert['status']}",
        f"",
        f"Risk Warning: {alert['risk_warning']}",
    ]
    return "\n".join(lines)
