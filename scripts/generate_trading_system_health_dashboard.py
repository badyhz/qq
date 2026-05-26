from __future__ import annotations

import argparse
import csv
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.execution_guards import (
    ExecutionGuardError,
    assert_dry_run_required,
    normalize_execution_mode,
)


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_csv_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))
    except OSError:
        return []


def _latest_trading_day_close(logs_dir: Path) -> dict[str, Any]:
    latest_path: Path | None = None
    for path in logs_dir.glob("trading_day_close_*.json"):
        if latest_path is None or path.name > latest_path.name:
            latest_path = path
    if latest_path is None:
        return {}
    payload = _load_json(latest_path)
    if payload:
        payload["_source_path"] = str(latest_path)
    return payload


def _build_account_state(latest_day_close: dict[str, Any], multi_day: dict[str, Any]) -> dict[str, Any]:
    pending_count = 0
    approved_count = 0
    position_status = "MISSING"
    orphan_status = "MISSING"

    candidate_summary = latest_day_close.get("candidate_summary", {})
    if isinstance(candidate_summary, dict):
        pending_count = int(candidate_summary.get("pending", candidate_summary.get("pending_total", 0)) or 0)
        approved_count = int(candidate_summary.get("approved", 0) or 0)
    elif isinstance(multi_day.get("candidates", {}), dict):
        pending_count = int(multi_day.get("candidates", {}).get("pending_total", 0) or 0)

    orphan_diagnosis = latest_day_close.get("orphan_diagnosis", {})
    diagnosis_rows = []
    if isinstance(orphan_diagnosis, dict):
        diagnosis_rows = [row for row in list(orphan_diagnosis.get("per_symbol_diagnosis", [])) if isinstance(row, dict)]
    if diagnosis_rows:
        statuses = {str(row.get("diagnosis", "")).strip().upper() for row in diagnosis_rows}
        if "NAKED_POSITION" in statuses:
            position_status = "NAKED_POSITION"
        elif "PARTIAL_PROTECTED" in statuses:
            position_status = "PARTIAL_PROTECTED"
        elif "ORPHAN_PROTECTION" in statuses:
            position_status = "ORPHAN_PROTECTION"
        elif statuses and statuses.issubset({"FLAT_CLEAN"}):
            position_status = "FLAT_CLEAN"
        elif "FULLY_PROTECTED" in statuses:
            position_status = "FULLY_PROTECTED"
    else:
        final_state = latest_day_close.get("final_account_state", {})
        if isinstance(final_state, dict) and final_state:
            naked = len(list(final_state.get("NAKED_POSITION", [])))
            partial = len(list(final_state.get("PARTIAL_PROTECTED", [])))
            orphan = len(list(final_state.get("ORPHAN_PROTECTION", [])))
            fully = len(list(final_state.get("FULLY_PROTECTED", [])))
            if naked > 0:
                position_status = "NAKED_POSITION"
            elif partial > 0:
                position_status = "PARTIAL_PROTECTED"
            elif orphan > 0:
                position_status = "ORPHAN_PROTECTION"
            elif fully > 0:
                position_status = "FULLY_PROTECTED"
            else:
                position_status = "FLAT_CLEAN"

    if isinstance(orphan_diagnosis, dict) and orphan_diagnosis:
        verdict = str(orphan_diagnosis.get("verdict", "")).strip().upper()
        if verdict == "PASS":
            orphan_status = "CLEAN"
        elif verdict in {"PARTIAL", "FAIL"}:
            orphan_status = "UNCLEAN"

    return {
        "position_status": position_status,
        "orphan_status": orphan_status,
        "pending_candidate_count": pending_count,
        "approved_candidate_count": approved_count,
    }


def _build_outcome_summary(multi_day: dict[str, Any], lifecycle_rows: list[dict[str, Any]]) -> dict[str, Any]:
    if isinstance(multi_day.get("outcome_summary", {}), dict) and multi_day.get("outcome_summary"):
        outcome = dict(multi_day.get("outcome_summary", {}))
    elif isinstance(multi_day.get("outcomes", {}), dict) and multi_day.get("outcomes"):
        outcome = dict(multi_day.get("outcomes", {}))
    else:
        outcome = {}

    if outcome:
        return {
            "take_profit_triggered_count": int(outcome.get("take_profit_triggered_count", 0) or 0),
            "stop_loss_triggered_count": int(outcome.get("stop_loss_triggered_count", 0) or 0),
            "manual_close_count": int(outcome.get("manual_close_count", 0) or 0),
            "unknown_exit_count": int(outcome.get("unknown_exit_count", 0) or 0),
            "orphan_after_close_count": int(outcome.get("orphan_after_close_count", 0) or 0),
            "total_pnl_estimate_usdt": round(_to_float(outcome.get("total_pnl_estimate_usdt", 0.0), 0.0), 8),
            "avg_pnl_pct_estimate": round(_to_float(outcome.get("avg_pnl_pct_estimate", 0.0), 0.0), 8),
        }

    tp_count = 0
    sl_count = 0
    manual_count = 0
    unknown_count = 0
    orphan_after_close_count = 0
    pnl_values: list[float] = []
    pnl_pct_values: list[float] = []
    for row in lifecycle_rows:
        outcome_code = str(row.get("outcome", "")).strip().upper()
        if outcome_code == "TAKE_PROFIT_TRIGGERED":
            tp_count += 1
        elif outcome_code == "STOP_LOSS_TRIGGERED":
            sl_count += 1
        elif outcome_code == "MANUAL_FLATTENED":
            manual_count += 1
        elif outcome_code in {"UNKNOWN", "EXTERNAL_CLOSED", ""}:
            unknown_count += 1
        if str(row.get("orphan_after_close", "")).strip().lower() in {"1", "true", "yes", "y"}:
            orphan_after_close_count += 1
        pnl_values.append(_to_float(row.get("pnl_estimate_usdt", 0.0), 0.0))
        pnl_pct_values.append(_to_float(row.get("pnl_pct_estimate", 0.0), 0.0))
    return {
        "take_profit_triggered_count": tp_count,
        "stop_loss_triggered_count": sl_count,
        "manual_close_count": manual_count,
        "unknown_exit_count": unknown_count,
        "orphan_after_close_count": orphan_after_close_count,
        "total_pnl_estimate_usdt": round(sum(pnl_values), 8) if pnl_values else 0.0,
        "avg_pnl_pct_estimate": round(sum(pnl_pct_values) / len(pnl_pct_values), 8) if pnl_pct_values else 0.0,
    }


def _build_lifecycle_summary(lifecycle_rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "trade_count": len(lifecycle_rows),
        "closed_count": sum(1 for row in lifecycle_rows if str(row.get("lifecycle_status", "")).strip().upper() == "CLOSED"),
        "pass_count": sum(1 for row in lifecycle_rows if str(row.get("execution_verdict", "")).strip().upper() == "PASS"),
        "fail_count": sum(1 for row in lifecycle_rows if str(row.get("execution_verdict", "")).strip().upper() == "FAIL"),
    }


def _build_execution_summary(multi_day: dict[str, Any], analysis_summary: dict[str, Any]) -> dict[str, Any]:
    execution = multi_day.get("execution", {}) if isinstance(multi_day.get("execution", {}), dict) else {}
    candidates = multi_day.get("candidates", {}) if isinstance(multi_day.get("candidates", {}), dict) else {}
    return {
        "total_submitted_count": int(execution.get("total_submitted_count", 0) or 0),
        "total_failed_count": int(execution.get("total_failed_count", 0) or 0),
        "protective_order_success_rate": round(_to_float(execution.get("protective_order_success_rate", 0.0), 0.0), 8),
        "duplicate_candidate_id_count": int(candidates.get("duplicate_candidate_id_count", 0) or 0),
        "analysis_trade_count": int(analysis_summary.get("trade_count", 0) or 0),
    }


def _build_quality_summary(quality_summary: dict[str, Any]) -> dict[str, Any]:
    if not quality_summary:
        return {
            "avg_execution_quality_score": 0.0,
            "min_execution_quality_score": 0.0,
            "max_execution_quality_score": 0.0,
            "final_verdict": "MISSING",
            "status": "MISSING",
        }
    return {
        "avg_execution_quality_score": round(_to_float(quality_summary.get("avg_execution_quality_score", 0.0), 0.0), 8),
        "min_execution_quality_score": round(_to_float(quality_summary.get("min_execution_quality_score", 0.0), 0.0), 8),
        "max_execution_quality_score": round(_to_float(quality_summary.get("max_execution_quality_score", 0.0), 0.0), 8),
        "final_verdict": str(quality_summary.get("final_verdict", "")).strip().upper() or "MISSING",
        "status": "OK",
    }


def _build_anomaly_summary(top_anomalies: dict[str, Any]) -> dict[str, Any]:
    severity_counts = top_anomalies.get("severity_counts", {}) if isinstance(top_anomalies.get("severity_counts", {}), dict) else {}
    return {
        "critical_count": int(severity_counts.get("critical_count", 0) or 0),
        "high_count": int(severity_counts.get("high_count", 0) or 0),
        "medium_count": int(severity_counts.get("medium_count", 0) or 0),
        "low_count": int(severity_counts.get("low_count", 0) or 0),
        "status": "OK" if top_anomalies else "MISSING",
    }


def _resolve_next_action(latest_day_close: dict[str, Any], execution_summary: dict[str, Any]) -> str:
    risk_guard = latest_day_close.get("risk_guard_summary", {}) if isinstance(latest_day_close.get("risk_guard_summary", {}), dict) else {}
    reason = str(risk_guard.get("reason", "")).strip().lower()
    if reason == "max_daily_submits_reached":
        return "DO_NOT_SUBMIT_TODAY_MAX_DAILY_SUBMITS_REACHED"
    if reason:
        return f"REVIEW_RISK_GUARD_{reason.upper()}"
    if int(execution_summary.get("total_failed_count", 0) or 0) > 0:
        return "INSPECT_FAILED_SUBMISSIONS_BEFORE_NEXT_SHIFT"
    return "READY_FOR_NEXT_SHIFT_GUARD_CHECK"


def _resolve_final_verdict(
    *,
    anomaly_summary: dict[str, Any],
    outcome_summary: dict[str, Any],
    execution_summary: dict[str, Any],
    quality_summary: dict[str, Any],
    missing_reports: list[str],
) -> str:
    critical_count = int(anomaly_summary.get("critical_count", 0) or 0)
    high_count = int(anomaly_summary.get("high_count", 0) or 0)
    unknown_exit_count = int(outcome_summary.get("unknown_exit_count", 0) or 0)
    total_failed_count = int(execution_summary.get("total_failed_count", 0) or 0)
    avg_quality = _to_float(quality_summary.get("avg_execution_quality_score", 0.0), 0.0)
    quality_present = str(quality_summary.get("status", "")).strip().upper() == "OK"

    # FAIL rules
    if critical_count > 0:
        return "FAIL"
    if int(outcome_summary.get("orphan_after_close_count", 0) or 0) > 0:
        return "FAIL"
    if total_failed_count > 0:
        return "FAIL"
    if quality_present and avg_quality < 75:
        return "FAIL"

    # PARTIAL rules
    if high_count > 0:
        return "PARTIAL"
    if unknown_exit_count > 0:
        return "PARTIAL"
    if missing_reports:
        return "PARTIAL"
    if quality_present and avg_quality < 90:
        return "PARTIAL"
    if not quality_present:
        return "PARTIAL"

    return "PASS"


def generate_trading_system_health_dashboard(
    *,
    logs_dir: str = "logs",
    reports_dir: str = "reports",
    output_dir: str = "reports/system_health",
) -> dict[str, Any]:
    logs_root = Path(logs_dir)
    reports_root = Path(reports_dir)
    out_root = Path(output_dir)
    out_root.mkdir(parents=True, exist_ok=True)

    multi_day_path = logs_root / "multi_day_performance_report.json"
    lifecycle_path = reports_root / "trade_lifecycle" / "trade_lifecycle.csv"
    quality_summary_path = reports_root / "execution_quality" / "execution_quality_summary.json"
    analysis_summary_path = reports_root / "trade_lifecycle_analysis" / "summary.json"
    anomalies_top_path = reports_root / "trade_lifecycle_anomalies" / "top_anomalies.json"

    multi_day = _load_json(multi_day_path)
    lifecycle_rows = _read_csv_rows(lifecycle_path)
    quality_summary_raw = _load_json(quality_summary_path)
    analysis_summary = _load_json(analysis_summary_path)
    anomalies_top = _load_json(anomalies_top_path)
    latest_day_close = _latest_trading_day_close(logs_root)

    missing_reports: list[str] = []
    if not multi_day:
        missing_reports.append(str(multi_day_path))
    if len(lifecycle_rows) == 0 and not lifecycle_path.exists():
        missing_reports.append(str(lifecycle_path))
    if not quality_summary_raw:
        missing_reports.append(str(quality_summary_path))
    if not analysis_summary:
        missing_reports.append(str(analysis_summary_path))
    if not anomalies_top:
        missing_reports.append(str(anomalies_top_path))

    account_state = _build_account_state(latest_day_close, multi_day)
    execution_summary = _build_execution_summary(multi_day, analysis_summary)
    outcome_summary = _build_outcome_summary(multi_day, lifecycle_rows)
    lifecycle_summary = _build_lifecycle_summary(lifecycle_rows)
    quality_summary = _build_quality_summary(quality_summary_raw)
    anomaly_summary = _build_anomaly_summary(anomalies_top)
    next_action = _resolve_next_action(latest_day_close, execution_summary)

    final_verdict = _resolve_final_verdict(
        anomaly_summary=anomaly_summary,
        outcome_summary=outcome_summary,
        execution_summary=execution_summary,
        quality_summary=quality_summary,
        missing_reports=missing_reports,
    )

    dashboard = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "final_verdict": final_verdict,
        "account_state": account_state,
        "execution_summary": execution_summary,
        "outcome_summary": outcome_summary,
        "lifecycle_summary": lifecycle_summary,
        "quality_summary": quality_summary,
        "anomaly_summary": anomaly_summary,
        "next_action": next_action,
        "missing_reports": missing_reports,
        "source_paths": {
            "multi_day_performance_report_json": str(multi_day_path),
            "trade_lifecycle_csv": str(lifecycle_path),
            "execution_quality_summary_json": str(quality_summary_path),
            "trade_lifecycle_analysis_summary_json": str(analysis_summary_path),
            "trade_lifecycle_anomalies_top_json": str(anomalies_top_path),
            "latest_trading_day_close_json": str(latest_day_close.get("_source_path", "")),
        },
    }

    dashboard_path = out_root / "trading_system_health_dashboard.json"
    summary_md_path = out_root / "summary.md"
    dashboard_path.write_text(json.dumps(dashboard, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        "# Trading System Health Dashboard",
        "",
        f"- final_verdict: {dashboard['final_verdict']}",
        f"- next_action: {dashboard['next_action']}",
        f"- missing_report_count: {len(missing_reports)}",
        "",
        f"- total_submitted_count: {execution_summary['total_submitted_count']}",
        f"- total_failed_count: {execution_summary['total_failed_count']}",
        f"- avg_execution_quality_score: {quality_summary['avg_execution_quality_score']}",
        f"- critical_count: {anomaly_summary['critical_count']}",
        f"- high_count: {anomaly_summary['high_count']}",
        "",
        f"- dashboard_json: {dashboard_path}",
    ]
    summary_md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    dashboard["output_json"] = str(dashboard_path)
    dashboard["output_md"] = str(summary_md_path)
    return dashboard


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate machine-readable trading system health dashboard")
    parser.add_argument("--logs-dir", default="logs")
    parser.add_argument("--reports-dir", default="reports")
    parser.add_argument("--output-dir", default="reports/system_health")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    mode = normalize_execution_mode(os.environ.get("QQ_RUNTIME_MODE"))
    assert_dry_run_required(mode)
    result = generate_trading_system_health_dashboard(
        logs_dir=str(args.logs_dir or "logs"),
        reports_dir=str(args.reports_dir or "reports"),
        output_dir=str(args.output_dir or "reports/system_health"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"final_verdict={result.get('final_verdict', '')}")
    print(f"next_action={result.get('next_action', '')}")
    print(f"output_json={result.get('output_json', '')}")


if __name__ == "__main__":
    main()
