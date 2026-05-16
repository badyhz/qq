from __future__ import annotations

from itertools import product
from typing import Any, Iterable


def parse_symbols(text: str) -> list[str]:
    items = [str(item).strip().upper() for item in str(text or "").split(",")]
    return [item for item in items if item]


def parse_timeframes(text: str) -> list[str]:
    allowed = {"1m", "5m", "15m", "1h", "4h", "1d"}
    result: list[str] = []
    for item in [str(v).strip() for v in str(text or "").split(",")]:
        if item and item in allowed:
            result.append(item)
    return result


def build_scan_grid(
    symbols: Iterable[str],
    timeframes: Iterable[str],
    min_scores: Iterable[float],
    lookbacks: Iterable[int],
) -> list[dict[str, Any]]:
    grid: list[dict[str, Any]] = []
    for symbol, timeframe, min_score, lookback in product(symbols, timeframes, min_scores, lookbacks):
        grid.append(
            {
                "symbol": str(symbol).strip().upper(),
                "timeframe": str(timeframe).strip(),
                "min_score": float(min_score),
                "lookback": int(lookback),
            }
        )
    return grid


def build_param_grid(params: dict[str, Iterable[Any]]) -> list[dict[str, Any]]:
    keys = [key for key, values in params.items() if list(values)]
    if not keys:
        return []
    value_lists = [list(params[key]) for key in keys]
    output: list[dict[str, Any]] = []
    for combo in product(*value_lists):
        output.append({key: value for key, value in zip(keys, combo)})
    return output


def summarize_scan_results(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows_list = [row for row in rows if isinstance(row, dict)]
    total = len(rows_list)
    accepted = sum(1 for row in rows_list if bool(row.get("accepted", False)))
    symbols = sorted({str(row.get("symbol", "")).strip().upper() for row in rows_list if str(row.get("symbol", "")).strip()})
    avg_score = 0.0
    scored = [float(row.get("score", 0.0)) for row in rows_list if row.get("score") is not None]
    if scored:
        avg_score = sum(scored) / len(scored)
    return {
        "total": total,
        "accepted": accepted,
        "rejected": total - accepted,
        "symbols": symbols,
        "avg_score": round(avg_score, 6),
    }
