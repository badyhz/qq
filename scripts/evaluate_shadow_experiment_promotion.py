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
    "comparison_verdict",
    "promotion_decision",
    "next_experiment_status",
    "risk_level",
    "required_next_samples",
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


def evaluate_shadow_experiment_promotion(
    *,
    experiment_comparison_csv: str = "reports/shadow_experiment_comparison/experiment_comparison.csv",
    experiment_matrix_csv: str = "reports/shadow_observation_experiments/experiment_matrix.csv",
    observation_experiment_dashboard_json: str = "reports/observation_experiment_dashboard/observation_experiment_dashboard.json",
    output_dir: str = "reports/shadow_experiment_promotion",
) -> dict[str, Any]:
    comparison_rows = read_csv_rows(Path(experiment_comparison_csv))
    matrix_rows = read_csv_rows(Path(experiment_matrix_csv))
    dashboard = _read_json(Path(observation_experiment_dashboard_json))

    matrix_index = {
        str(row.get("experiment_id", "")).strip(): row
        for row in matrix_rows
        if str(row.get("experiment_id", "")).strip()
    }

    rows: list[dict[str, Any]] = []
    for comp in comparison_rows:
        exp_id = str(comp.get("experiment_id", "")).strip()
        meta = matrix_index.get(exp_id, {})
        strategy_key = str(comp.get("strategy_key", meta.get("strategy_key", ""))).strip()
        symbol = str(comp.get("symbol", meta.get("symbol", ""))).strip().upper()
        side = str(comp.get("side", meta.get("side", ""))).strip().upper()
        timeframe = str(comp.get("timeframe", meta.get("timeframe", "5m"))).strip() or "5m"
        experiment_type = str(comp.get("experiment_type", meta.get("experiment_type", "UNKNOWN"))).strip().upper()
        sample_count = int(to_float_nan(comp.get("sample_count")) if str(comp.get("sample_count", "")).strip() else 0)
        comparison_verdict = str(comp.get("comparison_verdict", "INSUFFICIENT_DATA")).strip().upper() or "INSUFFICIENT_DATA"
        avg_r = to_float_nan(comp.get("avg_realized_r"))
        sl_count = int(to_float_nan(comp.get("sl_first_count")) if str(comp.get("sl_first_count", "")).strip() else 0)

        decision = "KEEP_COLLECTING"
        next_status = "WATCH_ONLY"
        risk_level = "LOW_CONFIDENCE"
        reasons: list[str] = []
        required_next_samples = max(0, 20 - sample_count)

        if sample_count < 20:
            decision = "KEEP_COLLECTING"
            reasons.append("insufficient_experiment_samples")
            risk_level = "LOW_CONFIDENCE"
        else:
            if math.isfinite(avg_r) and avg_r < -0.2:
                decision = "REJECT_EXPERIMENT"
                next_status = "REJECTED"
                risk_level = "HIGH"
                reasons.append("negative_avg_realized_r")
            elif sample_count >= 50 and math.isfinite(avg_r) and avg_r > 0.2 and sl_count <= int(sample_count * 0.45):
                decision = "PROMOTE_TO_STRICT_CANDIDATE_TEST"
                next_status = "PROMOTED"
                risk_level = "CONTROLLED"
                reasons.append("strong_sample_and_positive_r")
                required_next_samples = 0
            elif sample_count >= 20 and math.isfinite(avg_r) and avg_r > 0 and comparison_verdict in {
                "BETTER_THAN_BASELINE",
                "MORE_SAMPLES_BUT_WEAKER",
                "NO_SIGNIFICANT_DIFFERENCE",
            }:
                decision = "PROMOTE_TO_SHADOW_OBSERVATION"
                next_status = "EXPANDED"
                risk_level = "MEDIUM"
                reasons.append("eligible_for_shadow_observation_promotion")
                required_next_samples = max(0, 50 - sample_count)
            else:
                decision = "REDUCE_PRIORITY"
                next_status = "REDUCED"
                risk_level = "ELEVATED"
                reasons.append("weak_experiment_outcome")

        if comparison_verdict == "INSUFFICIENT_DATA":
            decision = "KEEP_COLLECTING"
            next_status = "WATCH_ONLY"
            risk_level = "LOW_CONFIDENCE"
            reasons.append("comparison_insufficient_data")

        rows.append(
            {
                "experiment_id": exp_id,
                "strategy_key": strategy_key,
                "symbol": symbol,
                "side": side,
                "timeframe": timeframe,
                "experiment_type": experiment_type,
                "sample_count": sample_count,
                "comparison_verdict": comparison_verdict,
                "promotion_decision": decision,
                "next_experiment_status": next_status,
                "risk_level": risk_level,
                "required_next_samples": required_next_samples,
                "reason": ";".join(sorted(set(reasons))) if reasons else "ok",
            }
        )

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "experiment_promotion_decisions.csv"
    summary_json = out_dir / "summary.json"
    summary_md = out_dir / "summary.md"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in FIELDS})

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "final_verdict": "PASS" if rows else "PARTIAL",
        "decision_count": len(rows),
        "keep_collecting_count": sum(
            1 for row in rows if str(row.get("promotion_decision", "")).strip().upper() == "KEEP_COLLECTING"
        ),
        "promote_count": sum(
            1
            for row in rows
            if str(row.get("promotion_decision", "")).strip().upper()
            in {"PROMOTE_TO_SHADOW_OBSERVATION", "PROMOTE_TO_STRICT_CANDIDATE_TEST"}
        ),
        "reject_count": sum(
            1 for row in rows if str(row.get("promotion_decision", "")).strip().upper() == "REJECT_EXPERIMENT"
        ),
        "dashboard_final_verdict": str(dashboard.get("final_verdict", "")).strip().upper() or "UNKNOWN",
        "csv_path": str(csv_path),
        "summary_json": str(summary_json),
        "summary_md": str(summary_md),
    }
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Shadow Experiment Promotion",
        "",
        f"- final_verdict: {summary['final_verdict']}",
        f"- decision_count: {summary['decision_count']}",
        f"- keep_collecting_count: {summary['keep_collecting_count']}",
        f"- promote_count: {summary['promote_count']}",
        f"- reject_count: {summary['reject_count']}",
    ]
    summary_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate promotion decisions for shadow experiments")
    parser.add_argument("--experiment-comparison-csv", default="reports/shadow_experiment_comparison/experiment_comparison.csv")
    parser.add_argument("--experiment-matrix-csv", default="reports/shadow_observation_experiments/experiment_matrix.csv")
    parser.add_argument(
        "--observation-experiment-dashboard-json",
        default="reports/observation_experiment_dashboard/observation_experiment_dashboard.json",
    )
    parser.add_argument("--output-dir", default="reports/shadow_experiment_promotion")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = evaluate_shadow_experiment_promotion(
        experiment_comparison_csv=str(
            args.experiment_comparison_csv or "reports/shadow_experiment_comparison/experiment_comparison.csv"
        ),
        experiment_matrix_csv=str(args.experiment_matrix_csv or "reports/shadow_observation_experiments/experiment_matrix.csv"),
        observation_experiment_dashboard_json=str(
            args.observation_experiment_dashboard_json
            or "reports/observation_experiment_dashboard/observation_experiment_dashboard.json"
        ),
        output_dir=str(args.output_dir or "reports/shadow_experiment_promotion"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"final_verdict={result.get('final_verdict', '')}")
    print(f"decision_count={result.get('decision_count', 0)}")


if __name__ == "__main__":
    main()
