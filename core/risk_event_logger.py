from __future__ import annotations

import json
import sys
import uuid
from collections.abc import Mapping as MappingABC
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

DEFAULT_RISK_EVENTS_PATH = "logs/risk_events.jsonl"
PREFLIGHT_RISK_STATES = {"FULLY_PROTECTED", "ORPHAN_PROTECTION", "PARTIAL_PROTECTED", "NAKED_POSITION"}

_EVENT_SEVERITY_DEFAULTS: dict[str, str] = {
    "API_AUTH_FAILED": "ERROR",
    "MISSING_API_KEY": "ERROR",
    "SUBMIT_FAILED": "ERROR",
    "PROTECTIVE_ORDER_FAILED": "ERROR",
    "PROTECTIVE_ORDER_PARTIAL": "ERROR",
    "NAKED_POSITION_DETECTED": "CRITICAL",
    "ORPHAN_PROTECTION_DETECTED": "WARNING",
    "DUPLICATE_ENTRY_SKIPPED": "WARNING",
    "FULLY_PROTECTED_POSITION_SKIPPED": "INFO",
    "LIVE_SUBMIT_BLOCKED": "CRITICAL",
    "UNSAFE_CONFIRM_REQUIRED": "WARNING",
    "FLATTEN_DRY_RUN_ONLY": "INFO",
    "FLATTEN_CANCEL_ATTEMPTED": "INFO",
    "FLATTEN_CLOSE_ATTEMPTED": "INFO",
    "BATCH_SYMBOL_FAILED": "ERROR",
    "EXCHANGE_CONSTRAINT_ERROR": "ERROR",
    "ORDER_WOULD_IMMEDIATELY_TRIGGER": "ERROR",
    "CLIENT_ORDER_ID_TOO_LONG": "ERROR",
    "CANDIDATE_APPROVED": "INFO",
    "CANDIDATE_REJECTED": "INFO",
    "CANDIDATE_EXPIRED": "INFO",
    "CANDIDATE_SUBMITTED": "INFO",
    "CANDIDATE_SUBMIT_FAILED": "ERROR",
    "CANDIDATE_SKIPPED_BY_PREFLIGHT": "WARNING",
    "SCHEDULER_RUN_FAILED": "ERROR",
    "SCHEDULER_PREFLIGHT_UNAVAILABLE": "WARNING",
    "APPROVED_CANDIDATE_SKIPPED": "WARNING",
    "NOTIFICATION_DRY_RUN": "INFO",
    "NOTIFICATION_SEND_FAILED": "ERROR",
}


def _context_preflight_status(context: Mapping[str, Any]) -> str:
    for key in ("preflight_status", "protection_status", "state"):
        value = str(context.get(key, "")).strip().upper()
        if value:
            return value
    return ""


def is_expected_safety_rejection(event: Mapping[str, Any]) -> bool:
    event_type = str(event.get("event_type", "")).strip().upper()
    message = str(event.get("message", "")).strip().lower()
    context = dict(event.get("context", {})) if isinstance(event.get("context", {}), MappingABC) else {}

    if event_type == "BATCH_SYMBOL_FAILED" and "symbol rejected by allowlist" in message:
        return True
    if event_type == "BATCH_SYMBOL_FAILED" and "batch skipped symbol due to risky preflight state" in message:
        preflight_status = str(context.get("preflight_status", "")).strip().lower()
        state = dict(context.get("state", {})) if isinstance(context.get("state", {}), MappingABC) else {}
        if preflight_status == "preflight_unavailable" and str(state.get("error_code", "")).strip().lower() == "missing_testnet_api_key":
            return True
    if event_type == "LIVE_SUBMIT_BLOCKED" and bool(event.get("is_expected_block", False)):
        return True
    if event_type in {"UNSAFE_CONFIRM_REQUIRED", "FLATTEN_DRY_RUN_ONLY", "NOTIFICATION_DRY_RUN", "FULLY_PROTECTED_POSITION_SKIPPED"}:
        return True
    if event_type == "CANDIDATE_SKIPPED_BY_PREFLIGHT":
        preflight_status = _context_preflight_status(context)
        if preflight_status in PREFLIGHT_RISK_STATES:
            return True
    return False


def build_risk_event(
    *,
    env: str,
    symbol: str,
    component: str,
    event_type: str,
    message: str,
    severity: str = "",
    context: Mapping[str, Any] | None = None,
    action_required: str = "",
    source_log: str = "",
    correlation_id: str = "",
    batch_id: str = "",
    event_scope: str = "UNKNOWN",
    is_test_event: bool | None = None,
    is_expected_block: bool | None = None,
    run_id: str = "",
    candidate_id: str = "",
    shift_id: str = "",
    approved_run_id: str = "",
) -> dict[str, Any]:
    resolved_type = str(event_type or "").strip().upper() or "UNKNOWN"
    resolved_severity = str(severity or "").strip().upper()
    if not resolved_severity:
        resolved_severity = _EVENT_SEVERITY_DEFAULTS.get(resolved_type, "WARNING")

    resolved_scope = str(event_scope or "UNKNOWN").strip().upper() or "UNKNOWN"
    inferred_test_event = resolved_scope in {"TEST_FIXTURE", "LOCAL_DRY_RUN", "LIVE_BLOCK_TEST"}
    resolved_is_test_event = bool(inferred_test_event if is_test_event is None else is_test_event)
    resolved_is_expected_block = bool(
        (resolved_scope == "LIVE_BLOCK_TEST") if is_expected_block is None else is_expected_block
    )

    return {
        "event_id": str(uuid.uuid4()),
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "severity": resolved_severity,
        "env": str(env or "").strip().lower(),
        "symbol": str(symbol or "").strip().upper(),
        "component": str(component or "").strip(),
        "event_type": resolved_type,
        "message": str(message or "").strip(),
        "context": dict(context or {}),
        "action_required": str(action_required or "").strip(),
        "source_log": str(source_log or "").strip(),
        "correlation_id": str(correlation_id or "").strip(),
        "batch_id": str(batch_id or "").strip(),
        "event_scope": resolved_scope,
        "is_test_event": resolved_is_test_event,
        "is_expected_block": resolved_is_expected_block,
        "run_id": str(run_id or "").strip(),
        "candidate_id": str(candidate_id or "").strip(),
        "shift_id": str(shift_id or "").strip(),
        "approved_run_id": str(approved_run_id or "").strip(),
    }


def log_risk_event(
    *,
    env: str,
    symbol: str,
    component: str,
    event_type: str,
    message: str,
    severity: str = "",
    context: Mapping[str, Any] | None = None,
    action_required: str = "",
    source_log: str = "",
    correlation_id: str = "",
    batch_id: str = "",
    event_scope: str = "UNKNOWN",
    is_test_event: bool | None = None,
    is_expected_block: bool | None = None,
    run_id: str = "",
    candidate_id: str = "",
    shift_id: str = "",
    approved_run_id: str = "",
    output_path: str = DEFAULT_RISK_EVENTS_PATH,
) -> dict[str, Any]:
    event = build_risk_event(
        env=env,
        symbol=symbol,
        component=component,
        event_type=event_type,
        message=message,
        severity=severity,
        context=context,
        action_required=action_required,
        source_log=source_log,
        correlation_id=correlation_id,
        batch_id=batch_id,
        event_scope=event_scope,
        is_test_event=is_test_event,
        is_expected_block=is_expected_block,
        run_id=run_id,
        candidate_id=candidate_id,
        shift_id=shift_id,
        approved_run_id=approved_run_id,
    )
    try:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception as exc:  # pragma: no cover
        print(f"[risk_event_logger] failed_to_append_event:{exc}", file=sys.stderr)
    return event
