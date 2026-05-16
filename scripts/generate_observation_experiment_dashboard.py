from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.strategy_edge_common import read_csv_rows, to_float_nan


BY_EXPERIMENT_FIELDS = [
    "experiment_id",
    "strategy_key",
    "symbol",
    "side",
    "timeframe",
    "experiment_type",
    "experiment_status",
    "sample_target",
    "current_observation_samples",
    "matched_observation_samples",
    "avg_near_miss_quality_score",
    "avg_primary_horizon_realized_r",
    "experiment_verdict",
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


def _safe_avg(values: list[float]) -> float:
    valid = [v for v in values if math.isfinite(v)]
    if not valid:
        return float("nan")
    return sum(valid) / len(valid)


def _match_experiment_rows(experiment: dict[str, Any], samples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    strategy_key = str(experiment.get("strategy_key", "")).strip()
    mode = str(experiment.get("collector_mode", "")).strip().lower()
    exp_type = str(experiment.get("experiment_type", "")).strip().upper()
    matched: list[dict[str, Any]] = []
    for sample in samples:
        if str(sample.get("strategy_key", "")).strip() != strategy_key:
            continue
        sample_mode = str(sample.get("collector_mode", "")).strip().lower()
        is_near = str(sample.get("near_miss", "")).strip().lower() in {"1", "true", "yes", "y"}
        if exp_type == "BASELINE_STRICT":
            if sample_mode != "strict":
                continue
        elif exp_type in {"RELAX_NEAR_MISS", "RELAX_BREAKOUT", "RELAX_TREND", "RELAX_RISK_REWARD", "COMBINED_RELAXATION"}:
            if not is_near:
                continue
            if mode and sample_mode and sample_mode != mode:
                continue
        matched.append(sample)
    return matched


def generate_observation_experiment_dashboard(
    *,
    experiment_matrix_csv: str = "reports/shadow_observation_experiments/experiment_matrix.csv",
    observation_samples_csv: str = "reports/observation_sample_store/observation_samples.csv",
    strategy_relaxation_suggestions_csv: str = "reports/strategy_relaxation_suggestions/strategy_relaxation_suggestions.csv",
    near_miss_strict_gap_csv: str = "reports/near_miss_strict_gap/near_miss_strict_gap.csv",
    output_dir: str = "reports/observation_experiment_dashboard",
) -> dict[str, Any]:
    matrix_rows = read_csv_rows(Path(experiment_matrix_csv))
    observation_rows = read_csv_rows(Path(observation_samples_csv))
    suggestion_rows = read_csv_rows(Path(strategy_relaxation_suggestions_csv))
    gap_rows = read_csv_rows(Path(near_miss_strict_gap_csv))

    suggestions_by_key = {
        str(row.get("strategy_key", "")).strip(): row
        for row in suggestion_rows
        if str(row.get("strategy_key", "")).strip()
    }
    gap_by_key: dict[str, list[dict[str, Any]]] = {}
    for row in gap_rows:
        key = str(row.get("strategy_key", "")).strip()
        if key:
            gap_by_key.setdefault(key, []).append(row)

    current_counts: dict[str, int] = {}
    for row in observation_rows:
        key = str(row.get("strategy_key", "")).strip()
        if key:
            current_counts[key] = int(current_counts.get(key, 0)) + 1

    by_rows: list[dict[str, Any]] = []
    for exp in matrix_rows:
        strategy_key = str(exp.get("strategy_key", "")).strip()
        matched = _match_experiment_rows(exp, observation_rows)
        q_values = [to_float_nan(row.get("near_miss_quality_score")) for row in matched]
        r_values = [to_float_nan(row.get("primary_horizon_realized_r")) for row in matched]
        avg_q = _safe_avg(q_values)
        avg_r = _safe_avg(r_values)
        sample_target = int(to_float_nan(exp.get("sample_target")) if str(exp.get("sample_target", "")).strip() else 0)
        status = str(exp.get("experiment_status", "WATCH_ONLY")).strip().upper() or "WATCH_ONLY"
        suggestion = suggestions_by_key.get(strategy_key, {})
        gap_items = gap_by_key.get(strategy_key, [])
        reasons: list[str] = []
        verdict = "INSUFFICIENT_DATA"
        if len(matched) <= 0:
            reasons.append("no_matched_observation_samples")
        else:
            if math.isfinite(avg_r) and avg_r > 0 and math.isfinite(avg_q) and avg_q >= 60:
                verdict = "WATCH"
                reasons.append("positive_observation_signal")
            elif math.isfinite(avg_r) and avg_r < -0.2:
                verdict = "REJECT"
                reasons.append("negative_observation_signal")
            else:
                verdict = "WATCH"
                reasons.append("mixed_observation_signal")
        if status == "INSUFFICIENT_DATA":
            verdict = "INSUFFICIENT_DATA"
            reasons.append("experiment_status_insufficient_data")
        if str(suggestion.get("suggestion_verdict", "")).strip().upper() in {"INSUFFICIENT_DATA", "WATCH_ONLY"}:
            reasons.append("suggestion_not_ready")
        if len(gap_items) < 3:
            reasons.append("need_more_observation_samples")

        by_rows.append(
            {
                "experiment_id": str(exp.get("experiment_id", "")).strip(),
                "strategy_key": strategy_key,
                "symbol": str(exp.get("symbol", "")).strip().upper(),
                "side": str(exp.get("side", "")).strip().upper(),
                "timeframe": str(exp.get("timeframe", "5m")).strip() or "5m",
                "experiment_type": str(exp.get("experiment_type", "")).strip().upper(),
                "experiment_status": status,
                "sample_target": sample_target,
                "current_observation_samples": int(current_counts.get(strategy_key, 0)),
                "matched_observation_samples": len(matched),
                "avg_near_miss_quality_score": round(avg_q, 8) if math.isfinite(avg_q) else float("nan"),
                "avg_primary_horizon_realized_r": round(avg_r, 8) if math.isfinite(avg_r) else float("nan"),
                "experiment_verdict": verdict,
                "reason": ";".join(sorted(set(reasons))) if reasons else "ok",
            }
        )

    experiment_count = len(matrix_rows)
    watch_only_count = sum(1 for row in matrix_rows if str(row.get("experiment_status", "")).strip().upper() == "WATCH_ONLY")
    insufficient_data_count = sum(
        1 for row in matrix_rows if str(row.get("experiment_status", "")).strip().upper() == "INSUFFICIENT_DATA"
    )
    active_experiment_count = sum(
        1
        for row in matrix_rows
        if str(row.get("experiment_status", "")).strip().upper() in {"WATCH_ONLY", "EXPERIMENT_ALLOWED", "ACTIVE"}
    )
    observation_sample_count = len(observation_rows)

    operator_attention: list[str] = []
    if observation_sample_count < 5:
        operator_attention.append("need_more_observation_samples")
    if insufficient_data_count > 0:
        operator_attention.append("experiments_insufficient_data")

    final_verdict = "PASS"
    if observation_sample_count <= 0 or insufficient_data_count > 0:
        final_verdict = "PARTIAL"
    if experiment_count <= 0:
        final_verdict = "PARTIAL"
        operator_attention.append("no_experiments_defined")

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    dashboard_json = out_dir / "observation_experiment_dashboard.json"
    by_experiment_csv = out_dir / "by_experiment.csv"
    summary_md = out_dir / "summary.md"

    with by_experiment_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=BY_EXPERIMENT_FIELDS)
        writer.writeheader()
        for row in by_rows:
            writer.writerow({field: row.get(field, "") for field in BY_EXPERIMENT_FIELDS})

    dashboard = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "final_verdict": final_verdict,
        "experiment_count": experiment_count,
        "active_experiment_count": active_experiment_count,
        "watch_only_count": watch_only_count,
        "insufficient_data_count": insufficient_data_count,
        "observation_sample_count": observation_sample_count,
        "safe_to_run_shadow_experiments": True,
        "submit_allowed": False,
        "real_submit_allowed": False,
        "operator_attention": sorted(set(operator_attention)),
        "by_experiment_csv": str(by_experiment_csv),
        "summary_md": str(summary_md),
    }
    dashboard_json.write_text(json.dumps(dashboard, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Observation Experiment Dashboard",
        "",
        f"- final_verdict: {dashboard['final_verdict']}",
        f"- experiment_count: {dashboard['experiment_count']}",
        f"- active_experiment_count: {dashboard['active_experiment_count']}",
        f"- watch_only_count: {dashboard['watch_only_count']}",
        f"- insufficient_data_count: {dashboard['insufficient_data_count']}",
        f"- observation_sample_count: {dashboard['observation_sample_count']}",
        "- safe_to_run_shadow_experiments: true",
        "- submit_allowed: false",
        "- real_submit_allowed: false",
    ]
    if operator_attention:
        lines.append(f"- operator_attention: {', '.join(sorted(set(operator_attention)))}")
    summary_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return dashboard


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate dashboard for shadow observation experiments")
    parser.add_argument("--experiment-matrix-csv", default="reports/shadow_observation_experiments/experiment_matrix.csv")
    parser.add_argument("--observation-samples-csv", default="reports/observation_sample_store/observation_samples.csv")
    parser.add_argument("--strategy-relaxation-suggestions-csv", default="reports/strategy_relaxation_suggestions/strategy_relaxation_suggestions.csv")
    parser.add_argument("--near-miss-strict-gap-csv", default="reports/near_miss_strict_gap/near_miss_strict_gap.csv")
    parser.add_argument("--output-dir", default="reports/observation_experiment_dashboard")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = generate_observation_experiment_dashboard(
        experiment_matrix_csv=str(args.experiment_matrix_csv or "reports/shadow_observation_experiments/experiment_matrix.csv"),
        observation_samples_csv=str(args.observation_samples_csv or "reports/observation_sample_store/observation_samples.csv"),
        strategy_relaxation_suggestions_csv=str(
            args.strategy_relaxation_suggestions_csv or "reports/strategy_relaxation_suggestions/strategy_relaxation_suggestions.csv"
        ),
        near_miss_strict_gap_csv=str(args.near_miss_strict_gap_csv or "reports/near_miss_strict_gap/near_miss_strict_gap.csv"),
        output_dir=str(args.output_dir or "reports/observation_experiment_dashboard"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"final_verdict={result.get('final_verdict', '')}")
    print(f"experiment_count={result.get('experiment_count', 0)}")


if __name__ == "__main__":
    main()
