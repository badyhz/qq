from datetime import datetime, timezone
from typing import Any

from core.order_state import (
    ORDER_EVENT_ACCEPTED,
    ORDER_EVENT_CANCELED,
    ORDER_EVENT_FILLED,
    ORDER_EVENT_PARTIALLY_FILLED,
    ORDER_EVENT_REJECTED,
    ORDER_STATUS_ACCEPTED,
    ORDER_STATUS_CANCELED,
    ORDER_STATUS_FILLED,
    ORDER_STATUS_PARTIALLY_FILLED,
    ORDER_STATUS_REJECTED,
)


EXTERNAL_STATUS_MAP = {
    "NEW": (ORDER_EVENT_ACCEPTED, ORDER_STATUS_ACCEPTED),
    "PARTIALLY_FILLED": (ORDER_EVENT_PARTIALLY_FILLED, ORDER_STATUS_PARTIALLY_FILLED),
    "FILLED": (ORDER_EVENT_FILLED, ORDER_STATUS_FILLED),
    "CANCELED": (ORDER_EVENT_CANCELED, ORDER_STATUS_CANCELED),
    "REJECTED": (ORDER_EVENT_REJECTED, ORDER_STATUS_REJECTED),
}


def adapt_broker_order_update(update: dict) -> dict:
    external_status = str(update.get("status", "")).strip().upper()
    order_id = _pick_str(update, ("order_id", "id", "client_order_id"))
    if not order_id:
        return {"ok": False, "reason": "missing_order_id", "event": None}

    mapped = EXTERNAL_STATUS_MAP.get(external_status)
    if mapped is None:
        event = {
            "order_id": order_id,
            "trade_id": update.get("trade_id"),
            "symbol": _pick_str(update, ("symbol",), ""),
            "side": _pick_str(update, ("side",), ""),
            "status": ORDER_STATUS_REJECTED,
            "event_type": ORDER_EVENT_REJECTED,
            "filled_qty": _to_float(update.get("filled_qty", 0.0)),
            "remaining_qty": _to_float(update.get("remaining_qty", 0.0)),
            "avg_fill_price": _to_float(update.get("avg_fill_price", update.get("avg_price", 0.0))),
            "reason": f"unknown_external_status:{external_status or 'EMPTY'}",
            "timestamp": _normalize_timestamp(update.get("timestamp")),
        }
        return {"ok": False, "reason": "unknown_external_status", "event": event}

    event_type, status = mapped
    total_qty = _to_float(update.get("total_qty", update.get("qty", update.get("quantity", 0.0))))
    filled_qty = _to_float(update.get("filled_qty", update.get("executed_qty", 0.0)))
    if update.get("remaining_qty", None) in ("", None):
        remaining_qty = max(total_qty - filled_qty, 0.0)
    else:
        remaining_qty = _to_float(update.get("remaining_qty", 0.0))

    event = {
        "order_id": order_id,
        "trade_id": update.get("trade_id"),
        "symbol": _pick_str(update, ("symbol",), ""),
        "side": _pick_str(update, ("side",), ""),
        "status": status,
        "event_type": event_type,
        "filled_qty": filled_qty,
        "remaining_qty": remaining_qty,
        "avg_fill_price": _to_float(update.get("avg_fill_price", update.get("avg_price", 0.0))),
        "reason": _pick_str(update, ("reason", "reject_reason"), ""),
        "timestamp": _normalize_timestamp(update.get("timestamp")),
    }
    return {"ok": True, "reason": "", "event": event}


def map_external_order_event(update: dict) -> dict:
    return adapt_broker_order_update(update)


def _to_float(value: Any, default: float = 0.0) -> float:
    if value in ("", None):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _pick_str(update: dict, keys: tuple[str, ...], default: str = "") -> str:
    for key in keys:
        value = update.get(key)
        if value in ("", None):
            continue
        return str(value)
    return default


def _normalize_timestamp(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    if value not in ("", None):
        return str(value)
    return datetime.now(timezone.utc).isoformat()
