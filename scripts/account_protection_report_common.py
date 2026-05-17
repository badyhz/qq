from __future__ import annotations

from typing import Any


def summarize_account_risk_state(rows_or_reports: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [row for row in list(rows_or_reports or []) if isinstance(row, dict)]
    blocked = [row for row in rows if not bool(row.get("allowed", True))]
    total_notional = sum(float(row.get("total_notional", 0.0) or 0.0) for row in rows)
    max_open_positions = max([int(row.get("current_open_positions", 0) or 0) for row in rows] or [0])
    return {
        "rows": len(rows),
        "blocked_count": len(blocked),
        "allowed_count": len(rows) - len(blocked),
        "max_open_positions": max_open_positions,
        "total_notional": round(total_notional, 8),
        "has_duplicate_candidate_ids": any(int(row.get("duplicate_candidate_id_count", 0) or 0) > 0 for row in rows),
        "has_pending_or_approved": any(int(row.get("pending_or_approved_count", 0) or 0) > 0 for row in rows),
        "block_reasons": sorted({str(row.get("reason", "")).strip() for row in blocked if str(row.get("reason", "")).strip()}),
    }


def classify_account_risk_guard(summary: dict[str, Any]) -> dict[str, str]:
    if int(summary.get("blocked_count", 0) or 0) > 0:
        return {"guard_status": "BLOCKED", "guard_reason": "account_risk_guard_rejected"}
    if bool(summary.get("has_duplicate_candidate_ids", False)):
        return {"guard_status": "PARTIAL", "guard_reason": "duplicate_candidate_ids_present"}
    if bool(summary.get("has_pending_or_approved", False)):
        return {"guard_status": "PARTIAL", "guard_reason": "pending_or_approved_candidates_present"}
    return {"guard_status": "PASS", "guard_reason": "account_risk_guard_clear"}


def summarize_protection_health(rows_or_reports: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [row for row in list(rows_or_reports or []) if isinstance(row, dict)]
    counts: dict[str, int] = {}
    for row in rows:
        status = str(row.get("protection_health", "UNKNOWN")).strip().upper() or "UNKNOWN"
        counts[status] = counts.get(status, 0) + 1
    return {
        "rows": len(rows),
        "status_counts": counts,
        "critical_count": counts.get("INVALID_TRIGGER_DIRECTION", 0),
        "failed_count": counts.get("MISSING_STOP_LOSS", 0)
        + counts.get("MISSING_TAKE_PROFIT", 0)
        + counts.get("PARTIAL_PROTECTION", 0),
        "warning_count": counts.get("ORPHAN_PROTECTION", 0) + counts.get("UNKNOWN", 0),
        "healthy_count": counts.get("HEALTHY", 0) + counts.get("NO_POSITION", 0),
    }


def classify_protection_health(summary: dict[str, Any]) -> dict[str, str]:
    if int(summary.get("critical_count", 0) or 0) > 0:
        return {"aggregate_health": "FAIL", "aggregate_reason": "critical_trigger_or_direction_issue"}
    if int(summary.get("failed_count", 0) or 0) > 0:
        return {"aggregate_health": "FAIL", "aggregate_reason": "missing_or_insufficient_protection_detected"}
    if int(summary.get("warning_count", 0) or 0) > 0:
        return {"aggregate_health": "PARTIAL", "aggregate_reason": "orphan_or_unknown_detected"}
    return {"aggregate_health": "PASS", "aggregate_reason": "all_positions_healthy_or_flat"}


def render_account_protection_markdown(summary: dict[str, Any]) -> str:
    account = dict(summary.get("account_risk", {}))
    protection = dict(summary.get("protection_health", {}))
    lines = [
        "# Account Protection Summary",
        "",
        "## Account Risk Guard",
        f"- guard_status: {account.get('guard_status', '')}",
        f"- guard_reason: {account.get('guard_reason', '')}",
        f"- blocked_count: {account.get('blocked_count', 0)}",
        f"- max_open_positions: {account.get('max_open_positions', 0)}",
        f"- total_notional: {account.get('total_notional', 0)}",
        "",
        "## Protection Health",
        f"- aggregate_health: {protection.get('aggregate_health', '')}",
        f"- aggregate_reason: {protection.get('aggregate_reason', '')}",
        f"- critical_count: {protection.get('critical_count', 0)}",
        f"- failed_count: {protection.get('failed_count', 0)}",
        f"- warning_count: {protection.get('warning_count', 0)}",
    ]
    return "\n".join(lines) + "\n"
