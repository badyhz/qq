from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.execution_candidate_queue import find_duplicate_candidate_ids
from core.trade_logger import read_jsonl_rows
from scripts.check_account_risk_guard import check_account_risk_guard
from scripts.check_protection_health import check_protection_health
from scripts.diagnose_post_close_orphans import diagnose_post_close_orphans
from scripts.generate_daily_observation_summary import generate_daily_observation_summary
from scripts.trading_day_close_report_common import (
    build_day_close_report_payload,
    compute_day_close_verdict,
    map_day_close_next_actions,
    render_day_close_markdown,
)
from scripts.validate_testnet_artifacts import validate_testnet_artifacts


TERMINAL_STATUSES = {"SUBMITTED", "REJECTED", "EXPIRED", "SKIPPED", "SUBMIT_FAILED"}


def _parse_symbols(value: str) -> list[str]:
    return [item.strip().upper() for item in str(value or "").split(",") if item.strip()]


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


def _same_date(value: Any, target_date: str) -> bool:
    dt = _parse_dt(value)
    if dt is None:
        return False
    return dt.strftime("%Y-%m-%d") == target_date


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _latest_snapshot(logs_dir: Path) -> dict[str, Any]:
    root = logs_dir / "testnet_state_snapshots"
    if not root.exists():
        return {}
    state_files = list(root.glob("*/state.json"))
    if not state_files:
        return {}
    latest = max(state_files, key=lambda path: path.stat().st_mtime)
    return _load_json(latest)


def _latest_shift_review(logs_dir: Path) -> dict[str, Any]:
    root = logs_dir / "shift_reviews"
    if not root.exists():
        return {}
    report_files = list(root.glob("*.json"))
    if not report_files:
        return {}
    latest = max(report_files, key=lambda path: path.stat().st_mtime)
    return _load_json(latest)


def _summarize_candidates(candidates_jsonl: str) -> dict[str, Any]:
    rows = [row for row in read_jsonl_rows(candidates_jsonl) if isinstance(row, dict)]
    counts = {
        "total": len(rows),
        "pending": 0,
        "approved": 0,
        "submitted": 0,
        "rejected": 0,
        "expired": 0,
        "skipped": 0,
        "submit_failed": 0,
    }
    for row in rows:
        status = str(row.get("status", "")).strip().lower()
        if status in counts:
            counts[status] += 1
    duplicates = find_duplicate_candidate_ids(rows)
    counts["duplicate_candidate_id_count"] = len(duplicates)
    return counts


def _summarize_runs(approved_runs_dir: str, target_date: str) -> dict[str, Any]:
    root = Path(approved_runs_dir)
    summary = {
        "approved_runs_count": 0,
        "submitted_count": 0,
        "failed_count": 0,
        "latest_run_id": "",
        "protective_orders_submitted_count": 0,
        "exchange_order_ids": [],
    }
    if not root.exists():
        return summary

    latest_dt = datetime.min.replace(tzinfo=timezone.utc)
    latest_payload: dict[str, Any] = {}
    for path in root.glob("*/summary.json"):
        payload = _load_json(path)
        completed_at = payload.get("completed_at_utc", "") or payload.get("started_at_utc", "")
        if completed_at and (not _same_date(completed_at, target_date)):
            continue
        summary["approved_runs_count"] += 1
        summary["submitted_count"] += int(payload.get("submitted_count", 0) or 0)
        summary["failed_count"] += int(payload.get("failed_count", 0) or 0)
        dt = _parse_dt(completed_at) or datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        if dt > latest_dt:
            latest_dt = dt
            latest_payload = payload

    if latest_payload:
        summary["latest_run_id"] = str(latest_payload.get("run_id", ""))
        details = [row for row in list(latest_payload.get("submit_details", [])) if isinstance(row, dict)]
        summary["exchange_order_ids"] = [str(row.get("exchange_order_id", "")) for row in details if str(row.get("exchange_order_id", ""))]
        summary["protective_orders_submitted_count"] = sum(
            1 for row in details if bool(row.get("protective_orders_submitted", False))
        )
    return summary


def _states_from_snapshot(snapshot: dict[str, Any]) -> dict[str, list[str]]:
    per_symbol = [row for row in list(snapshot.get("per_symbol_state", [])) if isinstance(row, dict)]
    states = {
        "FLAT_CLEAN": [],
        "FULLY_PROTECTED": [],
        "ORPHAN_PROTECTION": [],
        "PARTIAL_PROTECTED": [],
        "NAKED_POSITION": [],
        "UNKNOWN": [],
    }
    for row in per_symbol:
        symbol = str(row.get("symbol", "")).strip().upper()
        status = str(row.get("protection_status", "UNKNOWN")).strip().upper() or "UNKNOWN"
        if status not in states:
            status = "UNKNOWN"
        states[status].append(symbol)
    return states


def _write_md(path: Path, summary: dict[str, Any]) -> None:
    states = dict(summary.get("final_account_state", {}))
    execution = dict(summary.get("execution_summary", {}))
    candidates = dict(summary.get("candidate_summary", {}))
    protection = dict(summary.get("protection_summary", {}))
    risk_guard = dict(summary.get("risk_guard_summary", {}))
    risk_events = dict(summary.get("risk_events_summary", {}))
    artifacts = dict(summary.get("artifacts_summary", {}))
    sections: list[tuple[str, list[str]]] = [
        (
            "Final Account State",
            [
                f"FLAT_CLEAN: {json.dumps(states.get('FLAT_CLEAN', []), ensure_ascii=False)}",
                f"FULLY_PROTECTED: {json.dumps(states.get('FULLY_PROTECTED', []), ensure_ascii=False)}",
                f"ORPHAN_PROTECTION: {json.dumps(states.get('ORPHAN_PROTECTION', []), ensure_ascii=False)}",
                f"PARTIAL_PROTECTED: {json.dumps(states.get('PARTIAL_PROTECTED', []), ensure_ascii=False)}",
                f"NAKED_POSITION: {json.dumps(states.get('NAKED_POSITION', []), ensure_ascii=False)}",
            ],
        ),
        (
            "Execution Summary",
            [
                f"approved_runs_count: {execution.get('approved_runs_count', 0)}",
                f"submitted_count: {execution.get('submitted_count', 0)}",
                f"failed_count: {execution.get('failed_count', 0)}",
                f"latest_run_id: {execution.get('latest_run_id', '')}",
                f"exchange_order_ids: {json.dumps(execution.get('exchange_order_ids', []), ensure_ascii=False)}",
                f"protective_orders_submitted_count: {execution.get('protective_orders_submitted_count', 0)}",
            ],
        ),
        (
            "Candidate Summary",
            [
                f"pending: {candidates.get('pending', 0)}",
                f"approved: {candidates.get('approved', 0)}",
                f"submitted: {candidates.get('submitted', 0)}",
                f"rejected: {candidates.get('rejected', 0)}",
                f"expired: {candidates.get('expired', 0)}",
                f"duplicate_candidate_id_count: {candidates.get('duplicate_candidate_id_count', 0)}",
            ],
        ),
        ("Protection Summary", [f"aggregate_health: {protection.get('aggregate_health', '')}"]),
    ]
    for row in list(protection.get("per_symbol", [])):
        sections[3][1].append(
            f"{row.get('symbol', '')}: {row.get('protection_health', '')} ({row.get('protection_status', '')})"
        )
    sections.extend(
        [
            (
                "Risk Guard Summary",
                [
                    f"allowed: {risk_guard.get('allowed', False)}",
                    f"reason: {risk_guard.get('reason', '')}",
                    f"daily_submitted_count: {risk_guard.get('daily_submitted_count', 0)}",
                    f"max_daily_submits: {risk_guard.get('max_daily_submits', 0)}",
                    f"max_open_positions: {risk_guard.get('max_open_positions', 0)}",
                ],
            ),
            (
                "Risk Events Summary",
                [
                    f"non_expected_critical_count: {risk_events.get('non_expected_critical_count', 0)}",
                    f"non_expected_error_count: {risk_events.get('non_expected_error_count', 0)}",
                    f"non_expected_warning_count: {risk_events.get('non_expected_warning_count', 0)}",
                    f"expected_safety_rejection_count: {risk_events.get('expected_safety_rejection_count', 0)}",
                    f"latest_critical: {json.dumps(risk_events.get('latest_critical', {}), ensure_ascii=False)}",
                    f"latest_error: {json.dumps(risk_events.get('latest_error', {}), ensure_ascii=False)}",
                ],
            ),
            (
                "Artifacts Summary",
                [
                    f"ok: {artifacts.get('ok', False)}",
                    f"missing_files: {json.dumps(artifacts.get('missing_files', []), ensure_ascii=False)}",
                    f"optional_missing_files: {json.dumps(artifacts.get('optional_missing_files', []), ensure_ascii=False)}",
                ],
            ),
        ]
    )
    markdown = render_day_close_markdown(
        title="Trading Day Close Report",
        header_lines=[
            f"date: {summary.get('date', '')}",
            f"env: {summary.get('env', '')}",
            f"symbols: {','.join(list(summary.get('symbols', [])))}",
            f"final_verdict: {summary.get('final_verdict', '')}",
            f"verdict_reason: {summary.get('verdict_reason', '')}",
        ],
        sections=sections,
        next_actions=list(summary.get("next_actions", [])),
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown, encoding="utf-8")


def generate_trading_day_close_report(
    *,
    date: str,
    env: str = "testnet",
    symbols: str = "FETUSDT,OPUSDT",
    logs_dir: str = "logs",
    risk_events_jsonl: str = "logs/risk_events_scoped_v4.jsonl",
    candidates_jsonl: str = "logs/execution_candidates.jsonl",
    output_md: str = "",
    base_url: str = "",
) -> dict[str, Any]:
    target_date = str(date or "").strip() or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    resolved_env = str(env or "").strip().lower()
    symbol_list = _parse_symbols(symbols)
    root = Path(logs_dir)
    resolved_output_md = output_md or f"logs/trading_day_close_{target_date}.md"
    output_json = str(Path(resolved_output_md).with_suffix(".json"))

    snapshot = _latest_snapshot(root)
    if not snapshot:
        # Fallback to current read-only snapshot if archive missing.
        from scripts.archive_testnet_state_snapshot import archive_testnet_state_snapshot  # local import to avoid cycle

        snapshot = archive_testnet_state_snapshot(env=resolved_env, symbols=",".join(symbol_list), base_url=base_url)
    states = _states_from_snapshot(snapshot)
    shift_review = _latest_shift_review(root)

    daily_summary = generate_daily_observation_summary(
        date=target_date,
        risk_events_jsonl=risk_events_jsonl,
        candidates_jsonl=candidates_jsonl,
        approved_runs_dir=str(root / "approved_candidate_runs"),
        output_md=f"logs/daily_summary_{target_date}.md",
        production_only=True,
        clean_window=True,
        since_utc=f"{target_date}T00:00:00+00:00",
    )
    risk_summary = dict(daily_summary.get("risk_events", {}))

    protection_summary = check_protection_health(
        env=resolved_env,
        symbols=",".join(symbol_list),
        output_md="logs/protection_health_report.md",
        base_url=base_url,
        log_risk_events=False,
    )
    orphan_diag = diagnose_post_close_orphans(
        env=resolved_env,
        symbols=",".join(symbol_list),
        output_md="logs/post_close_orphan_diagnosis.md",
        base_url=base_url,
    )
    candidate_summary = _summarize_candidates(candidates_jsonl)
    run_summary = _summarize_runs(str(root / "approved_candidate_runs"), target_date)
    artifact_summary = validate_testnet_artifacts(logs_dir=str(root), date=target_date, strict=False)
    guard = check_account_risk_guard(
        env=resolved_env,
        symbols=",".join(symbol_list),
        target_symbol=symbol_list[-1] if symbol_list else "",
        target_notional_usdt=50.0,
        candidates_jsonl=candidates_jsonl,
        approved_runs_dir=str(root / "approved_candidate_runs"),
        config="config.yaml",
    )
    guard_checks = dict(guard.get("checks", {}))
    risk_guard_summary = {
        "allowed": bool(guard.get("allowed", False)),
        "reason": str(guard.get("reason", "")),
        "severity": str(guard.get("severity", "")),
        "daily_submitted_count": int(guard_checks.get("daily_submitted_count", 0)),
        "max_daily_submits": int(guard_checks.get("max_daily_submits", 0)),
        "max_open_positions": int(guard_checks.get("max_open_positions", 0)),
    }

    final_verdict, verdict_reason = compute_day_close_verdict(
        critical_symbols_count=len(list(states.get("NAKED_POSITION", []))),
        weak_symbols_count=len(list(states.get("PARTIAL_PROTECTED", []))),
        queue_fail_count=int(candidate_summary.get("submit_failed", 0)),
        run_fail_count=int(run_summary.get("failed_count", 0)),
        major_count=int(risk_summary.get("non_expected_critical_count", 0)),
        minor_count=int(risk_summary.get("non_expected_error_count", 0)),
        low_count=int(risk_summary.get("non_expected_warning_count", 0)),
        required_missing_count=len(list(artifact_summary.get("missing_files", []))),
        state_health=str(protection_summary.get("aggregate_health", "")),
        cleanup_needed_count=len(list(states.get("ORPHAN_PROTECTION", []))) + len(list(orphan_diag.get("orphan_symbols", []))),
        open_queue_count=int(candidate_summary.get("pending", 0)) + int(candidate_summary.get("approved", 0)),
    )
    next_actions = map_day_close_next_actions(verdict=final_verdict, reason=verdict_reason)
    if final_verdict == "PASS" and str(shift_review.get("verdict", "")).strip().upper() not in {"", "PASS"}:
        final_verdict = "PARTIAL"
        verdict_reason = "historical_shift_review_not_pass"
        next_actions = map_day_close_next_actions(verdict=final_verdict, reason=verdict_reason)

    report = build_day_close_report_payload(
        ok=final_verdict != "FAIL",
        date=target_date,
        env=resolved_env,
        symbols=symbol_list,
        final_verdict=final_verdict,
        day_summary={
            "date": target_date,
            "env": resolved_env,
            "symbols": symbol_list,
            "final_verdict": final_verdict,
        },
        state_summary=states,
        run_summary=run_summary,
        queue_summary=candidate_summary,
        health_summary={
            "aggregate_health": str(protection_summary.get("aggregate_health", "")),
            "per_symbol": list(protection_summary.get("per_symbol", [])),
        },
        cleanup_summary=orphan_diag,
        guard_summary=risk_guard_summary,
        event_summary={
            "non_expected_critical_count": int(risk_summary.get("non_expected_critical_count", 0)),
            "non_expected_error_count": int(risk_summary.get("non_expected_error_count", 0)),
            "non_expected_warning_count": int(risk_summary.get("non_expected_warning_count", 0)),
            "expected_safety_rejection_count": int(risk_summary.get("expected_safety_rejection_count", 0)),
            "latest_critical": dict(risk_summary.get("latest_critical", {})),
            "latest_error": dict(risk_summary.get("latest_error", {})),
        },
        file_summary={
            "ok": bool(artifact_summary.get("ok", False)),
            "missing_files": list(artifact_summary.get("missing_files", [])),
            "optional_missing_files": list(artifact_summary.get("optional_missing_files", [])),
            "latest_reports_generated": [
                str(daily_summary.get("output_md", "")),
                str(protection_summary.get("output_md", "")),
                str(orphan_diag.get("output_md", "")),
            ],
        },
        latest_snapshot=snapshot,
        latest_shift_review=shift_review,
        daily_level=str(daily_summary.get("verdict", "")),
        daily_reason=str(daily_summary.get("verdict_reason", "")),
        verdict_reason=verdict_reason,
        next_actions=next_actions,
        output_md=resolved_output_md,
        output_json=output_json,
    )
    Path(output_json).parent.mkdir(parents=True, exist_ok=True)
    Path(output_json).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_md(Path(resolved_output_md), report)
    return report


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate trading day close report from testnet artifacts and read-only checks")
    parser.add_argument("--date", default="")
    parser.add_argument("--env", default="testnet")
    parser.add_argument("--symbols", default="FETUSDT,OPUSDT")
    parser.add_argument("--logs-dir", default="logs")
    parser.add_argument("--risk-events-jsonl", default="logs/risk_events_scoped_v4.jsonl")
    parser.add_argument("--candidates-jsonl", default="logs/execution_candidates.jsonl")
    parser.add_argument("--output-md", default="")
    parser.add_argument("--base-url", default="")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    report = generate_trading_day_close_report(
        date=str(args.date or ""),
        env=str(args.env or "testnet"),
        symbols=str(args.symbols or "FETUSDT,OPUSDT"),
        logs_dir=str(args.logs_dir or "logs"),
        risk_events_jsonl=str(args.risk_events_jsonl or "logs/risk_events_scoped_v4.jsonl"),
        candidates_jsonl=str(args.candidates_jsonl or "logs/execution_candidates.jsonl"),
        output_md=str(args.output_md or ""),
        base_url=str(args.base_url or ""),
    )
    if bool(args.json):
        print(json.dumps(report, ensure_ascii=False))
        return
    print(f"final_verdict={report.get('final_verdict', '')}")
    print(f"verdict_reason={report.get('verdict_reason', '')}")
    print(f"output_md={report.get('output_md', '')}")
    print(f"output_json={report.get('output_json', '')}")


if __name__ == "__main__":
    main()
