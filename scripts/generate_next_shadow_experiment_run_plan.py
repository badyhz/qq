from __future__ import annotations

import argparse
import csv
import json
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
    "allowed_mode",
    "submit_permission",
    "run_command",
    "reason",
]

def _to_int(value: Any, default: int = 0) -> int:
    parsed = to_float_nan(value)
    if parsed != parsed:
        return int(default)
    return int(parsed)


def _collector_mode(experiment_type: str) -> str:
    text = str(experiment_type or "").strip().upper()
    if text == "BASELINE_STRICT":
        return "strict"
    return "observation"


def generate_next_shadow_experiment_run_plan(
    *,
    experiment_sample_tracker_csv: str = "reports/shadow_experiment_sample_tracker/experiment_sample_tracker.csv",
    experiment_priority_rank_csv: str = "reports/shadow_experiment_priorities/experiment_priority_rank.csv",
    expansion_candidates_csv: str = "reports/minimal_observation_expansion/expansion_candidates.csv",
    shadow_scan_daily_schedule_json: str = "reports/shadow_scan_schedule/shadow_scan_daily_schedule.json",
    observation_universe_expansion_review_json: str = "reports/observation_universe_expansion/observation_universe_expansion_review.json",
    output_dir: str = "reports/next_shadow_experiment_run_plan",
) -> dict[str, Any]:
    tracker_rows = read_csv_rows(Path(experiment_sample_tracker_csv))
    priority_rows = read_csv_rows(Path(experiment_priority_rank_csv))
    expansion_rows = read_csv_rows(Path(expansion_candidates_csv))
    schedule = read_json_file(Path(shadow_scan_daily_schedule_json))
    expansion_review = read_json_file(Path(observation_universe_expansion_review_json))

    priority_by_exp = {
        str(row.get("experiment_id", "")).strip(): row
        for row in priority_rows
        if str(row.get("experiment_id", "")).strip()
    }
    expansion_by_key = {
        str(row.get("strategy_key", "")).strip(): row
        for row in expansion_rows
        if str(row.get("strategy_key", "")).strip()
    }

    plan_rows: list[dict[str, Any]] = []
    for row in tracker_rows:
        exp_id = str(row.get("experiment_id", "")).strip()
        if not exp_id:
            continue
        status = str(row.get("collection_status", "")).strip().upper()
        if status == "PAUSED":
            continue
        target_samples = _to_int(row.get("next_run_sample_target"), 0)
        if target_samples <= 0:
            continue

        priority = priority_by_exp.get(exp_id, {})
        strategy_key = str(row.get("strategy_key", "")).strip()
        expansion = expansion_by_key.get(strategy_key, {})
        experiment_type = str(row.get("experiment_type", "UNKNOWN")).strip().upper() or "UNKNOWN"
        collector_mode = _collector_mode(experiment_type)
        priority_bucket = str(priority.get("priority_bucket", row.get("priority_bucket", "P2"))).strip().upper() or "P2"
        max_candidates = max(target_samples * 2, _to_int(expansion.get("max_candidates_adjustment"), 0), 10)
        reason_parts: list[str] = [
            str(row.get("next_action", "collect_more_shadow_experiment_samples")).strip() or "collect_more_shadow_experiment_samples"
        ]
        if str(expansion.get("expansion_allowed_now", "")).strip().lower() in {"false", "0"}:
            reason_parts.append("expansion_not_allowed_yet")
        run_command = (
            "PYTHONPATH=. ./.venv/bin/python scripts/run_shadow_observation_experiments.py "
            f"--experiment-matrix reports/shadow_observation_experiments/experiment_matrix.csv "
            f"--max-candidates-per-experiment {max_candidates} --json"
        )

        plan_rows.append(
            {
                "experiment_id": exp_id,
                "strategy_key": strategy_key,
                "symbol": str(row.get("symbol", "")).strip().upper(),
                "side": str(row.get("side", "")).strip().upper(),
                "timeframe": str(row.get("timeframe", "5m")).strip() or "5m",
                "experiment_type": experiment_type,
                "collector_mode": collector_mode,
                "target_samples_this_run": target_samples,
                "max_candidates_this_run": max_candidates,
                "priority_bucket": priority_bucket,
                "allowed_mode": "SHADOW_ONLY",
                "submit_permission": "NO_SUBMIT",
                "run_command": run_command,
                "reason": ";".join(sorted(set(part for part in reason_parts if part))),
            }
        )

    # deterministic ordering by priority then gap target
    bucket_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "PAUSED": 4}
    plan_rows.sort(
        key=lambda row: (
            bucket_order.get(str(row.get("priority_bucket", "P3")).strip().upper(), 9),
            -_to_int(row.get("target_samples_this_run"), 0),
            str(row.get("experiment_id", "")),
        )
    )
    ranked_rows: list[dict[str, Any]] = []
    for idx, row in enumerate(plan_rows, start=1):
        payload = dict(row)
        payload["run_rank"] = idx
        ranked_rows.append(payload)

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "next_shadow_experiment_run_plan.csv"
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
        "plan_row_count": len(ranked_rows),
        "recommended_next_action": "RUN_SHADOW_EXPERIMENT_PLAN" if ranked_rows else "KEEP_COLLECTING_SHADOW_EXPERIMENT_SAMPLES",
        "allowed_mode": "SHADOW_ONLY",
        "submit_permission": "NO_SUBMIT",
        "submit_attempted": False,
        "cancel_attempted": False,
        "flatten_attempted": False,
        "testnet_submit_allowed": False,
        "real_submit_allowed": False,
        "allow_expand_observation_universe": bool(expansion_review.get("allow_expand_observation_universe", False)),
        "schedule_allowed_mode": str(schedule.get("allowed_mode", "SHADOW_ONLY")).strip().upper() or "SHADOW_ONLY",
        "csv_path": str(csv_path),
        "summary_json": str(summary_json),
        "summary_md": str(summary_md),
    }
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Next Shadow Experiment Run Plan",
        "",
        f"- final_verdict: {summary['final_verdict']}",
        f"- plan_row_count: {summary['plan_row_count']}",
        f"- recommended_next_action: {summary['recommended_next_action']}",
        "- allowed_mode: SHADOW_ONLY",
        "- submit_permission: NO_SUBMIT",
        "- submit_attempted: false",
        "- cancel_attempted: false",
        "- flatten_attempted: false",
        "- testnet_submit_allowed: false",
        "- real_submit_allowed: false",
    ]
    summary_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate next run plan for shadow observation experiments")
    parser.add_argument("--experiment-sample-tracker-csv", default="reports/shadow_experiment_sample_tracker/experiment_sample_tracker.csv")
    parser.add_argument("--experiment-priority-rank-csv", default="reports/shadow_experiment_priorities/experiment_priority_rank.csv")
    parser.add_argument("--expansion-candidates-csv", default="reports/minimal_observation_expansion/expansion_candidates.csv")
    parser.add_argument("--shadow-scan-daily-schedule-json", default="reports/shadow_scan_schedule/shadow_scan_daily_schedule.json")
    parser.add_argument(
        "--observation-universe-expansion-review-json",
        default="reports/observation_universe_expansion/observation_universe_expansion_review.json",
    )
    parser.add_argument("--output-dir", default="reports/next_shadow_experiment_run_plan")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = generate_next_shadow_experiment_run_plan(
        experiment_sample_tracker_csv=str(
            args.experiment_sample_tracker_csv or "reports/shadow_experiment_sample_tracker/experiment_sample_tracker.csv"
        ),
        experiment_priority_rank_csv=str(
            args.experiment_priority_rank_csv or "reports/shadow_experiment_priorities/experiment_priority_rank.csv"
        ),
        expansion_candidates_csv=str(args.expansion_candidates_csv or "reports/minimal_observation_expansion/expansion_candidates.csv"),
        shadow_scan_daily_schedule_json=str(
            args.shadow_scan_daily_schedule_json or "reports/shadow_scan_schedule/shadow_scan_daily_schedule.json"
        ),
        observation_universe_expansion_review_json=str(
            args.observation_universe_expansion_review_json
            or "reports/observation_universe_expansion/observation_universe_expansion_review.json"
        ),
        output_dir=str(args.output_dir or "reports/next_shadow_experiment_run_plan"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"final_verdict={result.get('final_verdict', '')}")
    print(f"plan_row_count={result.get('plan_row_count', 0)}")


if __name__ == "__main__":
    main()
