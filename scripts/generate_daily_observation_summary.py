from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.risk_event_logger import is_expected_safety_rejection
from core.trade_logger import read_jsonl_rows


STATE_KEYS = ["FULLY_PROTECTED", "FLAT_CLEAN", "ORPHAN_PROTECTION", "PARTIAL_PROTECTED", "NAKED_POSITION"]
CANDIDATE_STATUS_KEYS = ["pending", "approved", "rejected", "expired", "submitted", "skipped", "submit_failed"]


def _date_utc_text() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _parse_date(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return _date_utc_text()
    return text


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


def _same_date_utc(value: Any, target_date: str) -> bool:
    dt = _parse_dt(value)
    if dt is None:
        return False
    return dt.strftime("%Y-%m-%d") == target_date


def _in_time_window(dt: datetime | None, since_dt: datetime | None, until_dt: datetime | None) -> bool:
    if dt is None:
        return False
    if since_dt is not None and dt < since_dt:
        return False
    if until_dt is not None and dt > until_dt:
        return False
    return True


def _in_value_window(value: Any, since_dt: datetime | None, until_dt: datetime | None) -> bool:
    if since_dt is None and until_dt is None:
        return True
    return _in_time_window(_parse_dt(value), since_dt, until_dt)


def _shift_status(summary: dict[str, Any]) -> str:
    explicit = str(summary.get("overall_status", "")).strip().upper()
    if explicit in {"PASS", "PARTIAL", "FAIL"}:
        return explicit
    per_symbol = list(summary.get("per_symbol_state", []))
    statuses = {str(row.get("protection_status", "")).strip().upper() for row in per_symbol}
    if "PREFLIGHT_UNAVAILABLE" in statuses:
        return "FAIL"
    if {"ORPHAN_PROTECTION", "PARTIAL_PROTECTED", "NAKED_POSITION"} & statuses:
        return "PARTIAL"
    return "PASS"


def _summarize_observation(
    *,
    observation_dir: str,
    target_date: str,
    since_dt: datetime | None,
    until_dt: datetime | None,
) -> tuple[dict[str, int], dict[str, int], int]:
    counts = {"shifts_total": 0, "shifts_pass": 0, "shifts_partial": 0, "shifts_fail": 0}
    state_counts = {key: 0 for key in STATE_KEYS}
    root = Path(observation_dir)
    if not root.exists():
        return counts, state_counts, 0
    windowed_count = 0

    for summary_path in sorted(root.glob("*/summary.json")):
        try:
            payload = json.loads(summary_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        started_at = payload.get("started_at_utc", "")
        if started_at and not _same_date_utc(started_at, target_date):
            continue
        started_dt = _parse_dt(started_at)
        if not _in_time_window(started_dt, since_dt, until_dt):
            continue
        windowed_count += 1
        counts["shifts_total"] += 1
        shift_status = _shift_status(payload)
        if shift_status == "PASS":
            counts["shifts_pass"] += 1
        elif shift_status == "PARTIAL":
            counts["shifts_partial"] += 1
        else:
            counts["shifts_fail"] += 1
        for row in list(payload.get("per_symbol_state", [])):
            key = str(row.get("protection_status", "")).strip().upper()
            if key in state_counts:
                state_counts[key] += 1
    return counts, state_counts, windowed_count


def _summarize_candidates(
    *,
    candidates_jsonl: str,
    target_date: str,
    since_dt: datetime | None,
    until_dt: datetime | None,
) -> dict[str, int]:
    rows = read_jsonl_rows(candidates_jsonl)
    summary = {"created": 0}
    for key in CANDIDATE_STATUS_KEYS:
        summary[key] = 0

    for row in rows:
        created_dt = _parse_dt(row.get("ts_utc", ""))
        if created_dt is not None and created_dt.strftime("%Y-%m-%d") == target_date and _in_time_window(created_dt, since_dt, until_dt):
            summary["created"] += 1
        activity_ts = row.get("updated_at_utc", "") or row.get("ts_utc", "")
        activity_dt = _parse_dt(activity_ts)
        if activity_dt is None or activity_dt.strftime("%Y-%m-%d") != target_date:
            continue
        if not _in_time_window(activity_dt, since_dt, until_dt):
            continue
        status = str(row.get("status", "")).strip().lower()
        if status in summary:
            summary[status] += 1
    return summary


def _event_in_scope(row: dict[str, Any], scope_filter: set[str]) -> bool:
    if not scope_filter:
        return True
    scope = str(row.get("event_scope", "UNKNOWN")).strip().upper()
    return scope in scope_filter


def _should_include_event(
    row: dict[str, Any],
    *,
    include_test_events: bool,
    include_expected_blocks: bool,
    scope_filter: set[str],
) -> bool:
    if not _event_in_scope(row, scope_filter):
        return False
    is_test_event = bool(row.get("is_test_event", False))
    event_scope = str(row.get("event_scope", "UNKNOWN")).strip().upper() or "UNKNOWN"
    is_expected_block = bool(row.get("is_expected_block", False))
    if (not include_test_events) and (is_test_event or event_scope in {"TEST_FIXTURE", "LOCAL_DRY_RUN"}):
        return False
    if (not include_expected_blocks) and event_scope == "LIVE_BLOCK_TEST" and is_expected_block:
        return False
    return True


def _summarize_risk_events(
    *,
    risk_events_jsonl: str,
    target_date: str,
    include_test_events: bool,
    include_expected_blocks: bool,
    scope_filter: set[str],
    production_only: bool,
    ignore_expected_safety_rejections: bool,
    since_dt: datetime | None,
    until_dt: datetime | None,
) -> dict[str, Any]:
    rows = read_jsonl_rows(risk_events_jsonl)
    count_by_severity: dict[str, int] = {}
    count_by_event_type: dict[str, int] = {}
    latest_critical: dict[str, Any] = {}
    latest_error: dict[str, Any] = {}
    filtered_events_count = 0
    ignored_test_events_count = 0
    included_events_count = 0
    count_by_scope: dict[str, int] = {}
    filtered_by_scope: dict[str, int] = {}
    unknown_by_type: dict[str, int] = {}
    expected_safety_rejection_count = 0
    ignored_expected_safety_rejection_count = 0
    non_expected_error_count = 0
    non_expected_critical_count = 0
    non_expected_warning_count = 0
    included_rows: list[dict[str, Any]] = []
    windowed_total_rows = 0

    for row in rows:
        ts = _parse_dt(row.get("ts_utc", ""))
        if ts is None or ts.strftime("%Y-%m-%d") != target_date:
            continue
        if not _in_time_window(ts, since_dt, until_dt):
            continue
        windowed_total_rows += 1
        scope = str(row.get("event_scope", "UNKNOWN")).strip().upper() or "UNKNOWN"
        count_by_scope[scope] = int(count_by_scope.get(scope, 0)) + 1
        if scope == "UNKNOWN":
            unknown_type = str(row.get("event_type", "UNKNOWN")).strip().upper()
            unknown_by_type[unknown_type] = int(unknown_by_type.get(unknown_type, 0)) + 1
        if production_only:
            if scope not in {"TESTNET_REAL", "PRODUCTION_LIKE"} or bool(row.get("is_test_event", False)) or bool(row.get("is_expected_block", False)):
                filtered_events_count += 1
                filtered_by_scope[scope] = int(filtered_by_scope.get(scope, 0)) + 1
                if bool(row.get("is_test_event", False)):
                    ignored_test_events_count += 1
                continue
        include = _should_include_event(
            row,
            include_test_events=include_test_events,
            include_expected_blocks=include_expected_blocks,
            scope_filter=scope_filter,
        )
        if not include:
            filtered_events_count += 1
            filtered_by_scope[scope] = int(filtered_by_scope.get(scope, 0)) + 1
            if bool(row.get("is_test_event", False)) or str(row.get("event_scope", "")).strip().upper() in {
                "TEST_FIXTURE",
                "LOCAL_DRY_RUN",
                "LIVE_BLOCK_TEST",
            }:
                ignored_test_events_count += 1
            continue
        is_expected = is_expected_safety_rejection(row)
        if is_expected:
            expected_safety_rejection_count += 1
            if ignore_expected_safety_rejections:
                ignored_expected_safety_rejection_count += 1
                filtered_events_count += 1
                filtered_by_scope[scope] = int(filtered_by_scope.get(scope, 0)) + 1
                continue
        included_events_count += 1
        severity = str(row.get("severity", "UNKNOWN")).strip().upper()
        event_type = str(row.get("event_type", "UNKNOWN")).strip().upper()
        count_by_severity[severity] = int(count_by_severity.get(severity, 0)) + 1
        count_by_event_type[event_type] = int(count_by_event_type.get(event_type, 0)) + 1
        included_rows.append(row)
        if severity == "CRITICAL":
            latest_critical = row
            if not is_expected:
                non_expected_critical_count += 1
        if severity == "ERROR":
            latest_error = row
            if not is_expected:
                non_expected_error_count += 1
        if severity == "WARNING":
            if not is_expected:
                non_expected_warning_count += 1

    latest_events = sorted(
        included_rows,
        key=lambda row: _parse_dt(row.get("ts_utc", "")) or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )[:20]

    return {
        "count_by_severity": count_by_severity,
        "count_by_event_type": count_by_event_type,
        "latest_critical": latest_critical,
        "latest_error": latest_error,
        "filtered_events_count": filtered_events_count,
        "ignored_test_events_count": ignored_test_events_count,
        "included_events_count": included_events_count,
        "count_by_scope": count_by_scope,
        "filtered_by_scope": filtered_by_scope,
        "unknown_events_count": int(count_by_scope.get("UNKNOWN", 0)),
        "expected_safety_rejection_count": expected_safety_rejection_count,
        "ignored_expected_safety_rejection_count": ignored_expected_safety_rejection_count,
        "non_expected_error_count": non_expected_error_count,
        "non_expected_critical_count": non_expected_critical_count,
        "non_expected_warning_count": non_expected_warning_count,
        "windowed_total_rows": windowed_total_rows,
        "latest_events": latest_events,
        "top_unknown_event_types": sorted(
            [{"event_type": event_type, "count": count} for event_type, count in unknown_by_type.items()],
            key=lambda item: int(item.get("count", 0)),
            reverse=True,
        )[:10],
    }


def _include_approved_run(
    summary_path: Path,
    payload: dict[str, Any],
    target_date: str,
    since_dt: datetime | None,
    until_dt: datetime | None,
) -> bool:
    run_id = str(payload.get("run_id", "")).strip()
    completed_at = _parse_dt(payload.get("completed_at_utc", "")) or _parse_dt(payload.get("started_at_utc", ""))
    if completed_at is not None:
        if completed_at.strftime("%Y-%m-%d") != target_date:
            return False
        return _in_time_window(completed_at, since_dt, until_dt)
    if run_id:
        compact_date = target_date.replace("-", "")
        if compact_date in run_id:
            mtime = datetime.fromtimestamp(summary_path.stat().st_mtime, tz=timezone.utc)
            return _in_time_window(mtime, since_dt, until_dt)
    mtime = datetime.fromtimestamp(summary_path.stat().st_mtime, tz=timezone.utc)
    return mtime.strftime("%Y-%m-%d") == target_date and _in_time_window(mtime, since_dt, until_dt)


def _summarize_approved_runs(
    *,
    approved_runs_dir: str,
    target_date: str,
    since_dt: datetime | None,
    until_dt: datetime | None,
) -> dict[str, int]:
    summary = {"runs_total": 0, "planned_count": 0, "submitted_count": 0, "failed_count": 0, "windowed_runs_total": 0}
    root = Path(approved_runs_dir)
    if not root.exists():
        return summary
    for summary_path in sorted(root.glob("*/summary.json")):
        try:
            payload = json.loads(summary_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not _include_approved_run(summary_path, payload, target_date, since_dt, until_dt):
            continue
        summary["windowed_runs_total"] += 1
        summary["runs_total"] += 1
        summary["planned_count"] += int(payload.get("planned_count", 0) or 0)
        summary["submitted_count"] += int(payload.get("submitted_count", 0) or 0)
        summary["failed_count"] += int(payload.get("failed_count", 0) or 0)
    return summary


def _verdict(
    *,
    risk_summary: dict[str, Any],
    candidate_summary: dict[str, int],
    observation_summary: dict[str, int],
) -> tuple[str, str]:
    critical_count = int(risk_summary.get("non_expected_critical_count", 0))
    error_count = int(risk_summary.get("non_expected_error_count", 0))
    warning_count = int(risk_summary.get("non_expected_warning_count", 0))
    event_type_counts = dict(risk_summary.get("count_by_event_type", {}))
    submit_failed = int(candidate_summary.get("submit_failed", 0))
    if critical_count > 0:
        return "FAIL", "non_expected_critical_events_detected"
    if submit_failed > 0:
        return "FAIL", "candidate_submit_failed_detected"
    if int(event_type_counts.get("CANDIDATE_SUBMIT_FAILED", 0)) > 0:
        return "FAIL", "risk_event_candidate_submit_failed_detected"
    if int(event_type_counts.get("NAKED_POSITION_DETECTED", 0)) > 0:
        return "FAIL", "real_naked_position_detected"
    if int(event_type_counts.get("PROTECTIVE_ORDER_FAILED", 0)) > 0 or int(event_type_counts.get("PROTECTIVE_ORDER_PARTIAL", 0)) > 0:
        return "FAIL", "real_protective_order_failure_detected"
    if error_count > 0 or warning_count > 0:
        return "PARTIAL", "non_expected_warning_or_error_events_detected"
    if int(observation_summary.get("shifts_partial", 0)) > 0:
        return "PARTIAL", "observation_shift_partial_present"
    if int(candidate_summary.get("pending", 0)) > 0 or int(candidate_summary.get("approved", 0)) > 0:
        return "PARTIAL", "candidate_queue_has_pending_or_approved_items"
    return "PASS", "no_non_expected_risk_and_queue_clean"


def _clean_shift_verdict(
    *,
    risk_summary: dict[str, Any],
    candidate_summary: dict[str, int],
    state_summary: dict[str, int],
    windowed_risk_event_count: int,
) -> tuple[str, str, bool]:
    non_expected_critical = int(risk_summary.get("non_expected_critical_count", 0))
    non_expected_error = int(risk_summary.get("non_expected_error_count", 0))
    non_expected_warning = int(risk_summary.get("non_expected_warning_count", 0))
    event_type_counts = dict(risk_summary.get("count_by_event_type", {}))
    no_events = windowed_risk_event_count == 0

    if non_expected_critical > 0:
        return "FAIL", "clean_window_non_expected_critical_detected", no_events
    if non_expected_error > 0:
        return "FAIL", "clean_window_non_expected_error_detected", no_events
    if int(candidate_summary.get("submit_failed", 0)) > 0 or int(event_type_counts.get("CANDIDATE_SUBMIT_FAILED", 0)) > 0:
        return "FAIL", "clean_window_submit_failed_detected", no_events
    if int(state_summary.get("NAKED_POSITION", 0)) > 0 or int(event_type_counts.get("NAKED_POSITION_DETECTED", 0)) > 0:
        return "FAIL", "clean_window_naked_position_detected", no_events
    if int(event_type_counts.get("PROTECTIVE_ORDER_FAILED", 0)) > 0 or int(event_type_counts.get("PROTECTIVE_ORDER_PARTIAL", 0)) > 0:
        return "FAIL", "clean_window_protective_order_failure_detected", no_events

    if int(state_summary.get("ORPHAN_PROTECTION", 0)) > 0 or int(state_summary.get("PARTIAL_PROTECTED", 0)) > 0:
        return "PARTIAL", "clean_window_state_has_orphan_or_partial", no_events
    if non_expected_warning > 0:
        return "PARTIAL", "clean_window_non_expected_warning_detected", no_events
    if int(candidate_summary.get("pending", 0)) > 0 or int(candidate_summary.get("approved", 0)) > 0:
        return "PARTIAL", "clean_window_pending_or_approved_candidates_exist", no_events
    if no_events:
        return "PASS", "clean_window_no_events", no_events
    return "PASS", "clean_window_no_non_expected_risk", no_events


def _write_markdown(path: Path, summary: dict[str, Any]) -> None:
    observation = dict(summary.get("observation", {}))
    states = dict(summary.get("states", {}))
    candidates = dict(summary.get("candidates", {}))
    risk = dict(summary.get("risk_events", {}))
    approved = dict(summary.get("approved_runs", {}))
    lines = [
        "# Daily Observation Summary",
        "",
        f"- date: {summary.get('date', '')}",
        f"- verdict: {summary.get('verdict', '')}",
        "",
        "## Observation",
        f"- shifts_total: {observation.get('shifts_total', 0)}",
        f"- shifts_pass: {observation.get('shifts_pass', 0)}",
        f"- shifts_partial: {observation.get('shifts_partial', 0)}",
        f"- shifts_fail: {observation.get('shifts_fail', 0)}",
        "",
        "## States",
    ]
    for key in STATE_KEYS:
        lines.append(f"- {key}: {states.get(key, 0)}")
    lines.extend(
        [
            "",
            "## Candidates",
            f"- created: {candidates.get('created', 0)}",
        ]
    )
    for key in CANDIDATE_STATUS_KEYS:
        lines.append(f"- {key}: {candidates.get(key, 0)}")
    lines.extend(
        [
            "",
            "## Risk Events",
            f"- count_by_severity: {json.dumps(risk.get('count_by_severity', {}), ensure_ascii=False)}",
            f"- count_by_event_type: {json.dumps(risk.get('count_by_event_type', {}), ensure_ascii=False)}",
            f"- latest_critical: {json.dumps(risk.get('latest_critical', {}), ensure_ascii=False)}",
            f"- latest_error: {json.dumps(risk.get('latest_error', {}), ensure_ascii=False)}",
            f"- count_by_scope: {json.dumps(risk.get('count_by_scope', {}), ensure_ascii=False)}",
            f"- filtered_by_scope: {json.dumps(risk.get('filtered_by_scope', {}), ensure_ascii=False)}",
            f"- filtered_events_count: {risk.get('filtered_events_count', 0)}",
            f"- ignored_test_events_count: {risk.get('ignored_test_events_count', 0)}",
            f"- included_events_count: {risk.get('included_events_count', 0)}",
            f"- unknown_events_count: {risk.get('unknown_events_count', 0)}",
            f"- expected_safety_rejection_count: {risk.get('expected_safety_rejection_count', 0)}",
            f"- ignored_expected_safety_rejection_count: {risk.get('ignored_expected_safety_rejection_count', 0)}",
            f"- non_expected_error_count: {risk.get('non_expected_error_count', 0)}",
            f"- non_expected_critical_count: {risk.get('non_expected_critical_count', 0)}",
            f"- top_unknown_event_types: {json.dumps(risk.get('top_unknown_event_types', []), ensure_ascii=False)}",
            f"- verdict_reason: {summary.get('verdict_reason', '')}",
            "",
            "## Approved Runs",
            f"- runs_total: {approved.get('runs_total', 0)}",
            f"- planned_count: {approved.get('planned_count', 0)}",
            f"- submitted_count: {approved.get('submitted_count', 0)}",
            f"- failed_count: {approved.get('failed_count', 0)}",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def generate_daily_observation_summary(
    *,
    date: str = "",
    observation_dir: str = "logs/observation_shifts",
    risk_events_jsonl: str = "logs/risk_events.jsonl",
    candidates_jsonl: str = "logs/execution_candidates.jsonl",
    approved_runs_dir: str = "logs/approved_candidate_runs",
    output_md: str = "",
    include_test_events: bool = False,
    include_expected_blocks: bool = False,
    ignore_expected_safety_rejections: bool = True,
    event_scope: str = "",
    production_only: bool = False,
    since_utc: str = "",
    until_utc: str = "",
    clean_window: bool = False,
    label: str = "",
) -> dict[str, Any]:
    target_date = _parse_date(date)
    since_dt = _parse_dt(since_utc)
    until_dt = _parse_dt(until_utc)
    effective_clean_window = bool(clean_window)
    effective_production_only = bool(production_only or effective_clean_window)
    effective_ignore_expected_safety_rejections = True if effective_clean_window else bool(ignore_expected_safety_rejections)
    resolved_output_md = output_md or f"logs/daily_summary_{target_date}.md"
    scope_filter = {item.strip().upper() for item in str(event_scope or "").split(",") if item.strip()}
    observation, states, windowed_observation_count = _summarize_observation(
        observation_dir=observation_dir,
        target_date=target_date,
        since_dt=since_dt,
        until_dt=until_dt,
    )
    candidates = _summarize_candidates(
        candidates_jsonl=candidates_jsonl,
        target_date=target_date,
        since_dt=since_dt,
        until_dt=until_dt,
    )
    risk = _summarize_risk_events(
        risk_events_jsonl=risk_events_jsonl,
        target_date=target_date,
        include_test_events=bool(include_test_events),
        include_expected_blocks=bool(include_expected_blocks),
        scope_filter=scope_filter,
        production_only=effective_production_only,
        ignore_expected_safety_rejections=effective_ignore_expected_safety_rejections,
        since_dt=since_dt,
        until_dt=until_dt,
    )
    approved_runs = _summarize_approved_runs(
        approved_runs_dir=approved_runs_dir,
        target_date=target_date,
        since_dt=since_dt,
        until_dt=until_dt,
    )
    verdict, verdict_reason = _verdict(risk_summary=risk, candidate_summary=candidates, observation_summary=observation)
    clean_shift_verdict = ""
    clean_shift_reason = ""
    no_events_in_clean_window = False
    if effective_clean_window:
        clean_shift_verdict, clean_shift_reason, no_events_in_clean_window = _clean_shift_verdict(
            risk_summary=risk,
            candidate_summary=candidates,
            state_summary=states,
            windowed_risk_event_count=int(risk.get("windowed_total_rows", 0)),
        )
        verdict = clean_shift_verdict
        verdict_reason = clean_shift_reason
    summary = {
        "date": target_date,
        "observation": observation,
        "states": states,
        "candidates": candidates,
        "risk_events": risk,
        "approved_runs": approved_runs,
        "verdict": verdict,
        "verdict_reason": verdict_reason,
        "clean_shift_verdict": clean_shift_verdict,
        "clean_shift_reason": clean_shift_reason,
        "no_events_in_clean_window": no_events_in_clean_window,
        "output_md": resolved_output_md,
        "include_test_events": bool(include_test_events),
        "include_expected_blocks": bool(include_expected_blocks),
        "ignore_expected_safety_rejections": effective_ignore_expected_safety_rejections,
        "event_scope_filter": sorted(list(scope_filter)),
        "production_only": effective_production_only,
        "clean_window": effective_clean_window,
        "since_utc": since_dt.isoformat() if since_dt is not None else "",
        "until_utc": until_dt.isoformat() if until_dt is not None else "",
        "label": str(label or ""),
        "windowed_observation_count": windowed_observation_count,
        "windowed_risk_event_count": int(risk.get("windowed_total_rows", 0)),
        "windowed_approved_runs_count": int(approved_runs.get("windowed_runs_total", 0)),
    }
    _write_markdown(Path(resolved_output_md), summary)
    return summary


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate daily summary for observation, candidates, risks, and approved runs")
    parser.add_argument("--date", default="")
    parser.add_argument("--observation-dir", default="logs/observation_shifts")
    parser.add_argument("--risk-events-jsonl", default="logs/risk_events.jsonl")
    parser.add_argument("--candidates-jsonl", default="logs/execution_candidates.jsonl")
    parser.add_argument("--approved-runs-dir", default="logs/approved_candidate_runs")
    parser.add_argument("--output-md", default="")
    parser.add_argument("--include-test-events", default="false")
    parser.add_argument("--include-expected-blocks", default="false")
    parser.add_argument("--ignore-expected-safety-rejections", default="true")
    parser.add_argument("--event-scope", default="")
    parser.add_argument("--production-only", action="store_true")
    parser.add_argument("--since-utc", default="")
    parser.add_argument("--until-utc", default="")
    parser.add_argument("--clean-window", default="false")
    parser.add_argument("--label", default="")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    summary = generate_daily_observation_summary(
        date=str(args.date or ""),
        observation_dir=str(args.observation_dir or "logs/observation_shifts"),
        risk_events_jsonl=str(args.risk_events_jsonl or "logs/risk_events.jsonl"),
        candidates_jsonl=str(args.candidates_jsonl or "logs/execution_candidates.jsonl"),
        approved_runs_dir=str(args.approved_runs_dir or "logs/approved_candidate_runs"),
        output_md=str(args.output_md or ""),
        include_test_events=_to_bool(args.include_test_events, default=False),
        include_expected_blocks=_to_bool(args.include_expected_blocks, default=False),
        ignore_expected_safety_rejections=_to_bool(args.ignore_expected_safety_rejections, default=True),
        event_scope=str(args.event_scope or ""),
        production_only=bool(args.production_only),
        since_utc=str(args.since_utc or ""),
        until_utc=str(args.until_utc or ""),
        clean_window=_to_bool(args.clean_window, default=False),
        label=str(args.label or ""),
    )
    if bool(args.json):
        print(json.dumps(summary, ensure_ascii=False))
        return
    print(f"date={summary.get('date', '')}")
    print(f"verdict={summary.get('verdict', '')}")
    print(f"output_md={summary.get('output_md', '')}")


if __name__ == "__main__":
    main()
