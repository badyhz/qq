from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def normalize_symbol_state(row: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(row, dict):
        return None
    symbol = str(row.get("symbol", "")).strip().upper()
    if not symbol:
        return None

    normalized = {
        "symbol": symbol,
        "positionAmt": _to_float(row.get("positionAmt", row.get("position_amt", 0.0)), 0.0),
        "openAlgoOrdersCount": _to_int(row.get("openAlgoOrdersCount", row.get("open_algo_orders_count", 0)), 0),
        "open_stop_market_count": _to_int(row.get("open_stop_market_count", 0), 0),
        "open_take_profit_market_count": _to_int(row.get("open_take_profit_market_count", 0), 0),
        "protection_status": str(row.get("protection_status", "")).strip().upper() or "UNKNOWN",
        "ok": bool(row.get("ok", False)),
    }
    return normalized


def classify_protection_state(row: dict[str, Any]) -> str:
    status = str(row.get("protection_status", "")).strip().upper()
    position_amt = abs(_to_float(row.get("positionAmt", 0.0), 0.0))
    open_count = _to_int(row.get("openAlgoOrdersCount", 0), 0)

    if status in {"FULLY_PROTECTED", "ORPHAN_PROTECTION", "NAKED_POSITION", "PARTIAL_PROTECTED", "FLAT_CLEAN"}:
        return status
    if position_amt <= 0 and open_count > 0:
        return "ORPHAN_PROTECTION"
    if position_amt > 0 and open_count <= 0:
        return "NAKED_POSITION"
    if position_amt <= 0 and open_count <= 0:
        return "FLAT_CLEAN"
    return "UNKNOWN"


def summarize_state_snapshot(rows: list[dict[str, Any]]) -> dict[str, Any]:
    normalized_rows: list[dict[str, Any]] = []
    counts = {
        "FULLY_PROTECTED": 0,
        "ORPHAN_PROTECTION": 0,
        "NAKED_POSITION": 0,
        "PARTIAL_PROTECTED": 0,
        "FLAT_CLEAN": 0,
        "UNKNOWN": 0,
    }

    for row in rows:
        item = normalize_symbol_state(row)
        if item is None:
            continue
        state = classify_protection_state(item)
        counts[state] = counts.get(state, 0) + 1
        item["classified_state"] = state
        normalized_rows.append(item)

    total = len(normalized_rows)
    ok_count = sum(1 for item in normalized_rows if bool(item.get("ok", False)))

    return {
        "total": total,
        "ok_count": ok_count,
        "error_count": total - ok_count,
        "counts": counts,
        "rows": normalized_rows,
    }


def read_state_snapshot_jsonl(path: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    p = Path(path)
    if not p.exists():
        return rows
    with p.open("r", encoding="utf-8") as fh:
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
