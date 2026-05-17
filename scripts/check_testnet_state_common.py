from __future__ import annotations

from typing import Any


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def normalize_position_risk_row(row: dict[str, Any]) -> dict[str, Any]:
    current = dict(row or {})
    symbol = str(current.get("symbol", "")).strip().upper()
    position_amt = _to_float(current.get("positionAmt", current.get("position_amt", 0.0)), 0.0)
    entry_price = _to_float(current.get("entryPrice", current.get("entry_price", 0.0)), 0.0)
    mark_price = _to_float(current.get("markPrice", current.get("mark_price", 0.0)), 0.0)
    return {
        "symbol": symbol,
        "position_amt": position_amt,
        "entry_price": entry_price,
        "mark_price": mark_price,
    }


def _normalize_order_type(row: dict[str, Any]) -> str:
    text = str(row.get("type", row.get("origType", row.get("algoType", ""))) or "").strip().upper()
    if text in {"STOP_MARKET", "STOP"}:
        return "STOP_MARKET"
    if text in {"TAKE_PROFIT_MARKET", "TAKE_PROFIT"}:
        return "TAKE_PROFIT_MARKET"
    return text


def normalize_open_algo_orders(rows: list[dict[str, Any]]) -> dict[str, Any]:
    stop_rows = 0
    tp_rows = 0
    for row in list(rows or []):
        if not isinstance(row, dict):
            continue
        order_type = _normalize_order_type(row)
        if order_type == "STOP_MARKET":
            stop_rows += 1
        elif order_type == "TAKE_PROFIT_MARKET":
            tp_rows += 1
    return {
        "open_stop_market_count": int(stop_rows),
        "open_take_profit_market_count": int(tp_rows),
        "open_algo_orders_count": int(stop_rows + tp_rows),
    }


def classify_testnet_protection_status(position: dict[str, Any], algo_orders: dict[str, Any]) -> dict[str, str]:
    position_amt = _to_float(position.get("position_amt", 0.0), 0.0)
    abs_position = abs(position_amt)
    stop_count = int(algo_orders.get("open_stop_market_count", 0) or 0)
    tp_count = int(algo_orders.get("open_take_profit_market_count", 0) or 0)
    open_count = int(algo_orders.get("open_algo_orders_count", 0) or 0)

    if abs_position <= 0 and open_count <= 0:
        return {"protection_status": "FLAT_CLEAN", "action_required": "none"}
    if abs_position <= 0 and open_count > 0:
        return {"protection_status": "ORPHAN_PROTECTION", "action_required": "review_orphan_and_clean_if_confirmed"}

    has_sl = stop_count > 0
    has_tp = tp_count > 0
    if has_sl and has_tp:
        return {"protection_status": "FULLY_PROTECTED", "action_required": "none"}
    if (not has_sl) and (not has_tp):
        return {"protection_status": "NAKED_POSITION", "action_required": "stop_new_orders_and_protect_or_flatten"}
    return {"protection_status": "PARTIAL_PROTECTED", "action_required": "repair_missing_protection_immediately"}


def build_testnet_state_result(
    symbol: str,
    position: dict[str, Any],
    algo_orders: dict[str, Any],
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    meta = dict(metadata or {})
    symbol_u = str(symbol or "").strip().upper()
    position_amt = _to_float(position.get("position_amt", 0.0), 0.0)
    entry_price = _to_float(position.get("entry_price", 0.0), 0.0)
    mark_price = _to_float(position.get("mark_price", 0.0), 0.0)
    normalized_algo = normalize_open_algo_orders([])
    normalized_algo.update({
        "open_stop_market_count": int(algo_orders.get("open_stop_market_count", 0) or 0),
        "open_take_profit_market_count": int(algo_orders.get("open_take_profit_market_count", 0) or 0),
        "open_algo_orders_count": int(algo_orders.get("open_algo_orders_count", 0) or 0),
    })
    status = classify_testnet_protection_status(position, normalized_algo)
    result = {
        "ok": True,
        "symbol": symbol_u,
        "positionAmt": position_amt,
        "entryPrice": entry_price,
        "markPrice": mark_price,
        "openAlgoOrdersCount": int(normalized_algo.get("open_algo_orders_count", 0)),
        "open_stop_market_count": int(normalized_algo.get("open_stop_market_count", 0)),
        "open_take_profit_market_count": int(normalized_algo.get("open_take_profit_market_count", 0)),
        "protection_status": str(status.get("protection_status", "UNKNOWN")),
        "action_required": str(status.get("action_required", "")),
    }
    result.update(meta)
    return result
