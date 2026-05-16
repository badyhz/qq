from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.strategy_edge_common import to_float_nan


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


def generate_daily_shadow_research_control_report(
    *,
    history_dashboard_json: str = "reports/shadow_experiment_history_dashboard/history_dashboard.json",
    experiment_priorities_summary_json: str = "reports/shadow_experiment_priorities/summary.json",
    experiment_sample_tracker_summary_json: str = "reports/shadow_experiment_sample_tracker/summary.json",
    next_run_summary_json: str = "reports/next_shadow_experiment_run/summary.json",
    progress_gap_summary_json: str = "reports/shadow_experiment_progress_gap/summary.json",
    trends_summary_json: str = "reports/shadow_experiment_trends/summary.json",
    frequency_review_json: str = "reports/shadow_experiment_frequency_review/frequency_review.json",
    tuning_summary_json: str = "reports/shadow_experiment_tuning/summary.json",
    shadow_only_loop_plan_json: str = "reports/shadow_only_loop_plan/shadow_only_loop_plan.json",
    output_dir: str = "reports/daily_shadow_research_control",
) -> dict[str, Any]:
    history = _read_json(Path(history_dashboard_json))
    priorities = _read_json(Path(experiment_priorities_summary_json))
    tracker = _read_json(Path(experiment_sample_tracker_summary_json))
    next_run = _read_json(Path(next_run_summary_json))
    gap = _read_json(Path(progress_gap_summary_json))
    trends = _read_json(Path(trends_summary_json))
    frequency = _read_json(Path(frequency_review_json))
    tuning = _read_json(Path(tuning_summary_json))
    loop_plan = _read_json(Path(shadow_only_loop_plan_json))

    total_experiments = _to_int(history.get("experiment_count"), max(_to_int(priorities.get("experiment_count"), 0), _to_int(tracker.get("experiment_count"), 0)))
    next_run_candidate_count = _to_int(next_run.get("next_run_candidate_count"), 0)
    sample_gap_total = _to_int(gap.get("sample_gap_total"), 0)
    needs_more_data_count = _to_int(history.get("needs_more_data_count"), _to_int(trends.get("watch_more_count"), 0))
    allow_increase_shadow_frequency = bool(frequency.get("allow_increase_shadow_frequency", False))

    operator_attention: list[str] = []
    if sample_gap_total > 0:
        operator_attention.append("Experiment samples are still below decision threshold.")
    if needs_more_data_count > 0:
        operator_attention.append("Most experiments still require more data and trend history.")
    if not allow_increase_shadow_frequency:
        operator_attention.append("Keep shadow frequency conservative until stability improves.")

    final_verdict = "PASS"
    if sample_gap_total > 0 or needs_more_data_count > 0:
        final_verdict = "PARTIAL"

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "final_verdict": final_verdict,
        "current_phase": "SHADOW_EXPERIMENT_COLLECTION",
        "total_experiments": total_experiments,
        "next_run_candidate_count": next_run_candidate_count,
        "sample_gap_total": sample_gap_total,
        "needs_more_data_count": needs_more_data_count,
        "allow_increase_shadow_frequency": allow_increase_shadow_frequency,
        "recommended_next_action": "RUN_SHADOW_ONLY_LOOP_ONCE",
        "allowed_mode": "SHADOW_ONLY",
        "submit_allowed": False,
        "testnet_submit_allowed": False,
        "real_submit_allowed": False,
        "prohibited_actions": ["NO_REAL_SUBMIT", "NO_TESTNET_SUBMIT", "NO_BYPASS_STRATEGY_GATE"],
        "operator_attention": sorted(set(operator_attention)),
        "submit_attempted": False,
        "cancel_attempted": False,
        "flatten_attempted": False,
        "inputs": {
            "history_final_verdict": str(history.get("final_verdict", "")).strip().upper(),
            "next_run_final_verdict": str(next_run.get("final_verdict", "")).strip().upper(),
            "progress_gap_final_verdict": str(gap.get("final_verdict", "")).strip().upper(),
            "trends_final_verdict": str(trends.get("final_verdict", "")).strip().upper(),
            "frequency_final_verdict": str(frequency.get("final_verdict", "")).strip().upper(),
            "tuning_final_verdict": str(tuning.get("final_verdict", "")).strip().upper(),
            "loop_plan_final_verdict": str(loop_plan.get("final_verdict", "")).strip().upper(),
        },
    }

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "daily_shadow_research_control_report.json"
    md_path = out_dir / "summary.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Daily Shadow Research Control Report",
        "",
        f"- final_verdict: {report['final_verdict']}",
        f"- current_phase: {report['current_phase']}",
        f"- total_experiments: {report['total_experiments']}",
        f"- next_run_candidate_count: {report['next_run_candidate_count']}",
        f"- sample_gap_total: {report['sample_gap_total']}",
        f"- needs_more_data_count: {report['needs_more_data_count']}",
        f"- recommended_next_action: {report['recommended_next_action']}",
        "- allowed_mode: SHADOW_ONLY",
        "- submit_allowed: false",
        "- testnet_submit_allowed: false",
        "- real_submit_allowed: false",
    ]
    if report["operator_attention"]:
        lines.append(f"- operator_attention: {', '.join(report['operator_attention'])}")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate daily shadow research control report")
    parser.add_argument("--history-dashboard-json", default="reports/shadow_experiment_history_dashboard/history_dashboard.json")
    parser.add_argument("--experiment-priorities-summary-json", default="reports/shadow_experiment_priorities/summary.json")
    parser.add_argument("--experiment-sample-tracker-summary-json", default="reports/shadow_experiment_sample_tracker/summary.json")
    parser.add_argument("--next-run-summary-json", default="reports/next_shadow_experiment_run/summary.json")
    parser.add_argument("--progress-gap-summary-json", default="reports/shadow_experiment_progress_gap/summary.json")
    parser.add_argument("--trends-summary-json", default="reports/shadow_experiment_trends/summary.json")
    parser.add_argument("--frequency-review-json", default="reports/shadow_experiment_frequency_review/frequency_review.json")
    parser.add_argument("--tuning-summary-json", default="reports/shadow_experiment_tuning/summary.json")
    parser.add_argument("--shadow-only-loop-plan-json", default="reports/shadow_only_loop_plan/shadow_only_loop_plan.json")
    parser.add_argument("--output-dir", default="reports/daily_shadow_research_control")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = generate_daily_shadow_research_control_report(
        history_dashboard_json=str(args.history_dashboard_json or "reports/shadow_experiment_history_dashboard/history_dashboard.json"),
        experiment_priorities_summary_json=str(
            args.experiment_priorities_summary_json or "reports/shadow_experiment_priorities/summary.json"
        ),
        experiment_sample_tracker_summary_json=str(
            args.experiment_sample_tracker_summary_json or "reports/shadow_experiment_sample_tracker/summary.json"
        ),
        next_run_summary_json=str(args.next_run_summary_json or "reports/next_shadow_experiment_run/summary.json"),
        progress_gap_summary_json=str(args.progress_gap_summary_json or "reports/shadow_experiment_progress_gap/summary.json"),
        trends_summary_json=str(args.trends_summary_json or "reports/shadow_experiment_trends/summary.json"),
        frequency_review_json=str(args.frequency_review_json or "reports/shadow_experiment_frequency_review/frequency_review.json"),
        tuning_summary_json=str(args.tuning_summary_json or "reports/shadow_experiment_tuning/summary.json"),
        shadow_only_loop_plan_json=str(args.shadow_only_loop_plan_json or "reports/shadow_only_loop_plan/shadow_only_loop_plan.json"),
        output_dir=str(args.output_dir or "reports/daily_shadow_research_control"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"final_verdict={result.get('final_verdict', '')}")
    print(f"recommended_next_action={result.get('recommended_next_action', '')}")


if __name__ == "__main__":
    main()
