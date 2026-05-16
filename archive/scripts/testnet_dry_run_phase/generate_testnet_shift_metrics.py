from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.execution_candidate_queue import find_duplicate_candidate_ids
from core.risk_event_logger import is_expected_safety_rejection
from core.trade_logger import read_jsonl_rows


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


def _to_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    return bool(default)


def _in_window(dt: datetime | None, since_dt: datetime | None, until_dt: datetime | None) -> bool:
    if dt is None:
        return False
    if since_dt is not None and dt < since_dt:
        return False
    if until_dt is not None and dt > until_dt:
        return False
    return True


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _latest_state_snapshot(root: Path, since_dt: datetime | None, until_dt: datetime | None) -> dict[str, Any]:
    latest: dict[str, Any] = {}
    latest_dt = datetime.min.replace(tzinfo=timezone.utc)
    for state_path in root.glob("*/state.json"):
        payload = _load_json(state_path)
        ts = _parse_dt(payload.get("ts_utc", "")) or datetime.fromtimestamp(state_path.stat().st_mtime, tz=timezone.utc)
        if (since_dt is not None or until_dt is not None) and (not _in_window(ts, since_dt, until_dt)):
            continue
        if ts > latest_dt:
            latest_dt = ts
            latest = payload
    return latest


def _protection_window_counts(root: Path, since_dt: datetime | None, until_dt: datetime | None) -> dict[str, int]:
    counts = {"ORPHAN_PROTECTION": 0, "PARTIAL_PROTECTED": 0, "NAKED_POSITION": 0}
    for state_path in root.glob("*/state.json"):
        payload = _load_json(state_path)
        ts = _parse_dt(payload.get("ts_utc", "")) or datetime.fromtimestamp(state_path.stat().st_mtime, tz=timezone.utc)
        if (since_dt is not None or until_dt is not None) and (not _in_window(ts, since_dt, until_dt)):
            continue
        for item in [row for row in list(payload.get("per_symbol_state", [])) if isinstance(row, dict)]:
            status = str(item.get("protection_status", "")).strip().upper()
            if status in counts:
                counts[status] += 1
    return counts


def _summarize_shift_reviews(root: Path, since_dt: datetime | None, until_dt: datetime | None) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for report_path in root.glob("shift_reviews/*.json"):
        payload = _load_json(report_path)
        ts = _parse_dt(payload.get("state_snapshot", {}).get("ts_utc", "")) or datetime.fromtimestamp(report_path.stat().st_mtime, tz=timezone.utc)
        if (since_dt is not None or until_dt is not None) and (not _in_window(ts, since_dt, until_dt)):
            continue
        rows.append(payload)
    rows.sort(key=lambda item: _parse_dt(item.get("state_snapshot", {}).get("ts_utc", "")) or datetime.min.replace(tzinfo=timezone.utc))
    pass_count = sum(1 for row in rows if str(row.get("verdict", "")).strip().upper() == "PASS")
    partial_count = sum(1 for row in rows if str(row.get("verdict", "")).strip().upper() == "PARTIAL")
    fail_count = sum(1 for row in rows if str(row.get("verdict", "")).strip().upper() == "FAIL")
    latest = rows[-1] if rows else {}
    return {
        "shift_reviews_total": len(rows),
        "shift_pass_count": pass_count,
        "shift_partial_count": partial_count,
        "shift_fail_count": fail_count,
        "latest_shift_verdict": str(latest.get("verdict", "")),
        "latest_shift_reason": str(latest.get("verdict_reason", "")),
    }


def _summarize_approved_runs(root: Path, since_dt: datetime | None, until_dt: datetime | None) -> dict[str, Any]:
    totals = {
        "approved_runs_total": 0,
        "submitted_runs_total": 0,
        "dry_run_runs_total": 0,
        "failed_runs_total": 0,
        "total_planned_count": 0,
        "total_submitted_count": 0,
        "total_failed_count": 0,
        "submit_success_rate": 0.0,
    }
    for summary_path in root.glob("approved_candidate_runs/*/summary.json"):
        payload = _load_json(summary_path)
        ts = _parse_dt(payload.get("completed_at_utc", "") or payload.get("started_at_utc", "")) or datetime.fromtimestamp(
            summary_path.stat().st_mtime, tz=timezone.utc
        )
        if (since_dt is not None or until_dt is not None) and (not _in_window(ts, since_dt, until_dt)):
            continue
        totals["approved_runs_total"] += 1
        planned = int(payload.get("planned_count", 0) or 0)
        submitted = int(payload.get("submitted_count", 0) or 0)
        failed = int(payload.get("failed_count", 0) or 0)
        totals["total_planned_count"] += planned
        totals["total_submitted_count"] += submitted
        totals["total_failed_count"] += failed
        if bool(payload.get("dry_run", True)):
            totals["dry_run_runs_total"] += 1
        if submitted > 0:
            totals["submitted_runs_total"] += 1
        if failed > 0:
            totals["failed_runs_total"] += 1
    planned_total = int(totals["total_planned_count"])
    submitted_total = int(totals["total_submitted_count"])
    totals["submit_success_rate"] = round((submitted_total / planned_total), 4) if planned_total > 0 else 0.0
    return totals


def _summarize_candidates(path: Path) -> dict[str, Any]:
    rows = [row for row in read_jsonl_rows(str(path)) if isinstance(row, dict)]
    status_counts = {
        "pending_count": 0,
        "approved_count": 0,
        "submitted_count": 0,
        "rejected_count": 0,
        "expired_count": 0,
        "submit_failed_count": 0,
    }
    for row in rows:
        status = str(row.get("status", "")).strip().upper()
        if status == "PENDING":
            status_counts["pending_count"] += 1
        elif status == "APPROVED":
            status_counts["approved_count"] += 1
        elif status == "SUBMITTED":
            status_counts["submitted_count"] += 1
        elif status == "REJECTED":
            status_counts["rejected_count"] += 1
        elif status == "EXPIRED":
            status_counts["expired_count"] += 1
        elif status == "SUBMIT_FAILED":
            status_counts["submit_failed_count"] += 1
    duplicates = find_duplicate_candidate_ids(rows)
    status_counts["candidate_total"] = len(rows)
    status_counts["duplicate_candidate_id_count"] = len(duplicates)
    status_counts["duplicate_candidate_ids"] = sorted(list(duplicates.keys()))
    return status_counts


def _should_include_event(
    row: dict[str, Any],
    *,
    production_only: bool,
    include_test_events: bool,
    include_expected_blocks: bool,
) -> tuple[bool, bool]:
    scope = str(row.get("event_scope", "UNKNOWN")).strip().upper() or "UNKNOWN"
    is_test_event = bool(row.get("is_test_event", False))
    is_expected_block = bool(row.get("is_expected_block", False))
    if production_only:
        if scope not in {"TESTNET_REAL", "PRODUCTION_LIKE"}:
            return False, is_test_event
        if is_test_event or is_expected_block:
            return False, is_test_event
        return True, is_test_event
    if (not include_test_events) and (is_test_event or scope in {"TEST_FIXTURE", "LOCAL_DRY_RUN"}):
        return False, True
    if (not include_expected_blocks) and scope == "LIVE_BLOCK_TEST" and is_expected_block:
        return False, is_test_event
    return True, is_test_event


def _summarize_risk_events(
    path: Path,
    since_dt: datetime | None,
    until_dt: datetime | None,
    *,
    production_only: bool,
    include_test_events: bool,
    include_expected_blocks: bool,
    ignore_expected_safety_rejections: bool,
) -> dict[str, Any]:
    rows = [row for row in read_jsonl_rows(str(path)) if isinstance(row, dict)]
    non_expected_critical = 0
    non_expected_error = 0
    non_expected_warning = 0
    expected_safety = 0
    ignored_expected_safety = 0
    latest_critical: dict[str, Any] = {}
    latest_error: dict[str, Any] = {}
    filtered_events_count = 0
    included_events_count = 0
    ignored_test_events_count = 0

    for row in rows:
        ts = _parse_dt(row.get("ts_utc", ""))
        if (since_dt is not None or until_dt is not None) and (not _in_window(ts, since_dt, until_dt)):
            continue
        include, is_test_event = _should_include_event(
            row,
            production_only=production_only,
            include_test_events=include_test_events,
            include_expected_blocks=include_expected_blocks,
        )
        if not include:
            filtered_events_count += 1
            if is_test_event:
                ignored_test_events_count += 1
            continue
        is_expected = is_expected_safety_rejection(row)
        if is_expected:
            expected_safety += 1
            if ignore_expected_safety_rejections:
                ignored_expected_safety += 1
                filtered_events_count += 1
                continue
        included_events_count += 1
        severity = str(row.get("severity", "")).strip().upper()
        if severity == "CRITICAL":
            non_expected_critical += 1
            latest_critical = row
        elif severity == "ERROR":
            non_expected_error += 1
            latest_error = row
        elif severity == "WARNING":
            non_expected_warning += 1
    return {
        "non_expected_critical_count": non_expected_critical,
        "non_expected_error_count": non_expected_error,
        "non_expected_warning_count": non_expected_warning,
        "expected_safety_rejection_count": expected_safety,
        "ignored_expected_safety_rejection_count": ignored_expected_safety,
        "filtered_events_count": filtered_events_count,
        "included_events_count": included_events_count,
        "ignored_test_events_count": ignored_test_events_count,
        "latest_critical": latest_critical,
        "latest_error": latest_error,
    }


def _verdict(
    *,
    runs: dict[str, Any],
    protection: dict[str, Any],
    queue: dict[str, Any],
    risk: dict[str, Any],
    clean_window: bool,
) -> tuple[str, str]:
    latest_aggregate = str(protection.get("latest_aggregate_status", "")).strip().upper()
    if latest_aggregate == "CRITICAL":
        return "FAIL", "latest_state_critical"
    if int(protection.get("latest_naked_symbols", 0)) > 0:
        return "FAIL", "latest_state_naked_position_present"
    if int(queue.get("submit_failed_count", 0)) > 0:
        return "FAIL", "candidate_submit_failed_present"
    if int(queue.get("duplicate_candidate_id_count", 0)) > 0:
        return "FAIL", "duplicate_candidate_ids_present"
    if int(risk.get("non_expected_critical_count", 0)) > 0:
        return "FAIL", "non_expected_critical_events_detected"
    if int(risk.get("non_expected_error_count", 0)) > 0:
        return "FAIL", "non_expected_error_events_detected"
    if int(runs.get("failed_runs_total", 0)) > 0:
        return "FAIL", "approved_run_failures_present"
    if latest_aggregate == "WARNING":
        return "PARTIAL", "latest_state_warning"
    if int(queue.get("pending_count", 0)) > 0 or int(queue.get("approved_count", 0)) > 0:
        return "PARTIAL", "pending_or_approved_candidates_present"
    if int(risk.get("non_expected_warning_count", 0)) > 0:
        return "PARTIAL", "non_expected_warning_events_detected"
    if int(runs.get("submitted_runs_total", 0)) < 1:
        return "PARTIAL", "no_successful_submit_run_in_scope"
    if clean_window:
        if latest_aggregate == "CLEAN":
            return "PASS", "clean_window_stable"
        return "PARTIAL", "clean_window_state_not_clean"
    if latest_aggregate == "CLEAN":
        return "PASS", "stable_clean_shift_window"
    return "PARTIAL", "state_not_clean_but_no_hard_failures"


def _write_markdown(path: Path, report: dict[str, Any]) -> None:
    lines = [
        "# Testnet Shift Metrics",
        "",
        f"- verdict: {report.get('verdict', '')}",
        f"- verdict_reason: {report.get('verdict_reason', '')}",
        f"- verdict_scope: {report.get('verdict_scope', '')}",
        f"- production_only: {report.get('production_only', False)}",
        f"- clean_window: {report.get('clean_window', False)}",
        f"- since_utc: {report.get('since_utc', '')}",
        f"- until_utc: {report.get('until_utc', '')}",
        "",
        "## Shift Reviews",
    ]
    for key, value in dict(report.get("shift_review", {})).items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Approved Runs"])
    for key, value in dict(report.get("approved_runs", {})).items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Protection Health"])
    for key, value in dict(report.get("protection_health", {})).items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Candidate Queue"])
    for key, value in dict(report.get("candidate_queue", {})).items():
        if key == "duplicate_candidate_ids":
            continue
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Risk Events"])
    for key, value in dict(report.get("risk_events", {})).items():
        if key in {"latest_critical", "latest_error"}:
            lines.append(f"- {key}: {json.dumps(value, ensure_ascii=False)}")
        else:
            lines.append(f"- {key}: {value}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def generate_testnet_shift_metrics(
    *,
    logs_dir: str = "logs",
    risk_events_jsonl: str = "logs/risk_events_scoped_v4.jsonl",
    production_only: bool = False,
    clean_window: bool = False,
    ignore_expected_safety_rejections: bool = True,
    include_test_events: bool = False,
    include_expected_blocks: bool = False,
    label: str = "",
    since_utc: str = "",
    until_utc: str = "",
    output_md: str = "logs/testnet_shift_metrics.md",
    json_output: bool = False,
) -> dict[str, Any]:
    root = Path(logs_dir)
    now = datetime.now(timezone.utc)
    since_dt = _parse_dt(since_utc)
    until_dt = _parse_dt(until_utc)
    if bool(clean_window):
        if since_dt is None:
            since_dt = now.replace(hour=0, minute=0, second=0, microsecond=0)
        if until_dt is None:
            until_dt = now
    verdict_scope = "clean_window" if bool(clean_window) else "full_history"

    shift = _summarize_shift_reviews(root, since_dt, until_dt)
    runs = _summarize_approved_runs(root, since_dt, until_dt)
    latest_snapshot = _latest_state_snapshot(root / "testnet_state_snapshots", since_dt, until_dt)
    protection_window = _protection_window_counts(root / "testnet_state_snapshots", since_dt, until_dt)
    per_symbol = [row for row in list(latest_snapshot.get("per_symbol_state", [])) if isinstance(row, dict)]
    latest_orphan = sum(1 for row in per_symbol if str(row.get("protection_status", "")).strip().upper() == "ORPHAN_PROTECTION")
    latest_partial = sum(1 for row in per_symbol if str(row.get("protection_status", "")).strip().upper() == "PARTIAL_PROTECTED")
    latest_naked = sum(1 for row in per_symbol if str(row.get("protection_status", "")).strip().upper() == "NAKED_POSITION")
    protection = {
        "latest_aggregate_status": str(latest_snapshot.get("aggregate_status", "UNKNOWN")),
        "latest_flat_clean_symbols": len(list(latest_snapshot.get("clean_symbols", []))),
        "latest_fully_protected_symbols": len(list(latest_snapshot.get("fully_protected_symbols", []))),
        "latest_orphan_symbols": latest_orphan,
        "latest_partial_symbols": latest_partial,
        "latest_naked_symbols": latest_naked,
        "orphan_count_over_window": int(protection_window.get("ORPHAN_PROTECTION", 0)),
        "partial_count_over_window": int(protection_window.get("PARTIAL_PROTECTED", 0)),
        "naked_count_over_window": int(protection_window.get("NAKED_POSITION", 0)),
    }
    queue = _summarize_candidates(root / "execution_candidates.jsonl")
    risk = _summarize_risk_events(
        Path(risk_events_jsonl),
        since_dt,
        until_dt,
        production_only=bool(production_only),
        include_test_events=bool(include_test_events),
        include_expected_blocks=bool(include_expected_blocks),
        ignore_expected_safety_rejections=bool(ignore_expected_safety_rejections),
    )
    verdict, verdict_reason = _verdict(runs=runs, protection=protection, queue=queue, risk=risk, clean_window=bool(clean_window))
    report = {
        "ok": True,
        "logs_dir": str(root),
        "risk_events_jsonl": str(risk_events_jsonl),
        "since_utc": since_dt.isoformat() if since_dt is not None else "",
        "until_utc": until_dt.isoformat() if until_dt is not None else "",
        "production_only": bool(production_only),
        "clean_window": bool(clean_window),
        "label": str(label or ""),
        "verdict_scope": verdict_scope,
        "shift_review": shift,
        "approved_runs": runs,
        "protection_health": protection,
        "candidate_queue": queue,
        "risk_events": risk,
        "latest_aggregate_status": str(protection.get("latest_aggregate_status", "UNKNOWN")),
        "duplicate_candidate_id_count": int(queue.get("duplicate_candidate_id_count", 0)),
        "pending_count": int(queue.get("pending_count", 0)),
        "approved_count": int(queue.get("approved_count", 0)),
        "filtered_events_count": int(risk.get("filtered_events_count", 0)),
        "included_events_count": int(risk.get("included_events_count", 0)),
        "ignored_test_events_count": int(risk.get("ignored_test_events_count", 0)),
        "expected_safety_rejection_count": int(risk.get("expected_safety_rejection_count", 0)),
        "ignored_expected_safety_rejection_count": int(risk.get("ignored_expected_safety_rejection_count", 0)),
        "non_expected_critical_count": int(risk.get("non_expected_critical_count", 0)),
        "non_expected_error_count": int(risk.get("non_expected_error_count", 0)),
        "non_expected_warning_count": int(risk.get("non_expected_warning_count", 0)),
        "verdict": verdict,
        "verdict_reason": verdict_reason,
        "output_md": output_md,
    }
    _write_markdown(Path(output_md), report)
    if json_output:
        print(json.dumps(report, ensure_ascii=False))
    return report


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate multi-shift testnet health metrics dashboard")
    parser.add_argument("--logs-dir", default="logs")
    parser.add_argument("--risk-events-jsonl", default="logs/risk_events_scoped_v4.jsonl")
    parser.add_argument("--production-only", action="store_true")
    parser.add_argument("--clean-window", action="store_true")
    parser.add_argument("--ignore-expected-safety-rejections", default="true")
    parser.add_argument("--include-test-events", default="false")
    parser.add_argument("--include-expected-blocks", default="false")
    parser.add_argument("--label", default="")
    parser.add_argument("--since-utc", default="")
    parser.add_argument("--until-utc", default="")
    parser.add_argument("--output-md", default="logs/testnet_shift_metrics.md")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    generate_testnet_shift_metrics(
        logs_dir=str(args.logs_dir or "logs"),
        risk_events_jsonl=str(args.risk_events_jsonl or "logs/risk_events_scoped_v4.jsonl"),
        production_only=bool(args.production_only),
        clean_window=bool(args.clean_window),
        ignore_expected_safety_rejections=_to_bool(args.ignore_expected_safety_rejections, default=True),
        include_test_events=_to_bool(args.include_test_events, default=False),
        include_expected_blocks=_to_bool(args.include_expected_blocks, default=False),
        label=str(args.label or ""),
        since_utc=str(args.since_utc or ""),
        until_utc=str(args.until_utc or ""),
        output_md=str(args.output_md or "logs/testnet_shift_metrics.md"),
        json_output=bool(args.json),
    )


if __name__ == "__main__":
    main()
