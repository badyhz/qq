from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from core.trade_logger import read_jsonl_rows


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


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


def make_candidate_id(*, symbol: str, seed: str) -> str:
    symbol_text = "".join(ch for ch in str(symbol or "").upper() if ch.isalnum())[:12] or "SYM"
    ts_text = _utc_now().strftime("%Y%m%d%H%M%S%f")
    nonce = str(time.time_ns())
    digest_seed = f"{seed}|{ts_text}|{nonce}"
    digest = hashlib.sha256(digest_seed.encode("utf-8")).hexdigest()[:8]
    return f"cand_{symbol_text}_{ts_text}_{digest}"


def find_duplicate_candidate_ids(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        candidate_id = str(row.get("candidate_id", "")).strip()
        if not candidate_id:
            continue
        counts[candidate_id] = int(counts.get(candidate_id, 0)) + 1
    return {candidate_id: count for candidate_id, count in counts.items() if count > 1}


def load_candidates(path: str) -> list[dict[str, Any]]:
    return [row for row in read_jsonl_rows(path) if isinstance(row, dict)]


def append_candidate(path: str, candidate: dict[str, Any]) -> dict[str, Any]:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(candidate, ensure_ascii=False) + "\n")
    return candidate


def write_candidates(path: str, rows: list[dict[str, Any]]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(dict(row), ensure_ascii=False) + "\n")


def dedupe_candidates(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: dict[str, dict[str, Any]] = {}
    for row in rows:
        candidate_id = str(row.get("candidate_id", "")).strip()
        if not candidate_id:
            continue
        seen[candidate_id] = dict(row)
    return list(seen.values())


def expire_old_candidates(
    rows: list[dict[str, Any]],
    *,
    now_utc: datetime | None = None,
) -> tuple[list[dict[str, Any]], int]:
    now = now_utc or _utc_now()
    expired_count = 0
    updated: list[dict[str, Any]] = []
    for row in rows:
        current = dict(row)
        status = str(current.get("status", "")).strip().upper()
        expires_at = _parse_dt(current.get("expires_at_utc", ""))
        if status in {"PENDING", "APPROVED"} and expires_at is not None and expires_at <= now:
            current["status"] = "EXPIRED"
            current["status_reason"] = "ttl_expired"
            expired_count += 1
        updated.append(current)
    return updated, expired_count


def update_candidate_status(
    path: str,
    candidate_id: str,
    status: str,
    reason: str = "",
) -> bool:
    rows = load_candidates(path)
    changed = False
    target = str(candidate_id or "").strip()
    new_status = str(status or "").strip().upper()
    for row in rows:
        if str(row.get("candidate_id", "")).strip() != target:
            continue
        row["status"] = new_status
        if reason:
            row["status_reason"] = str(reason)
        row["updated_at_utc"] = _utc_now().isoformat()
        changed = True
        break
    if changed:
        write_candidates(path, rows)
    return changed


def has_recent_pending_candidate(
    rows: list[dict[str, Any]],
    *,
    symbol: str,
    ttl_minutes: int,
    now_utc: datetime | None = None,
) -> bool:
    now = now_utc or _utc_now()
    target = str(symbol or "").strip().upper()
    ttl_delta = timedelta(minutes=max(1, int(ttl_minutes)))
    for row in rows:
        if str(row.get("symbol", "")).strip().upper() != target:
            continue
        status = str(row.get("status", "")).strip().upper()
        if status != "PENDING":
            continue
        ts = _parse_dt(row.get("ts_utc", ""))
        if ts is None:
            continue
        if now - ts <= ttl_delta:
            return True
    return False


def _is_enabled_flag(plan: Any) -> bool:
    if not isinstance(plan, dict):
        return False
    if not plan:
        return False
    enabled = plan.get("enabled", True)
    if isinstance(enabled, bool):
        return enabled
    text = str(enabled or "").strip().lower()
    if text in {"0", "false", "no", "off"}:
        return False
    return True


def score_execution_candidate(
    candidate: dict[str, Any],
    *,
    max_symbol_notional_usdt: float = 60.0,
    now_utc: datetime | None = None,
    submitted_correlation_ids: set[str] | None = None,
) -> dict[str, Any]:
    current = dict(candidate)
    now = now_utc or _utc_now()
    submitted_corr = submitted_correlation_ids or set()

    score = 50
    reasons: list[str] = []
    risk_flags = list(current.get("risk_flags", [])) if isinstance(current.get("risk_flags", []), list) else []
    preflight_status = str(current.get("preflight_status", "")).strip().upper()
    notional = 0.0
    try:
        notional = float(current.get("notional_usdt", 0.0) or 0.0)
    except (TypeError, ValueError):
        notional = 0.0

    if preflight_status == "FLAT_CLEAN":
        score += 20
        reasons.append("preflight_flat_clean")
    if _is_enabled_flag(current.get("stop_loss_plan", {})):
        score += 10
        reasons.append("stop_loss_enabled")
    else:
        score -= 30
        reasons.append("stop_loss_missing_or_disabled")
    if _is_enabled_flag(current.get("take_profit_plan", {})):
        score += 10
        reasons.append("take_profit_enabled")
    else:
        score -= 20
        reasons.append("take_profit_missing_or_disabled")
    if notional <= 50:
        score += 5
        reasons.append("notional_small")
    if not risk_flags:
        score += 10
        reasons.append("no_risk_flags")
    else:
        score -= 30
        reasons.append("risk_flags_present")
    if notional > float(max_symbol_notional_usdt):
        score -= 20
        reasons.append("notional_above_symbol_limit")

    expires_at = _parse_dt(current.get("expires_at_utc", ""))
    if expires_at is not None:
        remain = (expires_at - now).total_seconds()
        if 0 <= remain <= 600:
            score -= 10
            reasons.append("expires_soon")

    correlation_id = str(current.get("correlation_id", "")).strip()
    if correlation_id and correlation_id in submitted_corr:
        score -= 10
        reasons.append("duplicate_correlation_with_submitted")

    score = max(0, min(100, int(score)))
    hard_risk = bool(
        set(str(item).strip().upper() for item in risk_flags)
        & {"NAKED_POSITION", "PARTIAL_PROTECTED", "ORPHAN_PROTECTION", "PREFLIGHT_UNAVAILABLE"}
    )
    if hard_risk or score < 40:
        label = "BLOCKED"
    elif score >= 80:
        label = "HIGH"
    elif score >= 60:
        label = "MEDIUM"
    else:
        label = "LOW"

    current["signal_score"] = score
    current["signal_score_label"] = label
    current["signal_score_reasons"] = reasons
    current["risk_score"] = max(0, 100 - score)
    current["execution_priority"] = score
    return current


def apply_candidate_scoring(
    rows: list[dict[str, Any]],
    *,
    max_symbol_notional_usdt: float = 60.0,
    now_utc: datetime | None = None,
) -> list[dict[str, Any]]:
    dict_rows = [row for row in rows if isinstance(row, dict)]
    submitted_corr = {
        str(row.get("correlation_id", "")).strip()
        for row in dict_rows
        if str(row.get("status", "")).strip().upper() == "SUBMITTED" and str(row.get("correlation_id", "")).strip()
    }
    return [
        score_execution_candidate(
            row,
            max_symbol_notional_usdt=max_symbol_notional_usdt,
            now_utc=now_utc,
            submitted_correlation_ids=submitted_corr,
        )
        for row in dict_rows
    ]


def sort_candidates_for_review(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    active: list[dict[str, Any]] = []
    inactive: list[dict[str, Any]] = []
    for row in rows:
        status = str(row.get("status", "")).strip().upper()
        if status in {"PENDING", "APPROVED"}:
            active.append(dict(row))
        else:
            inactive.append(dict(row))

    def _ts_key(item: dict[str, Any]) -> datetime:
        return _parse_dt(item.get("ts_utc", "")) or datetime.min.replace(tzinfo=timezone.utc)

    active.sort(
        key=lambda row: (
            int(row.get("execution_priority", row.get("signal_score", 0)) or 0),
            _ts_key(row),
        ),
        reverse=True,
    )
    return active + inactive
