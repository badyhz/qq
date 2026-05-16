from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.execution_candidate_queue import find_duplicate_candidate_ids


DEFAULT_ACCOUNT_RISK_CONFIG: dict[str, Any] = {
    "enabled": True,
    "max_open_positions": 1,
    "max_total_notional_usdt": 100.0,
    "max_symbol_notional_usdt": 60.0,
    "max_daily_submits": 3,
    "max_pending_or_approved_candidates": 3,
    "allow_add_to_existing_position": False,
    "block_if_any_orphan": True,
    "block_if_any_partial": True,
    "block_if_any_naked": True,
    "block_if_duplicate_candidate_ids": True,
}


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _to_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    return bool(default)


def _parse_dt(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


def _same_day_utc(value: Any, target_day: datetime) -> bool:
    dt = _parse_dt(value)
    if dt is None:
        return False
    return dt.strftime("%Y-%m-%d") == target_day.strftime("%Y-%m-%d")


def _state_notional_usdt(state: dict[str, Any]) -> float:
    position_amt = abs(_to_float(state.get("positionAmt", 0.0), 0.0))
    if position_amt <= 0:
        return 0.0
    mark = abs(_to_float(state.get("markPrice", 0.0), 0.0))
    if mark <= 0:
        mark = abs(_to_float(state.get("entryPrice", 0.0), 0.0))
    return position_amt * max(mark, 0.0)


def _load_yaml_or_json(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    try:
        payload = json.loads(text)
        return payload if isinstance(payload, dict) else {}
    except json.JSONDecodeError:
        pass
    try:
        import yaml  # type: ignore

        payload = yaml.safe_load(text)
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def load_account_risk_config(config_path: str = "") -> dict[str, Any]:
    merged = dict(DEFAULT_ACCOUNT_RISK_CONFIG)
    path_text = str(config_path or "").strip()
    if not path_text:
        return merged
    path = Path(path_text)
    if not path.exists():
        return merged
    payload = _load_yaml_or_json(path)
    source = payload.get("account_risk", payload) if isinstance(payload, dict) else {}
    if not isinstance(source, dict):
        return merged
    for key, default_val in DEFAULT_ACCOUNT_RISK_CONFIG.items():
        if key not in source:
            continue
        if isinstance(default_val, bool):
            merged[key] = _to_bool(source.get(key), bool(default_val))
        elif isinstance(default_val, int):
            merged[key] = _to_int(source.get(key), int(default_val))
        else:
            merged[key] = _to_float(source.get(key), float(default_val))
    return merged


def validate_account_risk_before_submit(
    *,
    env: str,
    target_symbol: str,
    target_notional_usdt: float,
    per_symbol_state: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    approved_run_summaries: list[dict[str, Any]],
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    resolved_env = str(env or "").strip().lower()
    target = str(target_symbol or "").strip().upper()
    resolved_cfg = dict(DEFAULT_ACCOUNT_RISK_CONFIG)
    if isinstance(config, dict):
        for key in DEFAULT_ACCOUNT_RISK_CONFIG:
            if key in config:
                resolved_cfg[key] = config[key]

    checks: dict[str, Any] = {}
    blocks: list[str] = []
    warnings: list[str] = []
    now = datetime.now(timezone.utc)

    if resolved_env != "testnet":
        blocks.append("env_not_testnet")

    status_map: dict[str, str] = {}
    state_notional_total = 0.0
    open_positions = 0
    orphan_count = 0
    partial_count = 0
    naked_count = 0
    state_unavailable_count = 0
    target_symbol_notional = float(target_notional_usdt or 0.0)
    for state in [item for item in per_symbol_state if isinstance(item, dict)]:
        symbol = str(state.get("symbol", "")).strip().upper()
        status = str(state.get("protection_status", "UNKNOWN")).strip().upper()
        status_map[symbol] = status
        if status == "UNKNOWN":
            state_unavailable_count += 1
        notional = _state_notional_usdt(state)
        state_notional_total += notional
        if symbol == target:
            target_symbol_notional += notional
        position_amt = abs(_to_float(state.get("positionAmt", 0.0), 0.0))
        if position_amt > 0 or status in {"FULLY_PROTECTED", "PARTIAL_PROTECTED", "NAKED_POSITION"}:
            open_positions += 1
        if status == "ORPHAN_PROTECTION":
            orphan_count += 1
        elif status == "PARTIAL_PROTECTED":
            partial_count += 1
        elif status == "NAKED_POSITION":
            naked_count += 1

    if naked_count > 0 and _to_bool(resolved_cfg.get("block_if_any_naked", True), True):
        blocks.append("naked_position_present")
    if partial_count > 0 and _to_bool(resolved_cfg.get("block_if_any_partial", True), True):
        blocks.append("partial_protected_present")
    if orphan_count > 0 and _to_bool(resolved_cfg.get("block_if_any_orphan", True), True):
        blocks.append("orphan_protection_present")
    if state_unavailable_count > 0:
        blocks.append("account_state_unavailable")

    max_open_positions = _to_int(resolved_cfg.get("max_open_positions", 1), 1)
    if open_positions >= max_open_positions:
        blocks.append("max_open_positions_reached")

    if (
        status_map.get(target, "") == "FULLY_PROTECTED"
        and not _to_bool(resolved_cfg.get("allow_add_to_existing_position", False), False)
    ):
        blocks.append("target_symbol_already_fully_protected")

    max_total_notional = _to_float(resolved_cfg.get("max_total_notional_usdt", 100.0), 100.0)
    projected_total_notional = state_notional_total + max(0.0, float(target_notional_usdt or 0.0))
    if projected_total_notional > max_total_notional:
        blocks.append("max_total_notional_exceeded")

    max_symbol_notional = _to_float(resolved_cfg.get("max_symbol_notional_usdt", 60.0), 60.0)
    if target_symbol_notional > max_symbol_notional:
        blocks.append("max_symbol_notional_exceeded")

    daily_submitted_count = 0
    for run in [item for item in approved_run_summaries if isinstance(item, dict)]:
        completed_at = run.get("completed_at_utc", "") or run.get("started_at_utc", "")
        if completed_at and not _same_day_utc(completed_at, now):
            continue
        daily_submitted_count += _to_int(run.get("submitted_count", 0), 0)
    if daily_submitted_count >= _to_int(resolved_cfg.get("max_daily_submits", 3), 3):
        blocks.append("max_daily_submits_reached")

    pending_or_approved = 0
    for row in [item for item in candidates if isinstance(item, dict)]:
        status = str(row.get("status", "")).strip().upper()
        if status in {"PENDING", "APPROVED"}:
            pending_or_approved += 1
    max_pending = _to_int(resolved_cfg.get("max_pending_or_approved_candidates", 3), 3)
    if pending_or_approved > max_pending:
        warnings.append("pending_or_approved_candidates_exceeded")
        blocks.append("pending_or_approved_candidates_exceeded")

    duplicate_count = len(find_duplicate_candidate_ids([row for row in candidates if isinstance(row, dict)]))
    if duplicate_count > 0 and _to_bool(resolved_cfg.get("block_if_duplicate_candidate_ids", True), True):
        blocks.append("duplicate_candidate_ids_present")

    checks["open_positions"] = open_positions
    checks["max_open_positions"] = max_open_positions
    checks["projected_total_notional_usdt"] = round(projected_total_notional, 8)
    checks["max_total_notional_usdt"] = max_total_notional
    checks["target_symbol_notional_usdt"] = round(target_symbol_notional, 8)
    checks["max_symbol_notional_usdt"] = max_symbol_notional
    checks["daily_submitted_count"] = daily_submitted_count
    checks["max_daily_submits"] = _to_int(resolved_cfg.get("max_daily_submits", 3), 3)
    checks["pending_or_approved_candidates"] = pending_or_approved
    checks["max_pending_or_approved_candidates"] = max_pending
    checks["duplicate_candidate_ids"] = duplicate_count
    checks["orphan_count"] = orphan_count
    checks["partial_count"] = partial_count
    checks["naked_count"] = naked_count
    checks["target_status"] = status_map.get(target, "UNKNOWN")
    checks["state_unavailable_count"] = state_unavailable_count

    allowed = not blocks if _to_bool(resolved_cfg.get("enabled", True), True) else True
    severity = "INFO" if allowed else "CRITICAL"
    reason = "account_risk_guard_passed" if allowed else ";".join(blocks)
    action_required = "none" if allowed else "reduce_risk_and_retry"
    return {
        "allowed": bool(allowed),
        "severity": severity,
        "reason": reason,
        "checks": checks,
        "warnings": warnings,
        "blocks": blocks,
        "action_required": action_required,
        "config": resolved_cfg,
    }
