from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.strategy_edge_common import read_csv_rows, read_json_file, to_float_nan


FIELDS = [
    "requirement_key",
    "requirement_name",
    "current_value",
    "required_value",
    "gap_value",
    "gap_unit",
    "gap_severity",
    "priority",
    "blocking",
    "remediation_hint",
    "source_report",
]

def _to_float(value: Any, default: float = float("nan")) -> float:
    parsed = to_float_nan(value)
    if not math.isfinite(parsed):
        return float(default)
    return float(parsed)


def _severity_for_gap(gap_value: float, *, is_critical: bool = False) -> str:
    if gap_value <= 0:
        return "NONE"
    if is_critical or gap_value >= 10:
        return "CRITICAL"
    if gap_value >= 3:
        return "HIGH"
    if gap_value >= 1:
        return "MEDIUM"
    return "LOW"


def _build_numeric_gap(
    *,
    requirement_key: str,
    requirement_name: str,
    current_value: float,
    required_value: float,
    gap_unit: str,
    priority: str,
    remediation_hint: str,
    source_report: str,
    critical: bool = False,
) -> dict[str, Any]:
    gap = max(0.0, float(required_value) - float(current_value))
    blocking = gap > 0
    return {
        "requirement_key": requirement_key,
        "requirement_name": requirement_name,
        "current_value": round(current_value, 8),
        "required_value": round(required_value, 8),
        "gap_value": round(gap, 8),
        "gap_unit": gap_unit,
        "gap_severity": _severity_for_gap(gap, is_critical=critical),
        "priority": priority if blocking else "P3",
        "blocking": bool(blocking),
        "remediation_hint": remediation_hint,
        "source_report": source_report,
    }


def _build_bool_gap(
    *,
    requirement_key: str,
    requirement_name: str,
    current_ok: bool,
    priority: str,
    remediation_hint: str,
    source_report: str,
) -> dict[str, Any]:
    gap = 0.0 if current_ok else 1.0
    return {
        "requirement_key": requirement_key,
        "requirement_name": requirement_name,
        "current_value": bool(current_ok),
        "required_value": True,
        "gap_value": gap,
        "gap_unit": "flag",
        "gap_severity": "NONE" if current_ok else "LOW",
        "priority": priority if not current_ok else "P3",
        "blocking": bool(not current_ok),
        "remediation_hint": remediation_hint,
        "source_report": source_report,
    }


def diagnose_testnet_dry_run_readiness_gaps(
    *,
    phase_review_json: str = "reports/testnet_dry_run_phase_review/testnet_dry_run_phase_review.json",
    shadow_research_history_csv: str = "reports/shadow_research_history/shadow_research_history.csv",
    experiment_history_dashboard_json: str = "reports/shadow_experiment_history_dashboard/history_dashboard.json",
    experiment_stability_summary_json: str = "reports/shadow_experiment_stability/summary.json",
    strategy_candidate_score_summary_json: str = "reports/strategy_candidate_score/summary.json",
    daily_shadow_research_control_json: str = "reports/daily_shadow_research_control/daily_shadow_research_control_report.json",
    output_dir: str = "reports/testnet_dry_run_readiness_gaps",
) -> dict[str, Any]:
    phase = read_json_file(Path(phase_review_json))
    history_rows = read_csv_rows(Path(shadow_research_history_csv))
    history_dashboard = read_json_file(Path(experiment_history_dashboard_json))
    stability_summary = read_json_file(Path(experiment_stability_summary_json))
    strategy_summary = read_json_file(Path(strategy_candidate_score_summary_json))
    daily = read_json_file(Path(daily_shadow_research_control_json))

    unique_days = {
        str(row.get("run_date", "")).strip()
        for row in history_rows
        if str(row.get("run_date", "")).strip()
    }
    shadow_research_history_days = float(len(unique_days))
    experiment_total_samples = _to_float(
        history_dashboard.get("history_row_count"),
        _to_float(history_dashboard.get("experiment_count"), 0.0),
    )
    experiment_count = _to_float(stability_summary.get("experiment_count"), 0.0)
    needs_more_data_count = _to_float(stability_summary.get("needs_more_data_count"), 0.0)
    stability_ready_count = max(0.0, experiment_count - needs_more_data_count)
    weighted_sample_count = _to_float(
        strategy_summary.get("avg_weighted_sample_count"),
        _to_float(strategy_summary.get("weighted_sample_count"), 0.0),
    )
    if not math.isfinite(weighted_sample_count):
        weighted_sample_count = 0.0

    minimum = phase.get("minimum_requirements", {})
    system_health_pass = bool(minimum.get("system_health_pass", False))
    no_trade_actions_attempted = bool(minimum.get("no_trade_actions_attempted", False))
    readiness_not_fail = bool(minimum.get("testnet_dry_run_readiness_not_fail", False))
    if not minimum:
        no_trade_actions_attempted = (
            (not bool(daily.get("submit_attempted", False)))
            and (not bool(daily.get("cancel_attempted", False)))
            and (not bool(daily.get("flatten_attempted", False)))
        )

    rows = [
        _build_numeric_gap(
            requirement_key="shadow_research_history_days",
            requirement_name="Shadow research history days",
            current_value=shadow_research_history_days,
            required_value=3.0,
            gap_unit="days",
            priority="P1",
            remediation_hint="Continue daily shadow-only runs until at least 3 unique days are recorded.",
            source_report=shadow_research_history_csv,
        ),
        _build_numeric_gap(
            requirement_key="experiment_total_samples",
            requirement_name="Total experiment samples",
            current_value=experiment_total_samples,
            required_value=20.0,
            gap_unit="samples",
            priority="P0",
            remediation_hint="Run remediation shadow-only loops to increase experiment sample count.",
            source_report=experiment_history_dashboard_json,
            critical=True,
        ),
        _build_numeric_gap(
            requirement_key="stability_ready_count",
            requirement_name="Stability ready experiment count",
            current_value=stability_ready_count,
            required_value=1.0,
            gap_unit="experiments",
            priority="P1",
            remediation_hint="Accumulate more evaluated samples, then recompute stability summary.",
            source_report=experiment_stability_summary_json,
        ),
        _build_numeric_gap(
            requirement_key="strategy_weighted_sample_count",
            requirement_name="Strategy weighted sample count",
            current_value=weighted_sample_count,
            required_value=5.0,
            gap_unit="weighted_samples",
            priority="P1",
            remediation_hint="Collect additional strict/observation shadow samples to lift weighted count.",
            source_report=strategy_candidate_score_summary_json,
        ),
        _build_bool_gap(
            requirement_key="system_health_pass",
            requirement_name="System health PASS",
            current_ok=system_health_pass,
            priority="P2",
            remediation_hint="Keep system health checks green before any phase transition.",
            source_report=phase_review_json,
        ),
        _build_bool_gap(
            requirement_key="no_trade_actions_attempted",
            requirement_name="No submit/cancel/flatten attempts",
            current_ok=no_trade_actions_attempted,
            priority="P2",
            remediation_hint="Ensure all runs stay shadow-only with no trade actions attempted.",
            source_report=daily_shadow_research_control_json,
        ),
        _build_bool_gap(
            requirement_key="testnet_dry_run_readiness_not_fail",
            requirement_name="Testnet dry-run readiness report not FAIL",
            current_ok=readiness_not_fail,
            priority="P2",
            remediation_hint="Resolve any readiness FAIL conditions before re-evaluation.",
            source_report=phase_review_json,
        ),
    ]

    blocking_gap_count = sum(1 for row in rows if bool(row.get("blocking", False)))
    p0_gap_count = sum(1 for row in rows if bool(row.get("blocking", False)) and str(row.get("priority")) == "P0")
    p1_gap_count = sum(1 for row in rows if bool(row.get("blocking", False)) and str(row.get("priority")) == "P1")
    final_verdict = "NOT_READY" if blocking_gap_count > 0 else "READY"

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "readiness_gaps.csv"
    summary_json = out_dir / "summary.json"
    summary_md = out_dir / "summary.md"

    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in FIELDS})

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "final_verdict": final_verdict,
        "blocking_gap_count": blocking_gap_count,
        "p0_gap_count": p0_gap_count,
        "p1_gap_count": p1_gap_count,
        "submit_attempted": False,
        "cancel_attempted": False,
        "flatten_attempted": False,
        "csv_path": str(csv_path),
        "summary_json": str(summary_json),
        "summary_md": str(summary_md),
    }
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Testnet Dry-Run Readiness Gaps",
        "",
        f"- final_verdict: {summary['final_verdict']}",
        f"- blocking_gap_count: {summary['blocking_gap_count']}",
        f"- p0_gap_count: {summary['p0_gap_count']}",
        f"- p1_gap_count: {summary['p1_gap_count']}",
        "- submit_attempted: false",
        "- cancel_attempted: false",
        "- flatten_attempted: false",
    ]
    summary_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Diagnose quantified gaps for TESTNET_DRY_RUN_ONLY readiness")
    parser.add_argument("--phase-review-json", default="reports/testnet_dry_run_phase_review/testnet_dry_run_phase_review.json")
    parser.add_argument("--shadow-research-history-csv", default="reports/shadow_research_history/shadow_research_history.csv")
    parser.add_argument("--experiment-history-dashboard-json", default="reports/shadow_experiment_history_dashboard/history_dashboard.json")
    parser.add_argument("--experiment-stability-summary-json", default="reports/shadow_experiment_stability/summary.json")
    parser.add_argument("--strategy-candidate-score-summary-json", default="reports/strategy_candidate_score/summary.json")
    parser.add_argument("--daily-shadow-research-control-json", default="reports/daily_shadow_research_control/daily_shadow_research_control_report.json")
    parser.add_argument("--output-dir", default="reports/testnet_dry_run_readiness_gaps")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = diagnose_testnet_dry_run_readiness_gaps(
        phase_review_json=str(args.phase_review_json or "reports/testnet_dry_run_phase_review/testnet_dry_run_phase_review.json"),
        shadow_research_history_csv=str(args.shadow_research_history_csv or "reports/shadow_research_history/shadow_research_history.csv"),
        experiment_history_dashboard_json=str(
            args.experiment_history_dashboard_json or "reports/shadow_experiment_history_dashboard/history_dashboard.json"
        ),
        experiment_stability_summary_json=str(
            args.experiment_stability_summary_json or "reports/shadow_experiment_stability/summary.json"
        ),
        strategy_candidate_score_summary_json=str(
            args.strategy_candidate_score_summary_json or "reports/strategy_candidate_score/summary.json"
        ),
        daily_shadow_research_control_json=str(
            args.daily_shadow_research_control_json or "reports/daily_shadow_research_control/daily_shadow_research_control_report.json"
        ),
        output_dir=str(args.output_dir or "reports/testnet_dry_run_readiness_gaps"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"final_verdict={result.get('final_verdict', '')}")
    print(f"blocking_gap_count={result.get('blocking_gap_count', 0)}")


if __name__ == "__main__":
    main()
