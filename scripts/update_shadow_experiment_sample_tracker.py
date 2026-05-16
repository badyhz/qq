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
    "current_sample_count",
    "current_evaluated_count",
    "minimum_decision_samples",
    "promotion_candidate_samples",
    "strict_candidate_test_samples",
    "samples_needed_for_decision",
    "samples_needed_for_promotion",
    "next_run_sample_target",
    "priority_bucket",
    "collection_status",
    "next_action",
]


def _to_int(value: Any, default: int = 0) -> int:
    parsed = to_float_nan(value)
    if not math.isfinite(parsed):
        return int(default)
    return int(parsed)


def _priority_target(priority_bucket: str, gap: int) -> int:
    bucket = str(priority_bucket or "").strip().upper()
    if gap <= 0:
        return 0
    if bucket == "P0":
        return min(gap, 12)
    if bucket == "P1":
        return min(gap, 8)
    if bucket == "P2":
        return min(gap, 5)
    if bucket == "P3":
        return min(gap, 3)
    if bucket == "PAUSED":
        return 0
    return min(gap, 4)


def update_shadow_experiment_sample_tracker(
    *,
    experiment_history_csv: str = "reports/shadow_experiment_history/experiment_history.csv",
    experiment_priority_rank_csv: str = "reports/shadow_experiment_priorities/experiment_priority_rank.csv",
    experiment_promotion_decisions_csv: str = "reports/shadow_experiment_promotion/experiment_promotion_decisions.csv",
    experiment_matrix_csv: str = "reports/shadow_observation_experiments/experiment_matrix.csv",
    output_dir: str = "reports/shadow_experiment_sample_tracker",
) -> dict[str, Any]:
    history_rows = read_csv_rows(Path(experiment_history_csv))
    priority_rows = read_csv_rows(Path(experiment_priority_rank_csv))
    promotion_rows = read_csv_rows(Path(experiment_promotion_decisions_csv))
    matrix_rows = read_csv_rows(Path(experiment_matrix_csv))

    latest_by_exp: dict[str, dict[str, Any]] = {}
    for row in sorted(history_rows, key=lambda item: (str(item.get("run_date", "")), str(item.get("created_at", "")))):
        exp_id = str(row.get("experiment_id", "")).strip()
        if exp_id:
            latest_by_exp[exp_id] = row

    priority_by_exp = {
        str(row.get("experiment_id", "")).strip(): row
        for row in priority_rows
        if str(row.get("experiment_id", "")).strip()
    }
    promotion_by_exp = {
        str(row.get("experiment_id", "")).strip(): row
        for row in promotion_rows
        if str(row.get("experiment_id", "")).strip()
    }
    matrix_by_exp = {
        str(row.get("experiment_id", "")).strip(): row
        for row in matrix_rows
        if str(row.get("experiment_id", "")).strip()
    }

    experiment_ids = sorted(set(matrix_by_exp.keys()) | set(latest_by_exp.keys()) | set(priority_by_exp.keys()) | set(promotion_by_exp.keys()))
    out_rows: list[dict[str, Any]] = []
    for exp_id in experiment_ids:
        latest = latest_by_exp.get(exp_id, {})
        priority = priority_by_exp.get(exp_id, {})
        promotion = promotion_by_exp.get(exp_id, {})
        matrix = matrix_by_exp.get(exp_id, {})
        base = latest if latest else (priority if priority else (promotion if promotion else matrix))

        current_sample_count = _to_int(latest.get("sample_count"), _to_int(priority.get("sample_count"), 0))
        current_evaluated_count = _to_int(latest.get("evaluated_count"), _to_int(priority.get("primary_horizon_evaluated_count"), 0))
        minimum_decision_samples = 20
        promotion_candidate_samples = 20
        strict_candidate_test_samples = 50
        samples_needed_for_decision = max(0, minimum_decision_samples - current_sample_count)
        samples_needed_for_promotion = max(0, strict_candidate_test_samples - current_sample_count)
        priority_bucket = str(priority.get("priority_bucket", "P2")).strip().upper() or "P2"
        promotion_decision = str(promotion.get("promotion_decision", "KEEP_COLLECTING")).strip().upper() or "KEEP_COLLECTING"

        collection_status = "COLLECTING"
        next_action = "collect_more_shadow_experiment_samples"
        if promotion_decision == "REJECT_EXPERIMENT" or priority_bucket == "PAUSED":
            collection_status = "PAUSED"
            next_action = "pause_experiment_and_review"
        elif current_sample_count <= 0:
            collection_status = "NOT_STARTED"
            next_action = "collect_more_shadow_experiment_samples"
        elif current_sample_count < minimum_decision_samples:
            collection_status = "MINIMUM_NOT_MET"
            next_action = "collect_more_shadow_experiment_samples"
        elif current_sample_count < strict_candidate_test_samples:
            collection_status = "DECISION_READY"
            next_action = "collect_more_shadow_experiment_samples"
        else:
            collection_status = "PROMOTION_READY"
            next_action = "review_for_shadow_promotion"

        next_run_sample_target = _priority_target(priority_bucket, samples_needed_for_decision)
        if collection_status == "PAUSED":
            next_run_sample_target = 0

        out_rows.append(
            {
                "experiment_id": exp_id,
                "strategy_key": str(base.get("strategy_key", "")).strip(),
                "symbol": str(base.get("symbol", "")).strip().upper(),
                "side": str(base.get("side", "")).strip().upper(),
                "timeframe": str(base.get("timeframe", "5m")).strip() or "5m",
                "experiment_type": str(base.get("experiment_type", "UNKNOWN")).strip().upper() or "UNKNOWN",
                "current_sample_count": current_sample_count,
                "current_evaluated_count": current_evaluated_count,
                "minimum_decision_samples": minimum_decision_samples,
                "promotion_candidate_samples": promotion_candidate_samples,
                "strict_candidate_test_samples": strict_candidate_test_samples,
                "samples_needed_for_decision": samples_needed_for_decision,
                "samples_needed_for_promotion": samples_needed_for_promotion,
                "next_run_sample_target": next_run_sample_target,
                "priority_bucket": priority_bucket,
                "collection_status": collection_status,
                "next_action": next_action,
            }
        )

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "experiment_sample_tracker.csv"
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
        "experiment_count": len(out_rows),
        "minimum_not_met_count": sum(
            1 for row in out_rows if str(row.get("collection_status", "")).strip().upper() == "MINIMUM_NOT_MET"
        ),
        "collecting_count": sum(
            1
            for row in out_rows
            if str(row.get("collection_status", "")).strip().upper() in {"COLLECTING", "MINIMUM_NOT_MET", "NOT_STARTED"}
        ),
        "promotion_ready_count": sum(
            1 for row in out_rows if str(row.get("collection_status", "")).strip().upper() == "PROMOTION_READY"
        ),
        "total_next_run_sample_target": sum(max(0, _to_int(row.get("next_run_sample_target"), 0)) for row in out_rows),
        "csv_path": str(csv_path),
        "summary_json": str(summary_json),
        "summary_md": str(summary_md),
    }
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Shadow Experiment Sample Tracker",
        "",
        f"- final_verdict: {summary['final_verdict']}",
        f"- experiment_count: {summary['experiment_count']}",
        f"- minimum_not_met_count: {summary['minimum_not_met_count']}",
        f"- collecting_count: {summary['collecting_count']}",
        f"- promotion_ready_count: {summary['promotion_ready_count']}",
        f"- total_next_run_sample_target: {summary['total_next_run_sample_target']}",
    ]
    summary_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Update sample target tracker for shadow experiments")
    parser.add_argument("--experiment-history-csv", default="reports/shadow_experiment_history/experiment_history.csv")
    parser.add_argument("--experiment-priority-rank-csv", default="reports/shadow_experiment_priorities/experiment_priority_rank.csv")
    parser.add_argument(
        "--experiment-promotion-decisions-csv",
        default="reports/shadow_experiment_promotion/experiment_promotion_decisions.csv",
    )
    parser.add_argument("--experiment-matrix-csv", default="reports/shadow_observation_experiments/experiment_matrix.csv")
    parser.add_argument("--output-dir", default="reports/shadow_experiment_sample_tracker")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = update_shadow_experiment_sample_tracker(
        experiment_history_csv=str(args.experiment_history_csv or "reports/shadow_experiment_history/experiment_history.csv"),
        experiment_priority_rank_csv=str(
            args.experiment_priority_rank_csv or "reports/shadow_experiment_priorities/experiment_priority_rank.csv"
        ),
        experiment_promotion_decisions_csv=str(
            args.experiment_promotion_decisions_csv
            or "reports/shadow_experiment_promotion/experiment_promotion_decisions.csv"
        ),
        experiment_matrix_csv=str(args.experiment_matrix_csv or "reports/shadow_observation_experiments/experiment_matrix.csv"),
        output_dir=str(args.output_dir or "reports/shadow_experiment_sample_tracker"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"final_verdict={result.get('final_verdict', '')}")
    print(f"experiment_count={result.get('experiment_count', 0)}")


if __name__ == "__main__":
    main()
