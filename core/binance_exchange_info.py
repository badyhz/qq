from __future__ import annotations

from typing import Any, Optional


def parse_binance_exchange_info(
    payload: Any,
    *,
    symbols: Optional[list[str]] = None,
) -> dict[str, Any]:
    requested_symbols = {
        str(symbol or "").strip().upper()
        for symbol in list(symbols or [])
        if str(symbol or "").strip()
    }
    warnings: list[str] = []
    rules: dict[str, dict[str, Any]] = {}

    rows: list[dict[str, Any]] = []
    if isinstance(payload, dict):
        raw_symbols = payload.get("symbols", [])
        if isinstance(raw_symbols, list):
            rows = [row for row in raw_symbols if isinstance(row, dict)]
        else:
            warnings.append("exchange_info_symbols_not_list")
    elif isinstance(payload, list):
        rows = [row for row in payload if isinstance(row, dict)]
    else:
        warnings.append("exchange_info_invalid_payload")

    for row in rows:
        symbol = str(row.get("symbol", "")).strip().upper()
        if symbol == "":
            continue
        if requested_symbols and symbol not in requested_symbols:
            continue
        parsed, symbol_warnings = _parse_symbol_filters(row)
        if symbol_warnings:
            warnings.extend([f"{symbol}:{item}" for item in symbol_warnings])
        rules[symbol] = parsed

    missing_symbols = sorted(requested_symbols - set(rules.keys()))
    if missing_symbols:
        warnings.append("symbols_not_found_in_exchange_info")

    return {
        "success": True,
        "rules": rules,
        "warnings": list(dict.fromkeys(warnings)),
        "missing_symbols": missing_symbols,
        "found_symbols": sorted(rules.keys()),
    }


def _parse_symbol_filters(row: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []
    parsed = {
        "tick_size": 0.0,
        "step_size": 0.0,
        "min_qty": 0.0,
        "min_notional": 0.0,
        "price_precision": _to_int(row.get("pricePrecision"), default=-1),
        "qty_precision": _to_int(row.get("quantityPrecision", row.get("qtyPrecision")), default=-1),
    }

    filters = row.get("filters", [])
    if not isinstance(filters, list):
        return parsed, ["filters_missing_or_invalid"]

    for item in filters:
        if not isinstance(item, dict):
            continue
        filter_type = str(item.get("filterType", "")).strip().upper()
        if filter_type == "PRICE_FILTER":
            parsed["tick_size"] = _to_float(item.get("tickSize", parsed["tick_size"]))
        elif filter_type == "LOT_SIZE":
            parsed["step_size"] = _to_float(item.get("stepSize", parsed["step_size"]))
            parsed["min_qty"] = _to_float(item.get("minQty", parsed["min_qty"]))
        elif filter_type in {"MIN_NOTIONAL", "NOTIONAL"}:
            parsed["min_notional"] = _to_float(item.get("minNotional", parsed["min_notional"]))

    if parsed["tick_size"] <= 0:
        warnings.append("tick_size_missing")
    if parsed["step_size"] <= 0:
        warnings.append("step_size_missing")
    if parsed["min_qty"] <= 0:
        warnings.append("min_qty_missing")
    if parsed["min_notional"] <= 0:
        warnings.append("min_notional_missing")

    return parsed, warnings


def _to_float(value: Any, default: float = 0.0) -> float:
    if value in (None, ""):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_int(value: Any, default: int = 0) -> int:
    if value in (None, ""):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
