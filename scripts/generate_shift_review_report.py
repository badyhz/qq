from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.execution_candidate_queue import apply_candidate_scoring
from core.trade_logger import read_jsonl_rows
from scripts.generate_daily_observation_summary import generate_daily_observation_summary
from scripts.shift_review_report_common import (
    build_shift_report_payload,
    compute_shift_review_verdict,
    map_shift_next_actions,
    render_shift_report_markdown,
)
from scripts.validate_testnet_artifacts import validate_testnet_artifacts


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


def _parse_date(date: str) -> str:
    text = str(date or "").strip()
    if text:
        return text
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _latest_snapshot_json(root: Path) -> Path | None:
    if not root.exists():
        return None
    candidates = [path / "state.json" for path in root.glob("*") if (path / "state.json").exists()]
    if not candidates:
        return None
    return max(candidates, key=lambda item: item.stat().st_mtime)


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if isinstance(payload, dict):
        return payload
    return {}


def _summarize_candidates(candidates_jsonl: str, target_date: str) -> dict[str, int]:
    rows = read_jsonl_rows(candidates_jsonl)
    summary = {"pending": 0, "approved": 0, "submitted": 0, "skipped": 0, "submit_failed": 0}
    for row in rows:
        ts = _parse_dt(row.get("updated_at_utc", "") or row.get("ts_utc", ""))
        if ts is None or ts.strftime("%Y-%m-%d") != target_date:
            continue
        status = str(row.get("status", "")).strip().lower()
        if status in summary:
            summary[status] += 1
    return summary


def _candidate_quality_summary(candidates_jsonl: str) -> dict[str, int]:
    rows = apply_candidate_scoring(read_jsonl_rows(candidates_jsonl))
    summary = {"high_count": 0, "medium_count": 0, "low_count": 0, "blocked_count": 0}
    for row in rows:
        label = str(row.get("signal_score_label", "")).strip().upper()
        if label == "HIGH":
            summary["high_count"] += 1
        elif label == "MEDIUM":
            summary["medium_count"] += 1
        elif label == "LOW":
            summary["low_count"] += 1
        elif label == "BLOCKED":
            summary["blocked_count"] += 1
    return summary


def _summarize_latest_approved_run(approved_runs_dir: str, target_date: str) -> dict[str, Any]:
    root = Path(approved_runs_dir)
    if not root.exists():
        return {"run_id": "", "submitted_count": 0, "failed_count": 0, "planned_count": 0}
    latest_payload: dict[str, Any] = {}
    latest_dt = datetime.min.replace(tzinfo=timezone.utc)
    all_runs: list[tuple[datetime, dict[str, Any]]] = []
    for summary_path in root.glob("*/summary.json"):
        payload = _load_json(summary_path)
        ts = _parse_dt(payload.get("completed_at_utc", "") or payload.get("started_at_utc", ""))
        if ts is None:
            ts = datetime.fromtimestamp(summary_path.stat().st_mtime, tz=timezone.utc)
        all_runs.append((ts, payload))
        if ts.strftime("%Y-%m-%d") != target_date:
            continue
        if ts > latest_dt:
            latest_dt = ts
            latest_payload = payload
    # Fallback: if target date has no run records, use the latest run overall.
    if (not latest_payload) and all_runs:
        latest_payload = max(all_runs, key=lambda item: item[0])[1]
    return {
        "run_id": str(latest_payload.get("run_id", "")),
        "submitted_count": int(latest_payload.get("submitted_count", 0) or 0),
        "failed_count": int(latest_payload.get("failed_count", 0) or 0),
        "planned_count": int(latest_payload.get("planned_count", 0) or 0),
        "overall_status": str(latest_payload.get("overall_status", "")),
    }


def _protection_counts(snapshot: dict[str, Any]) -> dict[str, int]:
    summary = {"FLAT_CLEAN": 0, "FULLY_PROTECTED": 0, "ORPHAN_PROTECTION": 0, "PARTIAL_PROTECTED": 0, "NAKED_POSITION": 0, "UNKNOWN": 0}
    for row in list(snapshot.get("per_symbol_state", [])):
        status = str(row.get("protection_status", "UNKNOWN")).strip().upper() or "UNKNOWN"
        if status not in summary:
            status = "UNKNOWN"
        summary[status] += 1
    return summary


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_md(path: Path, report: dict[str, Any]) -> None:
    overview = dict(report.get("shift_overview", {}))
    protection = dict(report.get("protection_review", {}))
    candidate = dict(report.get("candidate_review", {}))
    execution = dict(report.get("execution_review", {}))
    risk = dict(report.get("risk_review", {}))
    artifact = dict(report.get("artifact_review", {}))
    quality = dict(report.get("candidate_quality_summary", {}))
    sections = [
        ("Shift Overview", [f"date: {overview.get('date', '')}", f"env: {overview.get('env', '')}", f"symbols: {','.join(list(overview.get('symbols', [])))}"]),
        (
            "Starting State / Final State",
            [
                f"snapshot_id: {report.get('state_snapshot', {}).get('snapshot_id', '')}",
                f"aggregate_status: {report.get('state_snapshot', {}).get('aggregate_status', '')}",
            ],
        ),
        (
            "Candidate Review",
            [
                f"pending: {candidate.get('pending', 0)}",
                f"approved: {candidate.get('approved', 0)}",
                f"submitted: {candidate.get('submitted', 0)}",
                f"skipped: {candidate.get('skipped', 0)}",
                f"submit_failed: {candidate.get('submit_failed', 0)}",
            ],
        ),
        (
            "Candidate Quality",
            [
                f"high_count: {quality.get('high_count', 0)}",
                f"medium_count: {quality.get('medium_count', 0)}",
                f"low_count: {quality.get('low_count', 0)}",
                f"blocked_count: {quality.get('blocked_count', 0)}",
            ],
        ),
        (
            "Execution Review",
            [
                f"latest_run_id: {execution.get('latest_run_id', '')}",
                f"planned_count: {execution.get('planned_count', 0)}",
                f"submitted_count: {execution.get('submitted_count', 0)}",
                f"failed_count: {execution.get('failed_count', 0)}",
            ],
        ),
        (
            "Protection Review",
            [
                f"FLAT_CLEAN: {protection.get('FLAT_CLEAN', 0)}",
                f"FULLY_PROTECTED: {protection.get('FULLY_PROTECTED', 0)}",
                f"ORPHAN_PROTECTION: {protection.get('ORPHAN_PROTECTION', 0)}",
                f"PARTIAL_PROTECTED: {protection.get('PARTIAL_PROTECTED', 0)}",
                f"NAKED_POSITION: {protection.get('NAKED_POSITION', 0)}",
            ],
        ),
        (
            "Risk Review",
            [
                f"non_expected_critical_count: {risk.get('non_expected_critical_count', 0)}",
                f"non_expected_error_count: {risk.get('non_expected_error_count', 0)}",
                f"non_expected_warning_count: {risk.get('non_expected_warning_count', 0)}",
                f"expected_safety_rejection_count: {risk.get('expected_safety_rejection_count', 0)}",
                f"latest_critical: {json.dumps(risk.get('latest_critical', {}), ensure_ascii=False)}",
                f"latest_error: {json.dumps(risk.get('latest_error', {}), ensure_ascii=False)}",
            ],
        ),
        (
            "Artifact Review",
            [
                f"ok: {artifact.get('ok', False)}",
                f"missing_files: {len(list(artifact.get('missing_files', [])))}",
                f"optional_missing_files: {len(list(artifact.get('optional_missing_files', [])))}",
            ],
        ),
    ]
    markdown = render_shift_report_markdown(
        title="Shift Review Report",
        sections=sections,
        verdict=str(report.get("verdict", "")),
        verdict_reason=str(report.get("verdict_reason", "")),
        next_actions=list(report.get("next_actions", [])),
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown, encoding="utf-8")


def generate_shift_review_report(
    *,
    date: str = "",
    state_snapshot_dir: str = "logs/testnet_state_snapshots",
    state_snapshot_json: str = "",
    daily_summary_md: str = "",
    risk_events_jsonl: str = "logs/risk_events_scoped_v4.jsonl",
    candidates_jsonl: str = "logs/execution_candidates.jsonl",
    approved_runs_dir: str = "logs/approved_candidate_runs",
    output_md: str = "",
) -> dict[str, Any]:
    target_date = _parse_date(date)
    logs_dir = str(Path(approved_runs_dir).parent)

    snapshot_path: Path | None = None
    if state_snapshot_json:
        snapshot_path = Path(state_snapshot_json)
    else:
        root = Path(state_snapshot_dir)
        if root.is_dir() and (root / "state.json").exists():
            snapshot_path = root / "state.json"
        elif root.name == "latest":
            snapshot_path = _latest_snapshot_json(root.parent)
        else:
            snapshot_path = _latest_snapshot_json(root)
    snapshot = _load_json(snapshot_path) if snapshot_path is not None and snapshot_path.exists() else {}

    resolved_daily_summary_md = daily_summary_md or f"logs/daily_summary_{target_date}.md"
    daily_summary = generate_daily_observation_summary(
        date=target_date,
        risk_events_jsonl=risk_events_jsonl,
        candidates_jsonl=candidates_jsonl,
        approved_runs_dir=approved_runs_dir,
        output_md=resolved_daily_summary_md,
        production_only=True,
    )

    artifact_summary = validate_testnet_artifacts(logs_dir=logs_dir, date=target_date, strict=False)
    candidate_summary = _summarize_candidates(candidates_jsonl, target_date)
    candidate_quality = _candidate_quality_summary(candidates_jsonl)
    latest_run = _summarize_latest_approved_run(approved_runs_dir, target_date)
    protection_summary = _protection_counts(snapshot)
    risk_review = {
        "non_expected_critical_count": int(daily_summary.get("risk_events", {}).get("non_expected_critical_count", 0)),
        "non_expected_error_count": int(daily_summary.get("risk_events", {}).get("non_expected_error_count", 0)),
        "non_expected_warning_count": int(daily_summary.get("risk_events", {}).get("non_expected_warning_count", 0)),
        "expected_safety_rejection_count": int(daily_summary.get("risk_events", {}).get("expected_safety_rejection_count", 0)),
        "latest_critical": dict(daily_summary.get("risk_events", {}).get("latest_critical", {})),
        "latest_error": dict(daily_summary.get("risk_events", {}).get("latest_error", {})),
    }
    verdict, reason = compute_shift_review_verdict(
        snapshot_level=str(snapshot.get("aggregate_status", "UNKNOWN")),
        daily_level=str(daily_summary.get("verdict", "")),
        artifact_ok=bool(artifact_summary.get("ok", False)),
        required_missing_count=len(list(artifact_summary.get("missing_files", []))),
        optional_missing_count=len(list(artifact_summary.get("optional_missing_files", []))),
        latest_is_noop=bool(artifact_summary.get("latest_approved_run_is_noop", False)),
        open_queue_count=int(candidate_summary.get("pending", 0)) + int(candidate_summary.get("approved", 0)),
        fail_count=int(candidate_summary.get("submit_failed", 0)),
        run_failed_count=int(latest_run.get("failed_count", 0)),
        run_done_count=int(latest_run.get("submitted_count", 0)),
        major_count=int(daily_summary.get("risk_events", {}).get("non_expected_critical_count", 0)),
        minor_count=int(daily_summary.get("risk_events", {}).get("non_expected_error_count", 0)),
        low_count=int(daily_summary.get("risk_events", {}).get("non_expected_warning_count", 0)),
    )
    actions = map_shift_next_actions(
        verdict=verdict,
        snapshot_level=str(snapshot.get("aggregate_status", "UNKNOWN")),
        open_queue_count=int(candidate_summary.get("pending", 0)) + int(candidate_summary.get("approved", 0)),
    )

    run_id = datetime.now(timezone.utc).strftime("shift_review_%Y%m%d_%H%M%S")
    resolved_output_md = output_md or f"logs/shift_reviews/{run_id}.md"
    output_md_path = Path(resolved_output_md)
    output_json_path = output_md_path.with_suffix(".json")

    report = build_shift_report_payload(
        overview={
            "date": target_date,
            "env": str(snapshot.get("env", "testnet")),
            "symbols": list(snapshot.get("symbols", [])),
        },
        state_snapshot=snapshot,
        queue_review=candidate_summary,
        quality_review=candidate_quality,
        run_review={
            "latest_run_id": str(latest_run.get("run_id", "")),
            "planned_count": int(latest_run.get("planned_count", 0)),
            "submitted_count": int(latest_run.get("submitted_count", 0)),
            "failed_count": int(latest_run.get("failed_count", 0)),
        },
        state_review=protection_summary,
        event_review=risk_review,
        file_review=artifact_summary,
        daily_level=str(daily_summary.get("verdict", "")),
        daily_reason=str(daily_summary.get("verdict_reason", "")),
        verdict=verdict,
        verdict_reason=reason,
        next_actions=actions,
        output_md=str(output_md_path),
        output_json=str(output_json_path),
    )
    _write_json(output_json_path, report)
    _write_md(output_md_path, report)
    return report


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate a no-trade shift review report from snapshots and logs")
    parser.add_argument("--date", default="")
    parser.add_argument("--state-snapshot-dir", default="logs/testnet_state_snapshots/latest")
    parser.add_argument("--state-snapshot-json", default="")
    parser.add_argument("--daily-summary-md", default="")
    parser.add_argument("--risk-events-jsonl", default="logs/risk_events_scoped_v4.jsonl")
    parser.add_argument("--candidates-jsonl", default="logs/execution_candidates.jsonl")
    parser.add_argument("--approved-runs-dir", default="logs/approved_candidate_runs")
    parser.add_argument("--output-md", default="")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    report = generate_shift_review_report(
        date=str(args.date or ""),
        state_snapshot_dir=str(args.state_snapshot_dir or "logs/testnet_state_snapshots/latest"),
        state_snapshot_json=str(args.state_snapshot_json or ""),
        daily_summary_md=str(args.daily_summary_md or ""),
        risk_events_jsonl=str(args.risk_events_jsonl or "logs/risk_events_scoped_v4.jsonl"),
        candidates_jsonl=str(args.candidates_jsonl or "logs/execution_candidates.jsonl"),
        approved_runs_dir=str(args.approved_runs_dir or "logs/approved_candidate_runs"),
        output_md=str(args.output_md or ""),
    )
    if bool(args.json):
        print(json.dumps(report, ensure_ascii=False))
        return
    print(f"verdict={report.get('verdict', '')}")
    print(f"output_md={report.get('output_md', '')}")
    print(f"output_json={report.get('output_json', '')}")


if __name__ == "__main__":
    main()
