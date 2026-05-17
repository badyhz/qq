from __future__ import annotations
from typing import Any
from pathlib import Path


def classify_protection_distance_state(row_or_report: dict[str, Any]) -> str:
    health = str(row_or_report.get("protection_health", "")).strip().upper()
    severity = str(row_or_report.get("severity", "")).strip().upper()
    alerts = row_or_report.get("alerts", [])
    if "near_stop" in alerts:
        return "NEAR_TRIGGER"
    if health in {"MISSING_STOP_LOSS", "MISSING_TAKE_PROFIT", "PARTIAL_PROTECTION"}:
        return "INVALID_PROTECTION"
    if health == "NO_POSITION":
        return "NO_POSITION"
    if severity == "CRITICAL":
        return "CRITICAL"
    if severity == "WARNING":
        return "WARNING"
    if health == "HEALTHY":
        return "HEALTHY"
    return "UNKNOWN"


def summarize_protection_distance(rows_or_reports: list[dict[str, Any]]) -> dict[str, Any]:
    per_symbol: list[dict[str, Any]] = []
    counts: dict[str, int] = {}
    for item in rows_or_reports:
        if "per_symbol" in item:
            per_symbol.extend(item["per_symbol"])
        else:
            per_symbol.append(item)
    for row in per_symbol:
        state = classify_protection_distance_state(row)
        counts[state] = counts.get(state, 0) + 1
    aggregate_status = "PASS"
    if counts.get("CRITICAL", 0) > 0:
        aggregate_status = "FAIL"
    elif counts.get("WARNING", 0) > 0 or counts.get("INVALID_PROTECTION", 0) > 0 or counts.get("NEAR_TRIGGER", 0) > 0:
        aggregate_status = "PARTIAL"
    return {
        "per_symbol": per_symbol,
        "counts": counts,
        "aggregate_status": aggregate_status,
    }


def classify_protection_trigger_outcome(row_or_report: dict[str, Any]) -> str:
    outcome = str(row_or_report.get("outcome", "")).strip().upper()
    verdict = str(row_or_report.get("verdict", "")).strip().upper()
    orphan_after_close = bool(row_or_report.get("orphan_after_close", False))
    if verdict == "FAIL":
        return "FAIL"
    if orphan_after_close:
        return "ORPHAN_AFTER_CLOSE"
    if outcome == "TAKE_PROFIT_TRIGGERED":
        return "TAKE_PROFIT_TRIGGERED"
    if outcome == "STOP_LOSS_TRIGGERED":
        return "STOP_LOSS_TRIGGERED"
    if outcome == "STILL_OPEN":
        return "STILL_OPEN"
    if outcome == "MANUAL_FLATTENED":
        return "MANUAL_FLATTENED"
    if outcome == "EXTERNAL_CLOSED":
        return "EXTERNAL_CLOSED"
    if outcome == "UNKNOWN":
        return "UNKNOWN"
    return "UNKNOWN"


def summarize_protection_trigger_outcomes(rows_or_reports: list[dict[str, Any]]) -> dict[str, Any]:
    per_symbol: list[dict[str, Any]] = []
    counts: dict[str, int] = {}
    for item in rows_or_reports:
        per_symbol.append(item)
    for row in per_symbol:
        state = classify_protection_trigger_outcome(row)
        counts[state] = counts.get(state, 0) + 1
    aggregate_status = "PASS"
    if counts.get("FAIL", 0) > 0:
        aggregate_status = "FAIL"
    elif counts.get("ORPHAN_AFTER_CLOSE", 0) > 0 or counts.get("UNKNOWN", 0) > 0:
        aggregate_status = "PARTIAL"
    return {
        "per_symbol": per_symbol,
        "counts": counts,
        "aggregate_status": aggregate_status,
    }


def render_protection_monitor_markdown(summary: dict[str, Any], *, title: str = "Protection Monitor Report") -> str:
    lines = [
        f"# {title}",
        "",
        f"- aggregate_status: {summary.get('aggregate_status', '')}",
        "",
    ]
    counts = summary.get("counts", {})
    if counts:
        lines.extend([
            "## Counts by State",
            "",
        ])
        for key, val in sorted(counts.items()):
            lines.append(f"- {key}: {val}")
        lines.append("")
    per_symbol = summary.get("per_symbol", [])
    if per_symbol and "protection_health" in per_symbol[0]:
        lines.extend([
            "## Per Symbol Distance",
            "",
            "| symbol | side | markPrice | SL | TP | dist_to_stop_pct | dist_to_tp_pct | health | severity |",
            "|---|---|---:|---:|---:|---:|---:|---:|---|---|",
        ])
        for row in per_symbol:
            lines.append(
                f"| {row.get('symbol', '')} | {row.get('side', '')} | {row.get('markPrice', 0)} | "
                f"{row.get('stop_loss_trigger_price', 0)} | {row.get('take_profit_trigger_price', 0)} | "
                f"{row.get('distance_to_stop_pct', 0)} | {row.get('distance_to_take_profit_pct', 0)} | "
                f"{row.get('protection_health', '')} | {row.get('severity', '')} |"
            )
        lines.append("")
    elif per_symbol and "outcome" in per_symbol[0]:
        lines.extend([
            "## Per Symbol Outcome",
            "",
            "| symbol | outcome | verdict | orphan_after_close |",
            "|---|---|---|---|",
        ])
        for row in per_symbol:
            lines.append(
                f"| {row.get('symbol', '')} | {row.get('outcome', '')} | {row.get('verdict', '')} | "
                f"{row.get('orphan_after_close', False)} |"
            )
        lines.append("")
    return "\n".join(lines) + "\n"
