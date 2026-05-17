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
    "run_rank",
    "experiment_id",
    "strategy_key",
    "symbol",
    "side",
    "timeframe",
    "experiment_type",
    "collector_mode",
    "target_samples_this_run",
    "max_candidates_this_run",
    "priority_bucket",
    "near_miss_threshold",
    "tuning_action",
    "tuning_applied",
    "allowed_mode",
    "submit_permission",
    "run_command",
    "reason",
]

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


def _apply_threshold_floor(current: float, action: str) -> tuple[float, bool]:
    if not math.isfinite(current):
        current = 0.75
    current = max(0.70, float(current))
    if action != "LOWER_NEAR_MISS_THRESHOLD_SLIGHTLY":
        return round(current, 8), False
    updated = max(0.70, round(current - 0.05, 8))
    return updated, updated != current


def generate_next_shadow_experiment_run_plan_v2(
    *,
    next_run_plan_csv: str = "reports/next_shadow_experiment_run_plan/next_shadow_experiment_run_plan.csv",
    tuning_suggestions_csv: str = "reports/shadow_experiment_tuning/tuning_suggestions.csv",
    experiment_sample_tracker_csv: str = "reports/shadow_experiment_sample_tracker/experiment_sample_tracker.csv",
    frequency_review_json: str = "reports/shadow_experiment_frequency_review/frequency_review.json",
    daily_research_control_json: str = "reports/daily_shadow_research_control/daily_shadow_research_control_report.json",
    output_dir: str = "reports/next_shadow_experiment_run_plan_v2",
) -> dict[str, Any]:
    plan_rows = read_csv_rows(Path(next_run_plan_csv))
    tuning_rows = read_csv_rows(Path(tuning_suggestions_csv))
    tracker_rows = read_csv_rows(Path(experiment_sample_tracker_csv))
    frequency = read_json_file(Path(frequency_review_json))
    research = read_json_file(Path(daily_research_control_json))

    tuning_by_exp = {
        str(row.get("experiment_id", "")).strip(): row
        for row in tuning_rows
        if str(row.get("experiment_id", "")).strip()
    }
    tracker_by_exp = {
        str(row.get("experiment_id", "")).strip(): row
        for row in tracker_rows
        if str(row.get("experiment_id", "")).strip()
    }
    allow_freq_up = bool(frequency.get("allow_increase_shadow_frequency", False))

    out_rows: list[dict[str, Any]] = []
    tuning_applied_count = 0
    for row in plan_rows:
        exp_id = str(row.get("experiment_id", "")).strip()
        if not exp_id:
            continue
        tuning = tuning_by_exp.get(exp_id, {})
        tracker = tracker_by_exp.get(exp_id, {})
        action = str(tuning.get("tuning_action", "KEEP_PARAMS")).strip().upper() or "KEEP_PARAMS"

        collector_mode = str(row.get("collector_mode", "observation")).strip().lower() or "observation"
        target = max(0, _to_int(row.get("target_samples_this_run"), 0))
        max_candidates = max(1, _to_int(row.get("max_candidates_this_run"), 10))
        near_miss_threshold = _to_float(tuning.get("current_near_miss_threshold"), _to_float(row.get("near_miss_threshold"), 0.75))
        reasons: list[str] = []
        applied = False

        if action == "LOWER_NEAR_MISS_THRESHOLD_SLIGHTLY":
            near_miss_threshold, applied = _apply_threshold_floor(near_miss_threshold, action)
            reasons.append("tuning_lower_near_miss_threshold")
        elif action == "INCREASE_TARGET_SAMPLES":
            suggested = _to_int(tuning.get("suggested_target_samples"), target)
            updated = min(20, max(target, suggested))
            applied = updated != target
            target = updated
            reasons.append("tuning_increase_target_samples")
        elif action == "SWITCH_TO_OBSERVATION_ONLY":
            applied = collector_mode != "observation"
            collector_mode = "observation"
            reasons.append("tuning_switch_to_observation_only")
        elif action == "REDUCE_PRIORITY":
            reasons.append("tuning_reduce_priority")
        else:
            reasons.append("tuning_keep_params")

        if not allow_freq_up:
            max_candidates = min(max_candidates, max(10, target * 2))
            reasons.append("frequency_cap_applied")
        if _to_int(tracker.get("samples_needed_for_decision"), 0) > 0:
            reasons.append("samples_needed_for_decision_not_met")
        if str(research.get("final_verdict", "")).strip().upper() == "PARTIAL":
            reasons.append("research_control_partial")

        if applied:
            tuning_applied_count += 1
        run_command = (
            "PYTHONPATH=. ./.venv/bin/python scripts/run_next_shadow_experiment_plan.py "
            f"--plan-csv reports/next_shadow_experiment_run_plan_v2/next_shadow_experiment_run_plan_v2.csv --json"
        )

        out_rows.append(
            {
                "experiment_id": exp_id,
                "strategy_key": str(row.get("strategy_key", "")).strip(),
                "symbol": str(row.get("symbol", "")).strip().upper(),
                "side": str(row.get("side", "")).strip().upper(),
                "timeframe": str(row.get("timeframe", "5m")).strip() or "5m",
                "experiment_type": str(row.get("experiment_type", "UNKNOWN")).strip().upper() or "UNKNOWN",
                "collector_mode": collector_mode,
                "target_samples_this_run": target,
                "max_candidates_this_run": max_candidates,
                "priority_bucket": str(row.get("priority_bucket", "P2")).strip().upper() or "P2",
                "near_miss_threshold": round(max(0.70, near_miss_threshold), 8),
                "tuning_action": action,
                "tuning_applied": bool(applied),
                "allowed_mode": "SHADOW_ONLY",
                "submit_permission": "NO_SUBMIT",
                "run_command": run_command,
                "reason": ";".join(sorted(set(reasons))),
            }
        )

    out_rows.sort(key=lambda item: (_to_int(item.get("run_rank"), 9999), str(item.get("experiment_id", ""))))
    ranked_rows: list[dict[str, Any]] = []
    for idx, row in enumerate(out_rows, start=1):
        item = dict(row)
        item["run_rank"] = idx
        ranked_rows.append(item)

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "next_shadow_experiment_run_plan_v2.csv"
    summary_json = out_dir / "summary.json"
    summary_md = out_dir / "summary.md"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for row in ranked_rows:
            writer.writerow({field: row.get(field, "") for field in FIELDS})

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "final_verdict": "PASS" if ranked_rows else "PARTIAL",
        "plan_version": "v2",
        "plan_v2_row_count": len(ranked_rows),
        "tuning_input_count": len(tuning_rows),
        "tuning_applied_count": tuning_applied_count,
        "allowed_mode": "SHADOW_ONLY",
        "submit_permission": "NO_SUBMIT",
        "testnet_submit_allowed": False,
        "real_submit_allowed": False,
        "submit_attempted": False,
        "cancel_attempted": False,
        "flatten_attempted": False,
        "csv_path": str(csv_path),
        "summary_json": str(summary_json),
        "summary_md": str(summary_md),
    }
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Next Shadow Experiment Run Plan V2",
        "",
        f"- final_verdict: {summary['final_verdict']}",
        f"- plan_v2_row_count: {summary['plan_v2_row_count']}",
        f"- tuning_applied_count: {summary['tuning_applied_count']}",
        "- allowed_mode: SHADOW_ONLY",
        "- submit_permission: NO_SUBMIT",
        "- submit_attempted: false",
        "- cancel_attempted: false",
        "- flatten_attempted: false",
    ]
    summary_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate v2 next-run plan by applying tuning suggestions")
    parser.add_argument("--next-run-plan-csv", default="reports/next_shadow_experiment_run_plan/next_shadow_experiment_run_plan.csv")
    parser.add_argument("--tuning-suggestions-csv", default="reports/shadow_experiment_tuning/tuning_suggestions.csv")
    parser.add_argument("--experiment-sample-tracker-csv", default="reports/shadow_experiment_sample_tracker/experiment_sample_tracker.csv")
    parser.add_argument("--frequency-review-json", default="reports/shadow_experiment_frequency_review/frequency_review.json")
    parser.add_argument("--daily-research-control-json", default="reports/daily_shadow_research_control/daily_shadow_research_control_report.json")
    parser.add_argument("--output-dir", default="reports/next_shadow_experiment_run_plan_v2")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = generate_next_shadow_experiment_run_plan_v2(
        next_run_plan_csv=str(args.next_run_plan_csv or "reports/next_shadow_experiment_run_plan/next_shadow_experiment_run_plan.csv"),
        tuning_suggestions_csv=str(args.tuning_suggestions_csv or "reports/shadow_experiment_tuning/tuning_suggestions.csv"),
        experiment_sample_tracker_csv=str(
            args.experiment_sample_tracker_csv or "reports/shadow_experiment_sample_tracker/experiment_sample_tracker.csv"
        ),
        frequency_review_json=str(args.frequency_review_json or "reports/shadow_experiment_frequency_review/frequency_review.json"),
        daily_research_control_json=str(
            args.daily_research_control_json or "reports/daily_shadow_research_control/daily_shadow_research_control_report.json"
        ),
        output_dir=str(args.output_dir or "reports/next_shadow_experiment_run_plan_v2"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"final_verdict={result.get('final_verdict', '')}")
    print(f"plan_v2_row_count={result.get('plan_v2_row_count', 0)}")


if __name__ == "__main__":
    main()
