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


def generate_shadow_experiment_frequency_review(
    *,
    shadow_experiment_trends_summary_json: str = "reports/shadow_experiment_trends/summary.json",
    shadow_experiment_progress_gap_summary_json: str = "reports/shadow_experiment_progress_gap/summary.json",
    history_dashboard_json: str = "reports/shadow_experiment_history_dashboard/history_dashboard.json",
    observation_universe_expansion_review_json: str = "reports/observation_universe_expansion/observation_universe_expansion_review.json",
    next_shadow_experiment_run_plan_summary_json: str = "reports/next_shadow_experiment_run_plan/summary.json",
    output_dir: str = "reports/shadow_experiment_frequency_review",
) -> dict[str, Any]:
    trends_summary = _read_json(Path(shadow_experiment_trends_summary_json))
    gap_summary = _read_json(Path(shadow_experiment_progress_gap_summary_json))
    history_dashboard = _read_json(Path(history_dashboard_json))
    expansion_review = _read_json(Path(observation_universe_expansion_review_json))
    next_run_summary = _read_json(Path(next_shadow_experiment_run_plan_summary_json))

    history_run_count = _to_int(trends_summary.get("max_history_run_count"), _to_int(history_dashboard.get("history_row_count"), 0))
    experiment_count = _to_int(history_dashboard.get("experiment_count"), 0)
    needs_more_data_count = _to_int(history_dashboard.get("needs_more_data_count"), 0)
    insufficient_history_count = _to_int(trends_summary.get("insufficient_history_count"), 0)
    target_total = _to_int(next_run_summary.get("total_next_run_sample_target"), 0)
    if target_total <= 0:
        target_total = _to_int(gap_summary.get("target_total"), 0)
    actual_total = _to_int(gap_summary.get("actual_total"), 0)
    sample_total = max(actual_total, _to_int(history_dashboard.get("history_row_count"), 0))

    missing_cache_gap_count = _to_int(
        (gap_summary.get("gap_reason_breakdown") or {}).get("MISSING_CACHE"),
        0,
    )
    unstable_bad_count = _to_int(history_dashboard.get("reject_count"), 0)

    allow_increase_shadow_frequency = (
        history_run_count >= 5
        and sample_total >= 20
        and unstable_bad_count == 0
        and needs_more_data_count < max(1, experiment_count)
        and missing_cache_gap_count == 0
    )
    allow_increase_max_candidates_per_day = (
        allow_increase_shadow_frequency
        and sample_total >= 50
        and _to_int(history_dashboard.get("avg_stability_score"), 0) >= 60
    )
    allow_more_observation_runs = allow_increase_shadow_frequency and bool(expansion_review.get("allow_expand_observation_universe", False))

    blocking_reasons: list[str] = []
    if history_run_count < 5:
        blocking_reasons.append("insufficient_history_runs")
    if sample_total < 20:
        blocking_reasons.append("insufficient_experiment_samples")
    if needs_more_data_count >= max(1, experiment_count):
        blocking_reasons.append("stability_needs_more_data")
    if missing_cache_gap_count > 0:
        blocking_reasons.append("progress_gap_due_to_missing_cache")
    if insufficient_history_count > 0:
        blocking_reasons.append("trend_history_not_ready")
    if str(next_run_summary.get("allowed_mode", "SHADOW_ONLY")).strip().upper() != "SHADOW_ONLY":
        blocking_reasons.append("next_run_plan_not_shadow_only")

    allowed_frequency_actions = ["KEEP_CURRENT_FREQUENCY", "CONTINUE_DAILY_SHADOW_EXPERIMENTS"]
    if allow_increase_shadow_frequency:
        allowed_frequency_actions.append("INCREASE_SHADOW_RUN_FREQUENCY")
    if allow_increase_max_candidates_per_day:
        allowed_frequency_actions.append("INCREASE_MAX_CANDIDATES_STEPWISE")
    if allow_more_observation_runs:
        allowed_frequency_actions.append("ADD_MORE_OBSERVATION_RUN_WINDOWS")

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "final_verdict": "PASS" if allow_increase_shadow_frequency else "PARTIAL",
        "allow_increase_shadow_frequency": bool(allow_increase_shadow_frequency),
        "allow_increase_max_candidates_per_day": bool(allow_increase_max_candidates_per_day),
        "allow_more_observation_runs": bool(allow_more_observation_runs),
        "current_allowed_mode": "SHADOW_ONLY",
        "submit_allowed": False,
        "real_submit_allowed": False,
        "blocking_reasons": sorted(set(blocking_reasons)),
        "allowed_frequency_actions": allowed_frequency_actions,
        "prohibited_actions": ["NO_TESTNET_SUBMIT", "NO_REAL_SUBMIT", "NO_BYPASS_STRATEGY_GATE"],
        "submit_attempted": False,
        "cancel_attempted": False,
        "flatten_attempted": False,
        "metrics": {
            "history_run_count": history_run_count,
            "experiment_count": experiment_count,
            "needs_more_data_count": needs_more_data_count,
            "target_total": target_total,
            "actual_total": actual_total,
            "sample_total_proxy": sample_total,
            "missing_cache_gap_count": missing_cache_gap_count,
            "insufficient_history_count": insufficient_history_count,
        },
    }

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "frequency_review.json"
    md_path = out_dir / "summary.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Shadow Experiment Frequency Review",
        "",
        f"- final_verdict: {report['final_verdict']}",
        f"- allow_increase_shadow_frequency: {str(report['allow_increase_shadow_frequency']).lower()}",
        f"- allow_increase_max_candidates_per_day: {str(report['allow_increase_max_candidates_per_day']).lower()}",
        f"- allow_more_observation_runs: {str(report['allow_more_observation_runs']).lower()}",
        "- current_allowed_mode: SHADOW_ONLY",
        "- submit_allowed: false",
        "- real_submit_allowed: false",
    ]
    if report["blocking_reasons"]:
        lines.append(f"- blocking_reasons: {', '.join(report['blocking_reasons'])}")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate review about increasing shadow experiment frequency")
    parser.add_argument("--shadow-experiment-trends-summary-json", default="reports/shadow_experiment_trends/summary.json")
    parser.add_argument("--shadow-experiment-progress-gap-summary-json", default="reports/shadow_experiment_progress_gap/summary.json")
    parser.add_argument("--history-dashboard-json", default="reports/shadow_experiment_history_dashboard/history_dashboard.json")
    parser.add_argument(
        "--observation-universe-expansion-review-json",
        default="reports/observation_universe_expansion/observation_universe_expansion_review.json",
    )
    parser.add_argument(
        "--next-shadow-experiment-run-plan-summary-json",
        default="reports/next_shadow_experiment_run_plan/summary.json",
    )
    parser.add_argument("--output-dir", default="reports/shadow_experiment_frequency_review")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = generate_shadow_experiment_frequency_review(
        shadow_experiment_trends_summary_json=str(
            args.shadow_experiment_trends_summary_json or "reports/shadow_experiment_trends/summary.json"
        ),
        shadow_experiment_progress_gap_summary_json=str(
            args.shadow_experiment_progress_gap_summary_json or "reports/shadow_experiment_progress_gap/summary.json"
        ),
        history_dashboard_json=str(args.history_dashboard_json or "reports/shadow_experiment_history_dashboard/history_dashboard.json"),
        observation_universe_expansion_review_json=str(
            args.observation_universe_expansion_review_json
            or "reports/observation_universe_expansion/observation_universe_expansion_review.json"
        ),
        next_shadow_experiment_run_plan_summary_json=str(
            args.next_shadow_experiment_run_plan_summary_json or "reports/next_shadow_experiment_run_plan/summary.json"
        ),
        output_dir=str(args.output_dir or "reports/shadow_experiment_frequency_review"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"final_verdict={result.get('final_verdict', '')}")
    print(
        "allow_increase_shadow_frequency="
        f"{str(result.get('allow_increase_shadow_frequency', False)).lower()}"
    )


if __name__ == "__main__":
    main()
