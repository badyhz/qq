from __future__ import annotations

from typing import Any


def _to_int(value: Any, fallback: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(fallback)


def normalize_kline_backfill_config(
    *,
    max_symbols: int,
    max_bars: int,
    market: str,
    dry_run: bool,
    write_cache: bool,
    public_only: bool,
    min_written_bars: int,
    fail_if_empty: bool,
) -> dict[str, Any]:
    return {
        "max_symbols": max(1, _to_int(max_symbols, 5)),
        "max_bars": max(1, _to_int(max_bars, 1500)),
        "market": str(market or "futures").strip().lower() or "futures",
        "dry_run": bool(dry_run),
        "write_cache": bool(write_cache),
        "public_only": bool(public_only),
        "min_written_bars": max(0, _to_int(min_written_bars, 100)),
        "fail_if_empty": bool(fail_if_empty),
    }


def build_kline_request_windows(
    *,
    plan_rows: list[dict[str, Any]],
    max_symbols: int,
    max_bars: int,
) -> list[dict[str, Any]]:
    picked = [
        row
        for row in list(plan_rows or [])
        if str(row.get("cache_status", "")).strip().upper() in {"MISSING", "PARTIAL", "STALE", "UNKNOWN"}
    ]
    picked = picked[: max(1, int(max_symbols))]
    windows: list[dict[str, Any]] = []
    for row in picked:
        symbol = str(row.get("symbol", "")).strip().upper()
        timeframe = str(row.get("timeframe", "5m")).strip() or "5m"
        requested_raw = row.get("required_bars")
        requested = _to_int(requested_raw, 300) if str(requested_raw or "").strip() else 300
        requested = max(1, min(int(max_bars), int(requested)))
        windows.append(
            {
                "symbol": symbol,
                "timeframe": timeframe,
                "requested_bars": requested,
            }
        )
    return windows


def summarize_backfill_plan(
    *,
    plan_rows_total: int,
    windows: list[dict[str, Any]],
) -> dict[str, Any]:
    symbols = sorted({str(row.get("symbol", "")).strip().upper() for row in windows if str(row.get("symbol", "")).strip()})
    bars_total = sum(int(row.get("requested_bars", 0) or 0) for row in windows)
    return {
        "plan_rows_total": int(plan_rows_total),
        "selected_rows": len(windows),
        "symbols_count": len(symbols),
        "requested_bars_total": bars_total,
        "symbols": symbols,
    }


def render_backfill_plan_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Public Kline Backfill Plan",
        "",
        "## Summary",
        f"- plan_rows_total: {summary.get('plan_rows_total', 0)}",
        f"- selected_rows: {summary.get('selected_rows', 0)}",
        f"- symbols_count: {summary.get('symbols_count', 0)}",
        f"- requested_bars_total: {summary.get('requested_bars_total', 0)}",
        "",
        "## Symbols",
    ]
    symbols = list(summary.get("symbols", []))
    if symbols:
        for symbol in symbols:
            lines.append(f"- {symbol}")
    else:
        lines.append("- none")
    return "\n".join(lines) + "\n"
