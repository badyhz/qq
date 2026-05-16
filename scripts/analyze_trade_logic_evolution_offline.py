from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import json
from typing import Any, Iterable


@dataclass(frozen=True)
class TradeFeature:
    symbol: str
    direction: str
    entry_price: float
    exit_price: float
    quantity: float
    return_pct: float
    pnl: float


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_direction(value: Any) -> str:
    text = str(value or "").strip().upper()
    if text in {"BUY", "LONG"}:
        return "LONG"
    if text in {"SELL", "SHORT"}:
        return "SHORT"
    return "UNKNOWN"


def _calc_return_pct(direction: str, entry_price: float, exit_price: float) -> float:
    if entry_price <= 0:
        return 0.0
    if direction == "SHORT":
        return (entry_price - exit_price) / entry_price * 100.0
    return (exit_price - entry_price) / entry_price * 100.0


def normalize_trade_row(row: dict[str, Any]) -> TradeFeature | None:
    symbol = str(row.get("symbol", "")).strip().upper()
    direction = _normalize_direction(row.get("side", row.get("direction", "")))
    entry_price = _to_float(row.get("entry_price", row.get("entry", 0.0)))
    exit_price = _to_float(row.get("exit_price", row.get("exit", 0.0)))
    quantity = _to_float(row.get("quantity", row.get("qty", 0.0)))

    if not symbol or direction == "UNKNOWN" or entry_price <= 0 or exit_price <= 0 or quantity <= 0:
        return None

    return_pct = _calc_return_pct(direction, entry_price, exit_price)
    pnl = (exit_price - entry_price) * quantity
    if direction == "SHORT":
        pnl = -pnl

    return TradeFeature(
        symbol=symbol,
        direction=direction,
        entry_price=entry_price,
        exit_price=exit_price,
        quantity=quantity,
        return_pct=return_pct,
        pnl=pnl,
    )


def build_trade_features(rows: Iterable[dict[str, Any]]) -> list[TradeFeature]:
    output: list[TradeFeature] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        item = normalize_trade_row(row)
        if item is not None:
            output.append(item)
    return output


def summarize_trade_features(features: Iterable[TradeFeature]) -> dict[str, Any]:
    items = list(features)
    total = len(items)
    if total == 0:
        return {
            "total_trades": 0,
            "win_rate": 0.0,
            "avg_return_pct": 0.0,
            "avg_pnl": 0.0,
            "long_count": 0,
            "short_count": 0,
        }

    win_count = sum(1 for item in items if item.pnl > 0)
    avg_return_pct = sum(item.return_pct for item in items) / total
    avg_pnl = sum(item.pnl for item in items) / total
    long_count = sum(1 for item in items if item.direction == "LONG")
    short_count = sum(1 for item in items if item.direction == "SHORT")

    return {
        "total_trades": total,
        "win_rate": round(win_count / total, 6),
        "avg_return_pct": round(avg_return_pct, 6),
        "avg_pnl": round(avg_pnl, 6),
        "long_count": long_count,
        "short_count": short_count,
    }


def read_trade_rows_jsonl(path: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    file_path = Path(path)
    if not file_path.exists():
        return rows
    with file_path.open("r", encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict):
                rows.append(item)
    return rows


def iso_utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
