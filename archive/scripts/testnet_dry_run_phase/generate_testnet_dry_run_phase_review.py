from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.strategy_edge_common import read_csv_rows, to_float_nan


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _to_int(value: Any, default: int = 0) -> int:
    parsed = to_float_nan(value)
    if parsed != parsed:
        return int(default)
    return int(parsed)


def _to_float(value: Any, default: float = float("nan")) -> float:
    parsed = to_float_nan(value)
    if parsed != parsed:
        return float(default)
    return float(parsed)


def generate_testnet_dry_run_phase_review(
    *,
    shadow_research_history_csv: str = "reports/shadow_research_history/shadow_research_history.csv",
    daily_research_control_json: str = "reports/daily_shadow_research_control/daily_shadow_research_control_report.json",
    testnet_dry_run_readiness_json: str = "reports/testnet_dry_run_readiness/testnet_dry_run_readiness_report.json",
    shadow_experiment_stability_summary_json: str = "reports/shadow_experiment_stability/summary.json",
    shadow_experiment_history_dashboard_json: str = "reports/shadow_experiment_history_dashboard/history_dashboard.json",
    strategy_candidate_score_summary_json: str = "reports/strategy_candidate_score/summary.json",
    system_health_json: str = "reports/system_health/trading_system_health_dashboard.json",
    output_dir: str = "reports/testnet_dry_run_phase_review",
) -> dict[str, Any]:
    history_rows = read_csv_rows(Path(shadow_research_history_csv))
    daily = _read_json(Path(daily_research_control_json))
    readiness = _read_json(Path(testnet_dry_run_readiness_json))
    stability = _read_json(Path(shadow_experiment_stability_summary_json))
    exp_dashboard = _read_json(Path(shadow_experiment_history_dashboard_json))
    strategy_summary = _read_json(Path(strategy_candidate_score_summary_json))
    system_health = _read_json(Path(system_health_json))

    unique_days = {str(row.get("run_date", "")).strip() for row in history_rows if str(row.get("run_date", "")).strip()}
    history_days = len(unique_days)
    total_experiment_samples = _to_int(exp_dashboard.get("history_row_count"), 0)
    needs_more_data_count = _to_int(stability.get("needs_more_data_count"), _to_int(exp_dashboard.get("needs_more_data_count"), 0))
    experiment_count = _to_int(stability.get("experiment_count"), _to_int(exp_dashboard.get("experiment_count"), 0))
    avg_weighted_sample_count = _to_float(strategy_summary.get("avg_weighted_sample_count"), _to_float(strategy_summary.get("weighted_sample_count")))
    if avg_weighted_sample_count != avg_weighted_sample_count:
        avg_weighted_sample_count = _to_float(daily.get("weighted_sample_count"), 0.0)

    system_health_pass = str(system_health.get("final_verdict", "")).strip().upper() == "PASS"
    readiness_not_fail = str(readiness.get("final_verdict", "")).strip().upper() != "FAIL"
    no_trade_actions_attempted = (
        (not bool(daily.get("submit_attempted", False)))
        and (not bool(daily.get("cancel_attempted", False)))
        and (not bool(daily.get("flatten_attempted", False)))
    )

    minimum_requirements = {
        "system_health_pass": bool(system_health_pass),
        "shadow_research_history_days_min_met": bool(history_days >= 3),
        "experiment_samples_min_met": bool(total_experiment_samples >= 20),
        "stability_not_all_needs_more_data": bool((experiment_count > 0) and (needs_more_data_count < experiment_count)),
        "strategy_candidate_weighted_samples_min_met": bool(avg_weighted_sample_count >= 5.0),
        "no_trade_actions_attempted": bool(no_trade_actions_attempted),
        "testnet_dry_run_readiness_not_fail": bool(readiness_not_fail),
    }

    allow_testnet_dry_run_only = all(minimum_requirements.values())
    blocking_reasons: list[str] = []
    if history_days < 3:
        blocking_reasons.append("insufficient_shadow_research_history")
    if total_experiment_samples < 20:
        blocking_reasons.append("insufficient_experiment_samples")
    if experiment_count <= 0 or needs_more_data_count >= max(1, experiment_count):
        blocking_reasons.append("stability_needs_more_data")
    if avg_weighted_sample_count < 5.0:
        blocking_reasons.append("weighted_sample_count_too_small")
    if not system_health_pass:
        blocking_reasons.append("system_health_not_pass")
    if not no_trade_actions_attempted:
        blocking_reasons.append("trade_actions_detected")
    if not readiness_not_fail:
        blocking_reasons.append("testnet_dry_run_readiness_fail")

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "final_verdict": "READY_FOR_TESTNET_DRY_RUN_ONLY" if allow_testnet_dry_run_only else "NOT_READY",
        "allow_testnet_dry_run_only": bool(allow_testnet_dry_run_only),
        "allow_testnet_submit": False,
        "allow_real_submit": False,
        "current_phase": str(daily.get("current_phase", "SHADOW_EXPERIMENT_COLLECTION")).strip().upper() or "SHADOW_EXPERIMENT_COLLECTION",
        "minimum_requirements": minimum_requirements,
        "blocking_reasons": sorted(set(blocking_reasons)),
        "allowed_next_modes": ["SHADOW_ONLY", "TESTNET_DRY_RUN_ONLY_WHEN_REQUIREMENTS_MET"],
        "prohibited_actions": ["NO_TESTNET_SUBMIT", "NO_REAL_SUBMIT", "NO_BYPASS_STRATEGY_GATE"],
        "submit_attempted": False,
        "cancel_attempted": False,
        "flatten_attempted": False,
        "metrics": {
            "history_days": history_days,
            "total_experiment_samples_proxy": total_experiment_samples,
            "experiment_count": experiment_count,
            "needs_more_data_count": needs_more_data_count,
            "avg_weighted_sample_count": avg_weighted_sample_count,
        },
    }

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "testnet_dry_run_phase_review.json"
    md_path = out_dir / "summary.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Testnet Dry-Run Phase Review",
        "",
        f"- final_verdict: {report['final_verdict']}",
        f"- allow_testnet_dry_run_only: {str(report['allow_testnet_dry_run_only']).lower()}",
        "- allow_testnet_submit: false",
        "- allow_real_submit: false",
        f"- current_phase: {report['current_phase']}",
    ]
    if report["blocking_reasons"]:
        lines.append(f"- blocking_reasons: {', '.join(report['blocking_reasons'])}")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate phase review for entering TESTNET_DRY_RUN_ONLY")
    parser.add_argument("--shadow-research-history-csv", default="reports/shadow_research_history/shadow_research_history.csv")
    parser.add_argument("--daily-research-control-json", default="reports/daily_shadow_research_control/daily_shadow_research_control_report.json")
    parser.add_argument("--testnet-dry-run-readiness-json", default="reports/testnet_dry_run_readiness/testnet_dry_run_readiness_report.json")
    parser.add_argument("--shadow-experiment-stability-summary-json", default="reports/shadow_experiment_stability/summary.json")
    parser.add_argument("--shadow-experiment-history-dashboard-json", default="reports/shadow_experiment_history_dashboard/history_dashboard.json")
    parser.add_argument("--strategy-candidate-score-summary-json", default="reports/strategy_candidate_score/summary.json")
    parser.add_argument("--system-health-json", default="reports/system_health/trading_system_health_dashboard.json")
    parser.add_argument("--output-dir", default="reports/testnet_dry_run_phase_review")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = generate_testnet_dry_run_phase_review(
        shadow_research_history_csv=str(args.shadow_research_history_csv or "reports/shadow_research_history/shadow_research_history.csv"),
        daily_research_control_json=str(
            args.daily_research_control_json or "reports/daily_shadow_research_control/daily_shadow_research_control_report.json"
        ),
        testnet_dry_run_readiness_json=str(
            args.testnet_dry_run_readiness_json or "reports/testnet_dry_run_readiness/testnet_dry_run_readiness_report.json"
        ),
        shadow_experiment_stability_summary_json=str(
            args.shadow_experiment_stability_summary_json or "reports/shadow_experiment_stability/summary.json"
        ),
        shadow_experiment_history_dashboard_json=str(
            args.shadow_experiment_history_dashboard_json or "reports/shadow_experiment_history_dashboard/history_dashboard.json"
        ),
        strategy_candidate_score_summary_json=str(
            args.strategy_candidate_score_summary_json or "reports/strategy_candidate_score/summary.json"
        ),
        system_health_json=str(args.system_health_json or "reports/system_health/trading_system_health_dashboard.json"),
        output_dir=str(args.output_dir or "reports/testnet_dry_run_phase_review"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"final_verdict={result.get('final_verdict', '')}")
    print(f"allow_testnet_dry_run_only={str(result.get('allow_testnet_dry_run_only', False)).lower()}")


if __name__ == "__main__":
    main()
