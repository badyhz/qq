from __future__ import annotations

from typing import Any


_RISK_STATUSES = {"ORPHAN_PROTECTION", "PARTIAL_PROTECTED", "NAKED_POSITION"}
_CLEAN_STATUS = "FLAT_CLEAN"
_FULLY_PROTECTED_STATUS = "FULLY_PROTECTED"


def _norm_symbol(value: Any) -> str:
    return str(value or "").strip().upper()


def _norm_status(value: Any) -> str:
    text = str(value or "").strip().upper()
    return text or "UNKNOWN"


def _norm_bool(value: Any) -> bool:
    return bool(value)


def summarize_snapshot_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    per_symbol_state: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        item = dict(row)
        item["symbol"] = _norm_symbol(item.get("symbol", ""))
        item["protection_status"] = _norm_status(item.get("protection_status", ""))
        item["ok"] = _norm_bool(item.get("ok", False))
        per_symbol_state.append(item)

    statuses = {
        row.get("protection_status", "UNKNOWN")
        for row in per_symbol_state
        if bool(row.get("ok", False))
    }
    has_failed = any(not bool(row.get("ok", False)) for row in per_symbol_state)

    if has_failed:
        aggregate_status = "UNKNOWN"
    elif "NAKED_POSITION" in statuses:
        aggregate_status = "CRITICAL"
    elif {"ORPHAN_PROTECTION", "PARTIAL_PROTECTED"} & statuses:
        aggregate_status = "WARNING"
    elif statuses and statuses <= {"FLAT_CLEAN", "FULLY_PROTECTED"}:
        aggregate_status = "CLEAN"
    else:
        aggregate_status = "UNKNOWN"

    status_counts = {
        "FULLY_PROTECTED": 0,
        "ORPHAN_PROTECTION": 0,
        "PARTIAL_PROTECTED": 0,
        "NAKED_POSITION": 0,
        "FLAT_CLEAN": 0,
        "UNKNOWN": 0,
    }
    for row in per_symbol_state:
        status = _norm_status(row.get("protection_status", "UNKNOWN"))
        if status not in status_counts:
            status = "UNKNOWN"
        status_counts[status] += 1

    risky_symbols = [
        str(row.get("symbol", ""))
        for row in per_symbol_state
        if str(row.get("protection_status", "")).strip().upper() in _RISK_STATUSES
    ]
    clean_symbols = [
        str(row.get("symbol", ""))
        for row in per_symbol_state
        if str(row.get("protection_status", "")).strip().upper() == _CLEAN_STATUS
    ]
    fully_protected_symbols = [
        str(row.get("symbol", ""))
        for row in per_symbol_state
        if str(row.get("protection_status", "")).strip().upper() == _FULLY_PROTECTED_STATUS
    ]

    return {
        "ok": not has_failed,
        "aggregate_status": aggregate_status,
        "status_counts": status_counts,
        "risky_symbols": risky_symbols,
        "clean_symbols": clean_symbols,
        "fully_protected_symbols": fully_protected_symbols,
        "per_symbol_state": per_symbol_state,
    }


def render_snapshot_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Testnet State Snapshot",
        "",
        "## Summary",
        f"- snapshot_id: {summary.get('snapshot_id', '')}",
        f"- env: {summary.get('env', '')}",
        f"- ts_utc: {summary.get('ts_utc', '')}",
        f"- aggregate_status: {summary.get('aggregate_status', '')}",
        f"- symbols: {','.join(list(summary.get('symbols', [])))}",
        "",
        "## Per Symbol State",
        "| symbol | positionAmt | entryPrice | markPrice | openAlgoOrdersCount | open_stop_market_count | open_take_profit_market_count | protection_status | action_required | ok |",
        "|---|---:|---:|---:|---:|---:|---:|---|---|---|",
    ]
    for row in list(summary.get("per_symbol_state", [])):
        lines.append(
            "| {symbol} | {positionAmt} | {entryPrice} | {markPrice} | {openAlgoOrdersCount} | {open_stop_market_count} | {open_take_profit_market_count} | {protection_status} | {action_required} | {ok} |".format(
                symbol=row.get("symbol", ""),
                positionAmt=row.get("positionAmt", 0),
                entryPrice=row.get("entryPrice", 0),
                markPrice=row.get("markPrice", 0),
                openAlgoOrdersCount=row.get("openAlgoOrdersCount", 0),
                open_stop_market_count=row.get("open_stop_market_count", 0),
                open_take_profit_market_count=row.get("open_take_profit_market_count", 0),
                protection_status=row.get("protection_status", ""),
                action_required=row.get("action_required", ""),
                ok=row.get("ok", False),
            )
        )

    counts = dict(summary.get("status_counts", {}))
    lines.extend(
        [
            "",
            "## Status Counts",
            f"- FULLY_PROTECTED: {counts.get('FULLY_PROTECTED', 0)}",
            f"- ORPHAN_PROTECTION: {counts.get('ORPHAN_PROTECTION', 0)}",
            f"- PARTIAL_PROTECTED: {counts.get('PARTIAL_PROTECTED', 0)}",
            f"- NAKED_POSITION: {counts.get('NAKED_POSITION', 0)}",
            f"- FLAT_CLEAN: {counts.get('FLAT_CLEAN', 0)}",
            f"- UNKNOWN: {counts.get('UNKNOWN', 0)}",
            "",
            f"- risky_symbols: {summary.get('risky_symbols', [])}",
            f"- clean_symbols: {summary.get('clean_symbols', [])}",
            f"- fully_protected_symbols: {summary.get('fully_protected_symbols', [])}",
        ]
    )
    return "\n".join(lines) + "\n"


def build_snapshot_archive_payload(rows: list[dict[str, Any]], metadata: dict[str, Any]) -> dict[str, Any]:
    summary = summarize_snapshot_rows(rows)
    payload = dict(metadata or {})
    payload.update(summary)
    payload["symbols"] = list(metadata.get("symbols", [])) if isinstance(metadata, dict) else []
    return payload
