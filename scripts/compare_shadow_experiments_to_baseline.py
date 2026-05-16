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
    "sample_count",
    "primary_horizon_evaluated_count",
    "tp_first_count",
    "sl_first_count",
    "timeout_count",
    "avg_realized_r",
    "avg_mfe_r",
    "avg_mae_r",
    "sample_lift_vs_baseline",
    "r_delta_vs_baseline",
    "risk_delta_vs_baseline",
    "comparison_verdict",
    "reason",
]


def _safe_avg(values: list[float]) -> float:
    valid = [v for v in values if math.isfinite(v)]
    if not valid:
        return float("nan")
    return sum(valid) / len(valid)


def compare_shadow_experiments_to_baseline(
    *,
    experiment_candidates_csv: str = "reports/shadow_observation_experiment_runs/experiment_candidates.csv",
    experiment_outcomes_csv: str = "reports/shadow_experiment_outcomes/experiment_outcomes.csv",
    experiment_outcomes_by_horizon_csv: str = "reports/shadow_experiment_outcomes/experiment_outcomes_by_horizon.csv",
    experiment_matrix_csv: str = "reports/shadow_observation_experiments/experiment_matrix.csv",
    output_dir: str = "reports/shadow_experiment_comparison",
) -> dict[str, Any]:
    candidate_rows = read_csv_rows(Path(experiment_candidates_csv))
    outcome_rows = read_csv_rows(Path(experiment_outcomes_csv))
    by_horizon_rows = read_csv_rows(Path(experiment_outcomes_by_horizon_csv))
    matrix_rows = read_csv_rows(Path(experiment_matrix_csv))

    candidates_by_exp: dict[str, list[dict[str, Any]]] = {}
    for row in candidate_rows:
        exp_id = str(row.get("experiment_id", "")).strip()
        if exp_id:
            candidates_by_exp.setdefault(exp_id, []).append(row)

    outcomes_by_exp: dict[str, list[dict[str, Any]]] = {}
    for row in outcome_rows:
        exp_id = str(row.get("experiment_id", "")).strip()
        if exp_id:
            outcomes_by_exp.setdefault(exp_id, []).append(row)

    by_horizon_by_exp: dict[str, list[dict[str, Any]]] = {}
    for row in by_horizon_rows:
        exp_id = str(row.get("experiment_id", "")).strip()
        if exp_id:
            by_horizon_by_exp.setdefault(exp_id, []).append(row)

    rows: list[dict[str, Any]] = []
    baseline_by_strategy: dict[str, dict[str, Any]] = {}
    for row in matrix_rows:
        exp_id = str(row.get("experiment_id", "")).strip()
        strategy_key = str(row.get("strategy_key", "")).strip()
        if not exp_id or not strategy_key:
            continue
        if str(row.get("experiment_type", "")).strip().upper() != "BASELINE_STRICT":
            continue
        items = outcomes_by_exp.get(exp_id, [])
        r_values = [to_float_nan(item.get("realized_r_multiple")) for item in items if math.isfinite(to_float_nan(item.get("realized_r_multiple")))]
        mae_values = [to_float_nan(item.get("mae_r")) for item in items if math.isfinite(to_float_nan(item.get("mae_r")))]
        baseline_by_strategy[strategy_key] = {
            "sample_count": len(candidates_by_exp.get(exp_id, [])),
            "avg_r": _safe_avg(r_values),
            "avg_mae": _safe_avg(mae_values),
        }

    for row in matrix_rows:
        exp_id = str(row.get("experiment_id", "")).strip()
        strategy_key = str(row.get("strategy_key", "")).strip()
        if not exp_id or not strategy_key:
            continue
        symbol = str(row.get("symbol", "")).strip().upper()
        side = str(row.get("side", "")).strip().upper()
        timeframe = str(row.get("timeframe", "5m")).strip() or "5m"
        experiment_type = str(row.get("experiment_type", "")).strip().upper() or "UNKNOWN"
        samples = list(candidates_by_exp.get(exp_id, []))
        outcomes = list(outcomes_by_exp.get(exp_id, []))
        by_h = list(by_horizon_by_exp.get(exp_id, []))

        sample_count = len(samples)
        primary_eval_count = len(outcomes)
        tp_count = sum(1 for item in outcomes if str(item.get("outcome", "")).strip().upper() == "SHADOW_TP_FIRST")
        sl_count = sum(1 for item in outcomes if str(item.get("outcome", "")).strip().upper() == "SHADOW_SL_FIRST")
        timeout_count = sum(
            1 for item in outcomes if str(item.get("outcome", "")).strip().upper().startswith("SHADOW_TIMEOUT_")
        )
        avg_r = _safe_avg([to_float_nan(item.get("realized_r_multiple")) for item in outcomes])
        avg_mfe = _safe_avg([to_float_nan(item.get("mfe_r")) for item in outcomes])
        avg_mae = _safe_avg([to_float_nan(item.get("mae_r")) for item in outcomes])

        baseline = baseline_by_strategy.get(strategy_key, {})
        base_sample_count = int(baseline.get("sample_count", 0) or 0)
        base_avg_r = to_float_nan(baseline.get("avg_r"))
        base_avg_mae = to_float_nan(baseline.get("avg_mae"))

        sample_lift = float(sample_count - base_sample_count)
        r_delta = (avg_r - base_avg_r) if (math.isfinite(avg_r) and math.isfinite(base_avg_r)) else float("nan")
        risk_delta = (avg_mae - base_avg_mae) if (math.isfinite(avg_mae) and math.isfinite(base_avg_mae)) else float("nan")

        reasons: list[str] = []
        verdict = "INSUFFICIENT_DATA"
        if sample_count < 5 or primary_eval_count < 5:
            reasons.append("insufficient_experiment_samples")
            verdict = "INSUFFICIENT_DATA"
        else:
            if math.isfinite(r_delta) and r_delta > 0.1 and sample_lift >= 0:
                verdict = "BETTER_THAN_BASELINE"
                reasons.append("positive_r_delta")
            elif sample_lift > 0 and (not math.isfinite(r_delta) or r_delta <= 0):
                verdict = "MORE_SAMPLES_BUT_WEAKER"
                reasons.append("sample_lift_with_nonpositive_r")
            elif math.isfinite(r_delta) and r_delta < -0.1:
                verdict = "WORSE_THAN_BASELINE"
                reasons.append("negative_r_delta")
            else:
                verdict = "NO_SIGNIFICANT_DIFFERENCE"
                reasons.append("small_delta")

        if experiment_type == "BASELINE_STRICT":
            reasons.append("baseline_reference")

        rows.append(
            {
                "experiment_id": exp_id,
                "strategy_key": strategy_key,
                "symbol": symbol,
                "side": side,
                "timeframe": timeframe,
                "experiment_type": experiment_type,
                "sample_count": sample_count,
                "primary_horizon_evaluated_count": primary_eval_count,
                "tp_first_count": tp_count,
                "sl_first_count": sl_count,
                "timeout_count": timeout_count,
                "avg_realized_r": round(avg_r, 8) if math.isfinite(avg_r) else float("nan"),
                "avg_mfe_r": round(avg_mfe, 8) if math.isfinite(avg_mfe) else float("nan"),
                "avg_mae_r": round(avg_mae, 8) if math.isfinite(avg_mae) else float("nan"),
                "sample_lift_vs_baseline": round(sample_lift, 8),
                "r_delta_vs_baseline": round(r_delta, 8) if math.isfinite(r_delta) else float("nan"),
                "risk_delta_vs_baseline": round(risk_delta, 8) if math.isfinite(risk_delta) else float("nan"),
                "comparison_verdict": verdict,
                "reason": ";".join(sorted(set(reasons))),
            }
        )

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "experiment_comparison.csv"
    summary_json = out_dir / "summary.json"
    summary_md = out_dir / "summary.md"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in FIELDS})

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "final_verdict": "PARTIAL" if rows else "PARTIAL",
        "experiment_count": len(rows),
        "insufficient_data_count": sum(
            1 for row in rows if str(row.get("comparison_verdict", "")).strip().upper() == "INSUFFICIENT_DATA"
        ),
        "better_count": sum(1 for row in rows if str(row.get("comparison_verdict", "")).strip().upper() == "BETTER_THAN_BASELINE"),
        "worse_count": sum(1 for row in rows if str(row.get("comparison_verdict", "")).strip().upper() == "WORSE_THAN_BASELINE"),
        "csv_path": str(csv_path),
        "summary_json": str(summary_json),
        "summary_md": str(summary_md),
    }
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Shadow Experiment Comparison",
        "",
        f"- final_verdict: {summary['final_verdict']}",
        f"- experiment_count: {summary['experiment_count']}",
        f"- insufficient_data_count: {summary['insufficient_data_count']}",
    ]
    summary_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compare shadow experiment groups to baseline strict")
    parser.add_argument("--experiment-candidates-csv", default="reports/shadow_observation_experiment_runs/experiment_candidates.csv")
    parser.add_argument("--experiment-outcomes-csv", default="reports/shadow_experiment_outcomes/experiment_outcomes.csv")
    parser.add_argument(
        "--experiment-outcomes-by-horizon-csv",
        default="reports/shadow_experiment_outcomes/experiment_outcomes_by_horizon.csv",
    )
    parser.add_argument("--experiment-matrix-csv", default="reports/shadow_observation_experiments/experiment_matrix.csv")
    parser.add_argument("--output-dir", default="reports/shadow_experiment_comparison")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = compare_shadow_experiments_to_baseline(
        experiment_candidates_csv=str(
            args.experiment_candidates_csv or "reports/shadow_observation_experiment_runs/experiment_candidates.csv"
        ),
        experiment_outcomes_csv=str(args.experiment_outcomes_csv or "reports/shadow_experiment_outcomes/experiment_outcomes.csv"),
        experiment_outcomes_by_horizon_csv=str(
            args.experiment_outcomes_by_horizon_csv or "reports/shadow_experiment_outcomes/experiment_outcomes_by_horizon.csv"
        ),
        experiment_matrix_csv=str(args.experiment_matrix_csv or "reports/shadow_observation_experiments/experiment_matrix.csv"),
        output_dir=str(args.output_dir or "reports/shadow_experiment_comparison"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"final_verdict={result.get('final_verdict', '')}")
    print(f"experiment_count={result.get('experiment_count', 0)}")


if __name__ == "__main__":
    main()
