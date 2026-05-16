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


def _in_date_range(value: Any, start_dt: datetime | None, end_dt: datetime | None) -> bool:
    dt = _parse_dt(value)
    if dt is None:
        return False
    if start_dt is not None and dt.date() < start_dt.date():
        return False
    if end_dt is not None and dt.date() > end_dt.date():
        return False
    return True


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _summarize_day_close(root: Path, start_dt: datetime | None, end_dt: datetime | None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    summary = {
        "days_total": 0,
        "pass_days": 0,
        "partial_days": 0,
        "fail_days": 0,
        "latest_day_verdict": "",
    }
    rows: list[dict[str, Any]] = []
    for path in root.glob("trading_day_close_*.json"):
        payload = _load_json(path)
        day = str(payload.get("date", "")).strip()
        if not day:
            continue
        try:
            day_dt = datetime.fromisoformat(f"{day}T00:00:00+00:00")
        except ValueError:
            continue
        if start_dt is not None and day_dt.date() < start_dt.date():
            continue
        if end_dt is not None and day_dt.date() > end_dt.date():
            continue
        rows.append(payload)

    rows.sort(key=lambda row: str(row.get("date", "")))
    summary["days_total"] = len(rows)
    for row in rows:
        verdict = str(row.get("final_verdict", row.get("verdict", ""))).strip().upper()
        if verdict == "PASS":
            summary["pass_days"] += 1
        elif verdict == "PARTIAL":
            summary["partial_days"] += 1
        elif verdict == "FAIL":
            summary["fail_days"] += 1
    if rows:
        summary["latest_day_verdict"] = str(rows[-1].get("final_verdict", rows[-1].get("verdict", "")))
    return summary, rows


def _summarize_execution(root: Path, start_dt: datetime | None, end_dt: datetime | None) -> dict[str, Any]:
    total_submitted = 0
    total_failed = 0
    total_planned = 0
    protective_true = 0
    notional_values: list[float] = []
    for path in (root / "approved_candidate_runs").glob("*/summary.json"):
        payload = _load_json(path)
        ts = payload.get("completed_at_utc", "") or payload.get("started_at_utc", "")
        if ts and (not _in_date_range(ts, start_dt, end_dt)):
            continue
        total_submitted += int(payload.get("submitted_count", 0) or 0)
        total_failed += int(payload.get("failed_count", 0) or 0)
        total_planned += int(payload.get("planned_count", 0) or 0)
        run_dir = path.parent / "batch"
        for submit_path in run_dir.glob("*_submit.jsonl"):
            for row in [item for item in read_jsonl_rows(str(submit_path)) if isinstance(item, dict)]:
                if bool(row.get("protective_orders_submitted", False)):
                    protective_true += 1
                notional_values.append(float(row.get("notional_usdt", 0.0) or 0.0))
    submit_success_rate = (total_submitted / total_planned) if total_planned > 0 else 0.0
    protective_rate = (protective_true / total_submitted) if total_submitted > 0 else 0.0
    return {
        "total_submitted_count": total_submitted,
        "total_failed_count": total_failed,
        "submit_success_rate": round(submit_success_rate, 6),
        "total_protective_orders_submitted": protective_true,
        "protective_order_success_rate": round(protective_rate, 6),
        "avg_notional_usdt": round(sum(notional_values) / len(notional_values), 8) if notional_values else 0.0,
        "max_notional_usdt": round(max(notional_values), 8) if notional_values else 0.0,
    }


def _summarize_candidates(candidates_jsonl: Path) -> dict[str, Any]:
    rows = [row for row in read_jsonl_rows(str(candidates_jsonl)) if isinstance(row, dict)]
    counts = {
        "generated_total": len(rows),
        "submitted_total": 0,
        "rejected_total": 0,
        "expired_total": 0,
        "pending_total": 0,
    }
    for row in rows:
        status = str(row.get("status", "")).strip().upper()
        if status == "SUBMITTED":
            counts["submitted_total"] += 1
        elif status == "REJECTED":
            counts["rejected_total"] += 1
        elif status == "EXPIRED":
            counts["expired_total"] += 1
        elif status in {"PENDING", "APPROVED"}:
            counts["pending_total"] += 1
    counts["duplicate_candidate_id_count"] = len(find_duplicate_candidate_ids(rows))
    return counts


def _summarize_risk(risk_jsonl: Path, start_dt: datetime | None, end_dt: datetime | None) -> dict[str, Any]:
    non_expected_critical = 0
    non_expected_error = 0
    non_expected_warning = 0
    expected_safety = 0
    for row in [item for item in read_jsonl_rows(str(risk_jsonl)) if isinstance(item, dict)]:
        ts = _parse_dt(row.get("ts_utc", ""))
        if ts is None:
            continue
        if start_dt is not None and ts.date() < start_dt.date():
            continue
        if end_dt is not None and ts.date() > end_dt.date():
            continue
        scope = str(row.get("event_scope", "UNKNOWN")).strip().upper()
        is_test_event = bool(row.get("is_test_event", False))
        if scope not in {"TESTNET_REAL", "PRODUCTION_LIKE"} or is_test_event:
            continue
        if is_expected_safety_rejection(row):
            expected_safety += 1
            continue
        severity = str(row.get("severity", "")).strip().upper()
        if severity == "CRITICAL":
            non_expected_critical += 1
        elif severity == "ERROR":
            non_expected_error += 1
        elif severity == "WARNING":
            non_expected_warning += 1
    return {
        "non_expected_critical_count": non_expected_critical,
        "non_expected_error_count": non_expected_error,
        "non_expected_warning_count": non_expected_warning,
        "expected_safety_rejection_count": expected_safety,
    }


def _summarize_outcomes(root: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for path in root.glob("protection_trigger_review_*.json"):
        payload = _load_json(path)
        if payload:
            rows.append(payload)
    for path in root.glob("protection_trigger_review_*.md"):
        payload = _parse_trigger_review_md(path)
        if payload:
            rows.append(payload)

    counts = {
        "still_open_count": 0,
        "take_profit_triggered_count": 0,
        "stop_loss_triggered_count": 0,
        "manual_close_count": 0,
        "unknown_exit_count": 0,
        "orphan_after_close_count": 0,
        "total_pnl_estimate_usdt": 0.0,
        "avg_pnl_pct_estimate": 0.0,
        "winning_outcome_count": 0,
        "losing_outcome_count": 0,
        "outcome_sample_count": 0,
    }
    pnl_pct_values: list[float] = []
    for row in rows:
        outcome = str(row.get("outcome", "")).strip().upper()
        counts["outcome_sample_count"] += 1
        if outcome == "STILL_OPEN":
            counts["still_open_count"] += 1
        elif outcome == "TAKE_PROFIT_TRIGGERED":
            counts["take_profit_triggered_count"] += 1
        elif outcome == "STOP_LOSS_TRIGGERED":
            counts["stop_loss_triggered_count"] += 1
        elif outcome == "MANUAL_FLATTENED":
            counts["manual_close_count"] += 1
        elif outcome in {"UNKNOWN", "EXTERNAL_CLOSED"}:
            counts["unknown_exit_count"] += 1
        if bool(row.get("orphan_after_close", False)):
            counts["orphan_after_close_count"] += 1

        pnl_usdt = _to_float(row.get("pnl_estimate_usdt", 0.0), 0.0)
        pnl_pct = _to_float(row.get("pnl_pct_estimate", 0.0), 0.0)
        entry = _to_float(row.get("entry_price", 0.0), 0.0)
        exit_price = _to_float(row.get("exit_price", 0.0), 0.0)
        qty = abs(_to_float(row.get("position_qty", row.get("quantity", 0.0)), 0.0))
        if abs(pnl_usdt) <= 0 and entry > 0 and exit_price > 0 and qty > 0:
            pnl_usdt = (exit_price - entry) * qty
        if abs(pnl_pct) <= 0 and entry > 0 and exit_price > 0:
            pnl_pct = (exit_price - entry) / entry * 100.0
        counts["total_pnl_estimate_usdt"] += pnl_usdt
        if pnl_pct != 0:
            pnl_pct_values.append(pnl_pct)
        if pnl_usdt > 0:
            counts["winning_outcome_count"] += 1
        elif pnl_usdt < 0:
            counts["losing_outcome_count"] += 1

    counts["total_pnl_estimate_usdt"] = round(counts["total_pnl_estimate_usdt"], 8)
    counts["avg_pnl_pct_estimate"] = round(sum(pnl_pct_values) / len(pnl_pct_values), 8) if pnl_pct_values else 0.0
    return counts


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _parse_trigger_review_md(path: Path) -> dict[str, Any]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return {}
    values: dict[str, Any] = {}
    for line in lines:
        text = line.strip()
        if not text.startswith("- "):
            continue
        body = text[2:]
        if ":" not in body:
            continue
        key, raw = body.split(":", 1)
        values[key.strip()] = raw.strip()
    if "outcome" not in values:
        return {}
    return {
        "symbol": values.get("symbol", ""),
        "outcome": values.get("outcome", ""),
        "orphan_after_close": str(values.get("orphan_after_close", "")).strip().lower() == "true",
        "entry_price": _to_float(values.get("entry_price", 0.0), 0.0),
        "exit_price": _to_float(values.get("exit_price", 0.0), 0.0),
        "position_qty": _to_float(values.get("position_qty", 0.0), 0.0),
        "pnl_estimate_usdt": _to_float(values.get("pnl_estimate_usdt", 0.0), 0.0),
        "pnl_pct_estimate": _to_float(values.get("pnl_pct_estimate", 0.0), 0.0),
    }


def _has_naked_or_partial(day_rows: list[dict[str, Any]]) -> bool:
    for row in day_rows:
        final_state = dict(row.get("final_account_state", {}))
        if list(final_state.get("NAKED_POSITION", [])) or list(final_state.get("PARTIAL_PROTECTED", [])):
            return True
    return False


def _verdict(
    *,
    day_close: dict[str, Any],
    execution: dict[str, Any],
    outcomes: dict[str, Any],
    candidates: dict[str, Any],
    risk: dict[str, Any],
    has_naked_or_partial: bool,
) -> tuple[str, str]:
    if int(day_close.get("fail_days", 0)) > 0:
        return "FAIL", "fail_day_present"
    if int(execution.get("total_failed_count", 0)) > 0:
        return "FAIL", "submit_failed_present"
    if has_naked_or_partial:
        return "FAIL", "naked_or_partial_state_present"
    if int(candidates.get("duplicate_candidate_id_count", 0)) > 0:
        return "FAIL", "duplicate_candidate_id_present"
    if int(risk.get("non_expected_critical_count", 0)) > 0 or int(risk.get("non_expected_error_count", 0)) > 0:
        return "FAIL", "non_expected_critical_or_error_present"
    if int(outcomes.get("orphan_after_close_count", 0)) > 0:
        return "PARTIAL", "orphan_after_close_present"
    if int(outcomes.get("unknown_exit_count", 0)) > 0:
        return "PARTIAL", "unknown_outcomes_present"
    if int(candidates.get("pending_total", 0)) > 0:
        return "PARTIAL", "pending_candidates_present"
    if int(outcomes.get("still_open_count", 0)) > 0:
        return "PARTIAL", "still_open_positions_present"
    if int(day_close.get("days_total", 0)) == 0:
        return "PARTIAL", "no_data"
    return "PASS", "stable_multi_day_execution"


def _write_md(path: Path, report: dict[str, Any]) -> None:
    lines = [
        "# Multi-Day Performance Report",
        "",
        f"- final_verdict: {report.get('final_verdict', '')}",
        f"- verdict_reason: {report.get('verdict_reason', '')}",
        f"- start_date: {report.get('start_date', '')}",
        f"- end_date: {report.get('end_date', '')}",
        "",
        "## Day Close",
    ]
    for key, value in dict(report.get("day_close", {})).items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Execution"])
    for key, value in dict(report.get("execution", {})).items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Outcomes"])
    for key, value in dict(report.get("outcome_summary", {})).items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Candidates"])
    for key, value in dict(report.get("candidates", {})).items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Risk"])
    for key, value in dict(report.get("risk", {})).items():
        lines.append(f"- {key}: {value}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def generate_multi_day_performance_report(
    *,
    logs_dir: str = "logs",
    start_date: str = "",
    end_date: str = "",
    output_md: str = "logs/multi_day_performance_report.md",
) -> dict[str, Any]:
    root = Path(logs_dir)
    start_dt = _parse_dt(f"{start_date}T00:00:00+00:00") if str(start_date or "").strip() else None
    end_dt = _parse_dt(f"{end_date}T23:59:59+00:00") if str(end_date or "").strip() else None

    day_close, day_rows = _summarize_day_close(root, start_dt, end_dt)
    execution = _summarize_execution(root, start_dt, end_dt)
    outcomes = _summarize_outcomes(root)
    candidates = _summarize_candidates(root / "execution_candidates.jsonl")
    risk = _summarize_risk(root / "risk_events_scoped_v4.jsonl", start_dt, end_dt)
    has_naked_or_partial = _has_naked_or_partial(day_rows)
    final_verdict, verdict_reason = _verdict(
        day_close=day_close,
        execution=execution,
        outcomes=outcomes,
        candidates=candidates,
        risk=risk,
        has_naked_or_partial=has_naked_or_partial,
    )

    report = {
        "ok": final_verdict != "FAIL",
        "logs_dir": str(root),
        "start_date": str(start_date or ""),
        "end_date": str(end_date or ""),
        "day_close": day_close,
        "execution": execution,
        "outcomes": outcomes,
        "outcome_summary": outcomes,
        "candidates": candidates,
        "risk": risk,
        "final_verdict": final_verdict,
        "verdict_reason": verdict_reason,
        "output_md": output_md,
        "output_json": str(Path(output_md).with_suffix(".json")),
    }
    output_json = Path(report["output_json"])
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_md(Path(output_md), report)
    return report


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate multi-day testnet performance report from logs")
    parser.add_argument("--logs-dir", default="logs")
    parser.add_argument("--start-date", default="")
    parser.add_argument("--end-date", default="")
    parser.add_argument("--output-md", default="logs/multi_day_performance_report.md")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    report = generate_multi_day_performance_report(
        logs_dir=str(args.logs_dir or "logs"),
        start_date=str(args.start_date or ""),
        end_date=str(args.end_date or ""),
        output_md=str(args.output_md or "logs/multi_day_performance_report.md"),
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
