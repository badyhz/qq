from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.strategy_edge_common import read_csv_rows, to_float_nan


FIELDS = [
    "experiment_id",
    "strategy_key",
    "symbol",
    "side",
    "timeframe",
    "experiment_type",
    "gap_reason",
    "current_target_samples",
    "actual_new_candidates",
    "suggested_target_samples",
    "current_near_miss_threshold",
    "suggested_near_miss_threshold",
    "current_collector_mode",
    "suggested_collector_mode",
    "tuning_action",
    "risk_level",
    "allowed_mode",
    "submit_permission",
    "reason",
]


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
    if not math.isfinite(parsed):
        return int(default)
    return int(parsed)


def _to_float(value: Any, default: float = float("nan")) -> float:
    parsed = to_float_nan(value)
    if not math.isfinite(parsed):
        return float(default)
    return float(parsed)


def _find_threshold(row: dict[str, Any], collector_mode: str) -> float:
    v = _to_float(row.get("near_miss_threshold"))
    if math.isfinite(v):
        return v
    return 0.75 if collector_mode == "observation" else 1.0


def generate_shadow_experiment_tuning_suggestions(
    *,
    progress_gap_report_csv: str = "reports/shadow_experiment_progress_gap/progress_gap_report.csv",
    next_run_summary_json: str = "reports/next_shadow_experiment_run/summary.json",
    frequency_review_json: str = "reports/shadow_experiment_frequency_review/frequency_review.json",
    experiment_sample_tracker_csv: str = "reports/shadow_experiment_sample_tracker/experiment_sample_tracker.csv",
    next_run_plan_csv: str = "reports/next_shadow_experiment_run_plan/next_shadow_experiment_run_plan.csv",
    output_dir: str = "reports/shadow_experiment_tuning",
) -> dict[str, Any]:
    gap_rows = read_csv_rows(Path(progress_gap_report_csv))
    _ = _read_json(Path(next_run_summary_json))
    frequency = _read_json(Path(frequency_review_json))
    tracker_rows = read_csv_rows(Path(experiment_sample_tracker_csv))
    plan_rows = read_csv_rows(Path(next_run_plan_csv))

    plan_by_exp = {
        str(row.get("experiment_id", "")).strip(): row
        for row in plan_rows
        if str(row.get("experiment_id", "")).strip()
    }
    tracker_by_exp = {
        str(row.get("experiment_id", "")).strip(): row
        for row in tracker_rows
        if str(row.get("experiment_id", "")).strip()
    }

    out_rows: list[dict[str, Any]] = []
    for gap in gap_rows:
        exp_id = str(gap.get("experiment_id", "")).strip()
        if not exp_id:
            continue
        plan = plan_by_exp.get(exp_id, {})
        tracker = tracker_by_exp.get(exp_id, {})
        current_target = max(0, _to_int(gap.get("target_samples_this_run"), _to_int(plan.get("target_samples_this_run"), 0)))
        actual = max(0, _to_int(gap.get("actual_new_candidates"), 0))
        gap_reason = str(gap.get("gap_reason", "UNKNOWN")).strip().upper() or "UNKNOWN"
        collector_mode = str(plan.get("collector_mode", gap.get("suggested_collector_mode", "observation"))).strip().lower() or "observation"
        current_threshold = _find_threshold(plan, collector_mode)

        tuning_action = "KEEP_PARAMS"
        suggested_threshold = current_threshold
        suggested_collector_mode = collector_mode
        suggested_target = current_target
        reason_parts: list[str] = []

        if gap_reason == "FILTER_TOO_STRICT" and actual > 0:
            tuning_action = "LOWER_NEAR_MISS_THRESHOLD_SLIGHTLY"
            suggested_threshold = max(0.60, round(current_threshold - 0.05, 4))
            reason_parts.append("strict_filter_blocks_candidates")
        elif actual <= 0 and collector_mode == "strict":
            tuning_action = "SWITCH_TO_OBSERVATION_ONLY"
            suggested_collector_mode = "observation"
            reason_parts.append("no_candidates_in_strict_mode")
        elif gap_reason == "NO_SIGNAL":
            tuning_action = "INCREASE_TARGET_SAMPLES"
            suggested_target = max(current_target, current_target + max(1, int(round(current_target * 0.2))))
            reason_parts.append("no_signal_observed")
        else:
            reason_parts.append("keep_conservative_settings")

        if _to_int(tracker.get("samples_needed_for_decision"), 0) > 0:
            reason_parts.append("samples_below_decision_threshold")
        if not bool(frequency.get("allow_increase_shadow_frequency", False)):
            reason_parts.append("frequency_increase_not_allowed")

        out_rows.append(
            {
                "experiment_id": exp_id,
                "strategy_key": str(gap.get("strategy_key", plan.get("strategy_key", ""))).strip(),
                "symbol": str(gap.get("symbol", plan.get("symbol", ""))).strip().upper(),
                "side": str(gap.get("side", plan.get("side", ""))).strip().upper(),
                "timeframe": str(gap.get("timeframe", plan.get("timeframe", "5m"))).strip() or "5m",
                "experiment_type": str(gap.get("experiment_type", plan.get("experiment_type", "UNKNOWN"))).strip().upper() or "UNKNOWN",
                "gap_reason": gap_reason,
                "current_target_samples": current_target,
                "actual_new_candidates": actual,
                "suggested_target_samples": suggested_target,
                "current_near_miss_threshold": round(current_threshold, 6),
                "suggested_near_miss_threshold": round(suggested_threshold, 6),
                "current_collector_mode": collector_mode,
                "suggested_collector_mode": suggested_collector_mode,
                "tuning_action": tuning_action,
                "risk_level": "LOW_CONFIDENCE",
                "allowed_mode": "SHADOW_ONLY",
                "submit_permission": "NO_SUBMIT",
                "reason": ";".join(sorted(set(reason_parts))),
            }
        )

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "tuning_suggestions.csv"
    summary_json = out_dir / "summary.json"
    summary_md = out_dir / "summary.md"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for row in out_rows:
            writer.writerow({field: row.get(field, "") for field in FIELDS})

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "final_verdict": "PASS" if out_rows else "PARTIAL",
        "suggestion_count": len(out_rows),
        "action_breakdown": {
            action: sum(1 for row in out_rows if str(row.get("tuning_action", "")).strip().upper() == action)
            for action in {
                "KEEP_PARAMS",
                "LOWER_NEAR_MISS_THRESHOLD_SLIGHTLY",
                "INCREASE_TARGET_SAMPLES",
                "SWITCH_TO_OBSERVATION_ONLY",
                "RELAX_ONE_DIMENSION_FOR_OBSERVATION",
                "REDUCE_PRIORITY",
                "UNKNOWN",
            }
        },
        "allowed_mode": "SHADOW_ONLY",
        "submit_permission": "NO_SUBMIT",
        "submit_attempted": False,
        "cancel_attempted": False,
        "flatten_attempted": False,
        "csv_path": str(csv_path),
        "summary_json": str(summary_json),
        "summary_md": str(summary_md),
    }
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Shadow Experiment Tuning Suggestions",
        "",
        f"- final_verdict: {summary['final_verdict']}",
        f"- suggestion_count: {summary['suggestion_count']}",
        "- allowed_mode: SHADOW_ONLY",
        "- submit_permission: NO_SUBMIT",
        "- submit_attempted: false",
        "- cancel_attempted: false",
        "- flatten_attempted: false",
    ]
    summary_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate conservative tuning suggestions for shadow experiments")
    parser.add_argument("--progress-gap-report-csv", default="reports/shadow_experiment_progress_gap/progress_gap_report.csv")
    parser.add_argument("--next-run-summary-json", default="reports/next_shadow_experiment_run/summary.json")
    parser.add_argument("--frequency-review-json", default="reports/shadow_experiment_frequency_review/frequency_review.json")
    parser.add_argument("--experiment-sample-tracker-csv", default="reports/shadow_experiment_sample_tracker/experiment_sample_tracker.csv")
    parser.add_argument("--next-run-plan-csv", default="reports/next_shadow_experiment_run_plan/next_shadow_experiment_run_plan.csv")
    parser.add_argument("--output-dir", default="reports/shadow_experiment_tuning")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = generate_shadow_experiment_tuning_suggestions(
        progress_gap_report_csv=str(args.progress_gap_report_csv or "reports/shadow_experiment_progress_gap/progress_gap_report.csv"),
        next_run_summary_json=str(args.next_run_summary_json or "reports/next_shadow_experiment_run/summary.json"),
        frequency_review_json=str(args.frequency_review_json or "reports/shadow_experiment_frequency_review/frequency_review.json"),
        experiment_sample_tracker_csv=str(
            args.experiment_sample_tracker_csv or "reports/shadow_experiment_sample_tracker/experiment_sample_tracker.csv"
        ),
        next_run_plan_csv=str(args.next_run_plan_csv or "reports/next_shadow_experiment_run_plan/next_shadow_experiment_run_plan.csv"),
        output_dir=str(args.output_dir or "reports/shadow_experiment_tuning"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"final_verdict={result.get('final_verdict', '')}")
    print(f"suggestion_count={result.get('suggestion_count', 0)}")


if __name__ == "__main__":
    main()
