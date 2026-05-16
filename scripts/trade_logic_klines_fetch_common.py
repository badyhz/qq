from __future__ import annotations

from typing import Any, Iterable

BINANCE_KLINES_URL = "https://fapi.binance.com/fapi/v1/klines"


def normalize_symbol(symbol: str) -> str:
    return str(symbol or "").strip().upper()


def normalize_interval(interval: str, allowed_intervals: Iterable[str] | None = None) -> str:
    value = str(interval or "").strip().lower()
    if not value:
        raise ValueError("interval is empty")
    if allowed_intervals is not None:
        allowed = {str(item).strip().lower() for item in allowed_intervals}
        if value not in allowed:
            raise ValueError(f"unsupported interval: {interval}")
    return value


def build_kline_request_params(
    *, symbol: str, interval: str, start_ms: int, end_ms: int, limit: int = 1500
) -> dict[str, Any]:
    return {
        "symbol": normalize_symbol(symbol),
        "interval": str(interval),
        "startTime": int(start_ms),
        "endTime": int(end_ms),
        "limit": int(limit),
    }


def normalize_kline_rows(payload: Any) -> list[list[Any]]:
    if not isinstance(payload, list):
        return []
    rows: list[list[Any]] = []
    for item in payload:
        if not isinstance(item, list) or len(item) < 6:
            continue
        try:
            open_time_ms = int(item[0])
        except (TypeError, ValueError):
            continue
        row = list(item)
        row[0] = open_time_ms
        rows.append(row)
    return rows
