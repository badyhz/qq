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
    "history_run_count",
    "total_sample_count",
    "total_evaluated_count",
    "avg_realized_r",
    "r_std",
    "horizon_consistency_score",
    "sl_first_rate",
    "sample_confidence_level",
    "stability_score",
    "stability_grade",
    "stability_verdict",
    "reason",
]


def _safe_avg(values: list[float]) -> float:
    valid = [v for v in values if math.isfinite(v)]
    if not valid:
        return float("nan")
    return sum(valid) / len(valid)


def _safe_std(values: list[float]) -> float:
    valid = [v for v in values if math.isfinite(v)]
    if len(valid) < 2:
        return float("nan")
    mean = sum(valid) / len(valid)
    variance = sum((v - mean) ** 2 for v in valid) / len(valid)
    return math.sqrt(max(0.0, variance))


def _sample_level(count: int) -> str:
    if count < 5:
        return "TOO_SMALL"
    if count < 20:
        return "LOW"
    if count < 50:
        return "MEDIUM"
    return "HIGH"


def _to_int(value: Any, default: int = 0) -> int:
    parsed = to_float_nan(value)
    if not math.isfinite(parsed):
        return int(default)
    return int(parsed)


def _grade(score: float) -> str:
    if score >= 80:
        return "A"
    if score >= 70:
        return "B"
    if score >= 60:
        return "C"
    if score >= 50:
        return "D"
    return "F"


def calculate_shadow_experiment_stability_score(
    *,
    experiment_history_csv: str = "reports/shadow_experiment_history/experiment_history.csv",
    experiment_comparison_csv: str = "reports/shadow_experiment_comparison/experiment_comparison.csv",
    experiment_outcomes_by_horizon_csv: str = "reports/shadow_experiment_outcomes/experiment_outcomes_by_horizon.csv",
    experiment_promotion_decisions_csv: str = "reports/shadow_experiment_promotion/experiment_promotion_decisions.csv",
    output_dir: str = "reports/shadow_experiment_stability",
) -> dict[str, Any]:
    history_rows = read_csv_rows(Path(experiment_history_csv))
    comparison_rows = read_csv_rows(Path(experiment_comparison_csv))
    horizon_rows = read_csv_rows(Path(experiment_outcomes_by_horizon_csv))
    promotion_rows = read_csv_rows(Path(experiment_promotion_decisions_csv))

    history_by_exp: dict[str, list[dict[str, Any]]] = {}
    for row in history_rows:
        exp_id = str(row.get("experiment_id", "")).strip()
        if exp_id:
            history_by_exp.setdefault(exp_id, []).append(row)

    comparison_by_exp: dict[str, dict[str, Any]] = {}
    for row in comparison_rows:
        exp_id = str(row.get("experiment_id", "")).strip()
        if exp_id:
            comparison_by_exp[exp_id] = row

    promotion_by_exp: dict[str, dict[str, Any]] = {}
    for row in promotion_rows:
        exp_id = str(row.get("experiment_id", "")).strip()
        if exp_id:
            promotion_by_exp[exp_id] = row

    horizon_by_exp: dict[str, list[dict[str, Any]]] = {}
    for row in horizon_rows:
        exp_id = str(row.get("experiment_id", "")).strip()
        if exp_id:
            horizon_by_exp.setdefault(exp_id, []).append(row)

    experiment_ids = sorted(set(history_by_exp.keys()) | set(comparison_by_exp.keys()) | set(promotion_by_exp.keys()))
    out_rows: list[dict[str, Any]] = []
    for exp_id in experiment_ids:
        hrows = list(history_by_exp.get(exp_id, []))
        comp = comparison_by_exp.get(exp_id, {})
        promo = promotion_by_exp.get(exp_id, {})
        hhz = list(horizon_by_exp.get(exp_id, []))
        first = hrows[0] if hrows else (comp if comp else promo)

        realized_series = [to_float_nan(row.get("avg_realized_r")) for row in hrows]
        avg_realized_r = _safe_avg(realized_series)
        r_std = _safe_std(realized_series)
        total_sample_count = sum(max(0, _to_int(row.get("sample_count"), 0)) for row in hrows)
        total_evaluated_count = sum(max(0, _to_int(row.get("evaluated_count"), 0)) for row in hrows)
        if total_sample_count <= 0:
            total_sample_count = max(0, _to_int(comp.get("sample_count"), 0))
        if total_evaluated_count <= 0:
            total_evaluated_count = max(0, _to_int(comp.get("primary_horizon_evaluated_count"), 0))
        history_run_count = len(hrows)
        sample_confidence_level = _sample_level(total_sample_count)

        sl_first = max(0, _to_int(comp.get("sl_first_count"), 0))
        sample_count_for_risk = max(0, _to_int(comp.get("sample_count"), 0))
        sl_first_rate = float("nan")
        if sample_count_for_risk > 0:
            sl_first_rate = sl_first / sample_count_for_risk

        horizon_r_values = [to_float_nan(row.get("realized_r_multiple")) for row in hhz]
        horizon_std = _safe_std(horizon_r_values)
        horizon_consistency_score = float("nan")
        if math.isfinite(horizon_std):
            horizon_consistency_score = max(0.0, min(100.0, 100.0 - (horizon_std * 120.0)))

        sample_component = max(0.0, min(100.0, (total_sample_count / 50.0) * 100.0))
        r_stability_component = 0.0 if not math.isfinite(r_std) else max(0.0, min(100.0, 100.0 - (r_std * 150.0)))
        horizon_component = horizon_consistency_score if math.isfinite(horizon_consistency_score) else 0.0
        risk_component = 0.0 if not math.isfinite(sl_first_rate) else max(0.0, min(100.0, (1.0 - sl_first_rate) * 100.0))
        cross_run_component = max(0.0, min(100.0, (history_run_count / 10.0) * 100.0))
        stability_score = (
            sample_component * 0.30
            + r_stability_component * 0.25
            + horizon_component * 0.20
            + risk_component * 0.15
            + cross_run_component * 0.10
        )
        stability_grade = _grade(stability_score)

        reasons: list[str] = []
        verdict = "UNKNOWN"
        if total_sample_count < 20 or total_evaluated_count < 10:
            verdict = "NEEDS_MORE_DATA"
            reasons.append("insufficient_experiment_samples")
        elif math.isfinite(avg_realized_r) and avg_realized_r < -0.1 and math.isfinite(sl_first_rate) and sl_first_rate >= 0.5:
            verdict = "UNSTABLE_BAD"
            reasons.append("negative_r_with_high_sl_first_rate")
        elif stability_score >= 70 and math.isfinite(avg_realized_r) and avg_realized_r > 0:
            verdict = "STABLE_PROMISING"
            reasons.append("stable_positive_signal")
        elif math.isfinite(avg_realized_r) and avg_realized_r > 0:
            verdict = "UNSTABLE_PROMISING"
            reasons.append("positive_but_not_stable")
        else:
            verdict = "UNSTABLE_BAD"
            reasons.append("weak_or_negative_signal")

        if str(promo.get("promotion_decision", "")).strip().upper() == "KEEP_COLLECTING" and verdict != "STABLE_PROMISING":
            reasons.append("promotion_not_ready")

        out_rows.append(
            {
                "experiment_id": exp_id,
                "strategy_key": str(first.get("strategy_key", "")).strip(),
                "symbol": str(first.get("symbol", "")).strip().upper(),
                "side": str(first.get("side", "")).strip().upper(),
                "timeframe": str(first.get("timeframe", "5m")).strip() or "5m",
                "experiment_type": str(first.get("experiment_type", "UNKNOWN")).strip().upper() or "UNKNOWN",
                "history_run_count": history_run_count,
                "total_sample_count": total_sample_count,
                "total_evaluated_count": total_evaluated_count,
                "avg_realized_r": round(avg_realized_r, 8) if math.isfinite(avg_realized_r) else float("nan"),
                "r_std": round(r_std, 8) if math.isfinite(r_std) else float("nan"),
                "horizon_consistency_score": round(horizon_consistency_score, 8)
                if math.isfinite(horizon_consistency_score)
                else float("nan"),
                "sl_first_rate": round(sl_first_rate, 8) if math.isfinite(sl_first_rate) else float("nan"),
                "sample_confidence_level": sample_confidence_level,
                "stability_score": round(stability_score, 8),
                "stability_grade": stability_grade,
                "stability_verdict": verdict,
                "reason": ";".join(sorted(set(reasons))) if reasons else "ok",
            }
        )

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "stability_scores.csv"
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
        "needs_more_data_count": sum(
            1 for row in out_rows if str(row.get("stability_verdict", "")).strip().upper() == "NEEDS_MORE_DATA"
        ),
        "stable_promising_count": sum(
            1 for row in out_rows if str(row.get("stability_verdict", "")).strip().upper() == "STABLE_PROMISING"
        ),
        "unstable_bad_count": sum(
            1 for row in out_rows if str(row.get("stability_verdict", "")).strip().upper() == "UNSTABLE_BAD"
        ),
        "avg_stability_score": _safe_avg([to_float_nan(row.get("stability_score")) for row in out_rows]),
        "csv_path": str(csv_path),
        "summary_json": str(summary_json),
        "summary_md": str(summary_md),
    }
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Shadow Experiment Stability",
        "",
        f"- final_verdict: {summary['final_verdict']}",
        f"- experiment_count: {summary['experiment_count']}",
        f"- needs_more_data_count: {summary['needs_more_data_count']}",
        f"- stable_promising_count: {summary['stable_promising_count']}",
        f"- unstable_bad_count: {summary['unstable_bad_count']}",
    ]
    summary_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Calculate stability score for shadow experiments")
    parser.add_argument("--experiment-history-csv", default="reports/shadow_experiment_history/experiment_history.csv")
    parser.add_argument("--experiment-comparison-csv", default="reports/shadow_experiment_comparison/experiment_comparison.csv")
    parser.add_argument(
        "--experiment-outcomes-by-horizon-csv",
        default="reports/shadow_experiment_outcomes/experiment_outcomes_by_horizon.csv",
    )
    parser.add_argument(
        "--experiment-promotion-decisions-csv",
        default="reports/shadow_experiment_promotion/experiment_promotion_decisions.csv",
    )
    parser.add_argument("--output-dir", default="reports/shadow_experiment_stability")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = calculate_shadow_experiment_stability_score(
        experiment_history_csv=str(args.experiment_history_csv or "reports/shadow_experiment_history/experiment_history.csv"),
        experiment_comparison_csv=str(
            args.experiment_comparison_csv or "reports/shadow_experiment_comparison/experiment_comparison.csv"
        ),
        experiment_outcomes_by_horizon_csv=str(
            args.experiment_outcomes_by_horizon_csv or "reports/shadow_experiment_outcomes/experiment_outcomes_by_horizon.csv"
        ),
        experiment_promotion_decisions_csv=str(
            args.experiment_promotion_decisions_csv
            or "reports/shadow_experiment_promotion/experiment_promotion_decisions.csv"
        ),
        output_dir=str(args.output_dir or "reports/shadow_experiment_stability"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"final_verdict={result.get('final_verdict', '')}")
    print(f"experiment_count={result.get('experiment_count', 0)}")


if __name__ == "__main__":
    main()
