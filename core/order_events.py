from datetime import datetime, timezone
from typing import Any, Optional

from core.order_state import (
    ORDER_EVENT_FILLED,
    ORDER_EVENT_PARTIALLY_FILLED,
    ORDER_EVENT_SUBMITTED,
    ORDER_STATUS_NEW,
    get_next_order_status,
)


def initialize_order(
    *,
    order_id: str,
    trade_id: Optional[Any],
    symbol: str,
    side: str,
    qty: float,
    timestamp: Optional[Any] = None,
) -> tuple[dict, dict]:
    created_at = _normalize_timestamp(timestamp)
    normalized_qty = max(_to_float(qty), 0.0)
    order = {
        "order_id": str(order_id),
        "trade_id": trade_id,
        "symbol": str(symbol),
        "side": str(side),
        "status": ORDER_STATUS_NEW,
        "total_qty": normalized_qty,
        "filled_qty": 0.0,
        "remaining_qty": normalized_qty,
        "avg_fill_price": 0.0,
        "reason": "",
        "timestamp": created_at,
        "event_type": ORDER_EVENT_SUBMITTED,
    }
    event = build_order_event(order=order, event_type=ORDER_EVENT_SUBMITTED, timestamp=created_at)
    return order, event


def apply_order_event(
    order: dict,
    *,
    event_type: str,
    filled_qty: Optional[float] = None,
    remaining_qty: Optional[float] = None,
    avg_fill_price: Optional[float] = None,
    reason: str = "",
    timestamp: Optional[Any] = None,
) -> dict:
    current_status = order.get("status")
    resolved_event_type = event_type

    updated = dict(order)
    total_qty = _to_float(updated.get("total_qty", 0.0))
    prev_filled = _to_float(updated.get("filled_qty", 0.0))
    prev_avg_fill = _to_float(updated.get("avg_fill_price", 0.0))
    next_filled = prev_filled
    next_avg_fill = prev_avg_fill

    if event_type in (ORDER_EVENT_PARTIALLY_FILLED, ORDER_EVENT_FILLED):
        fill_transition = get_next_order_status(current_status, event_type)
        if fill_transition is None:
            return {
                "ok": False,
                "reason": "invalid_state_transition",
                "current_status": current_status,
                "event_type": event_type,
            }
        qty_from_filled = None if filled_qty in ("", None) else _to_float(filled_qty, default=-1.0)
        qty_from_remaining = (
            None if remaining_qty in ("", None) else total_qty - _to_float(remaining_qty, default=total_qty + 1.0)
        )
        if qty_from_filled is None and qty_from_remaining is None:
            return {"ok": False, "reason": "missing_fill_progress"}

        candidates = [value for value in (qty_from_filled, qty_from_remaining) if value is not None]
        next_filled = max(candidates) if candidates else prev_filled
        if next_filled < prev_filled:
            return {"ok": False, "reason": "non_monotonic_fill_progress"}
        if next_filled > total_qty + 1e-12:
            return {"ok": False, "reason": "overfill"}

        fill_delta = next_filled - prev_filled
        if fill_delta > 0:
            if avg_fill_price in ("", None):
                if prev_avg_fill <= 0:
                    return {"ok": False, "reason": "invalid_avg_fill_price"}
                fill_price = prev_avg_fill
            else:
                fill_price = _to_float(avg_fill_price, default=0.0)
                if fill_price <= 0:
                    return {"ok": False, "reason": "invalid_avg_fill_price"}
            next_avg_fill = (
                ((prev_avg_fill * prev_filled) + (fill_price * fill_delta)) / next_filled
                if next_filled > 0
                else 0.0
            )
        elif avg_fill_price not in ("", None):
            override_avg = _to_float(avg_fill_price, default=0.0)
            if override_avg > 0 and next_filled > 0:
                next_avg_fill = override_avg

        if next_filled > 0 and next_avg_fill <= 0:
            return {"ok": False, "reason": "invalid_avg_fill_price"}

        if next_filled >= total_qty - 1e-12:
            next_filled = total_qty
            resolved_event_type = ORDER_EVENT_FILLED

    next_status = get_next_order_status(current_status, resolved_event_type)
    if next_status is None:
        return {
            "ok": False,
            "reason": "invalid_state_transition",
            "current_status": current_status,
            "event_type": resolved_event_type,
        }

    next_remaining = total_qty - next_filled
    if next_remaining < -1e-12:
        return {"ok": False, "reason": "negative_remaining_qty"}
    next_remaining = max(next_remaining, 0.0)
    updated["status"] = next_status
    updated["filled_qty"] = next_filled
    updated["remaining_qty"] = next_remaining
    updated["avg_fill_price"] = next_avg_fill
    updated["reason"] = str(reason or "")
    updated["timestamp"] = _normalize_timestamp(timestamp)
    updated["event_type"] = resolved_event_type

    event = build_order_event(order=updated, event_type=resolved_event_type, timestamp=updated["timestamp"])
    return {"ok": True, "order": updated, "event": event}


def build_order_event(order: dict, *, event_type: str, timestamp: Optional[Any] = None) -> dict:
    return {
        "order_id": order.get("order_id"),
        "trade_id": order.get("trade_id"),
        "symbol": order.get("symbol", ""),
        "side": order.get("side", ""),
        "status": order.get("status", ""),
        "event_type": event_type,
        "filled_qty": _to_float(order.get("filled_qty", 0.0)),
        "remaining_qty": _to_float(order.get("remaining_qty", 0.0)),
        "avg_fill_price": _to_float(order.get("avg_fill_price", 0.0)),
        "reason": order.get("reason", ""),
        "timestamp": _normalize_timestamp(timestamp or order.get("timestamp")),
    }


def _normalize_timestamp(value: Optional[Any]) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    if value not in ("", None):
        return str(value)
    return datetime.now(timezone.utc).isoformat()


def _to_float(value: Any, default: float = 0.0) -> float:
    if value in ("", None):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
