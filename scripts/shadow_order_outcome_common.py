from __future__ import annotations

from typing import Any


def classify_shadow_order_outcome(row: dict[str, Any]) -> str:
    status = str(row.get("outcome_status", "")).strip().lower()
    reason = str(row.get("order_level_exit_reason", row.get("exit_reason", ""))).strip().lower()
    if status in {"fetch_failed", "missing_required_field", "fetch_disabled"}:
        return "FAILED"
    if reason in {"tp", "take_profit", "take_profit_triggered"}:
        return "TAKE_PROFIT"
    if reason in {"sl", "stop_loss", "stop_loss_triggered"}:
        return "STOP_LOSS"
    if reason in {"open", "still_open"}:
        return "OPEN"
    if status in {"ok", "insufficient_future_bars"}:
        return "OPEN"
    return "UNKNOWN"


def summarize_shadow_order_outcomes(rows: list[dict[str, Any]]) -> dict[str, Any]:
    counts: dict[str, int] = {}
    for row in list(rows or []):
        cls = classify_shadow_order_outcome(row if isinstance(row, dict) else {})
        counts[cls] = counts.get(cls, 0) + 1
    total = sum(counts.values())
    return {
        "counts": counts,
        "total_rows": total,
        "failed_rows": counts.get("FAILED", 0),
        "tp_rows": counts.get("TAKE_PROFIT", 0),
        "sl_rows": counts.get("STOP_LOSS", 0),
        "open_rows": counts.get("OPEN", 0),
    }


def calculate_shadow_order_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    summary = summarize_shadow_order_outcomes(rows)
    total = max(1, int(summary.get("total_rows", 0)))
    tp = int(summary.get("tp_rows", 0))
    sl = int(summary.get("sl_rows", 0))
    failed = int(summary.get("failed_rows", 0))
    return {
        **summary,
        "win_rate": round(tp / total, 8),
        "loss_rate": round(sl / total, 8),
        "failure_rate": round(failed / total, 8),
    }


def render_shadow_order_outcome_markdown(summary: dict[str, Any]) -> str:
    counts = dict(summary.get("counts", {}))
    lines = [
        "# Shadow Order Outcome Summary",
        "",
        f"- total_rows: {summary.get('total_rows', 0)}",
        f"- failed_rows: {summary.get('failed_rows', 0)}",
        f"- tp_rows: {summary.get('tp_rows', 0)}",
        f"- sl_rows: {summary.get('sl_rows', 0)}",
        f"- open_rows: {summary.get('open_rows', 0)}",
        f"- win_rate: {summary.get('win_rate', 0.0)}",
        "",
        "## Counts",
    ]
    for key in sorted(counts.keys()):
        lines.append(f"- {key}: {counts[key]}")
    return "\n".join(lines) + "\n"
