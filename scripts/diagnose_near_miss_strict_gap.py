from __future__ import annotations

import argparse
import csv
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.execution_guards import assert_dry_run_required, normalize_execution_mode
from scripts.strategy_edge_common import read_csv_rows, to_float_nan


FIELDS = [
    "observation_sample_id",
    "shadow_candidate_id",
    "symbol",
    "side",
    "timeframe",
    "strategy_key",
    "trend_score",
    "breakout_score",
    "risk_reward_score",
    "signal_strength_score",
    "failed_dimension",
    "gap_to_strict_threshold",
    "gap_severity",
    "primary_gap_reason",
    "secondary_gap_reasons",
    "suggested_relaxation_type",
    "safe_to_experiment",
    "reason",
]


def _failed_dimension(*, trend_gap: float, breakout_gap: float, rr_gap: float) -> str:
    fails = [
        ("TREND", trend_gap > 0),
        ("BREAKOUT", breakout_gap > 0),
        ("RISK_REWARD", rr_gap > 0),
    ]
    failed = [name for name, flag in fails if flag]
    if not failed:
        return "UNKNOWN"
    if len(failed) > 1:
        return "MULTIPLE"
    return failed[0]


def _gap_severity(value: float) -> str:
    if not math.isfinite(value):
        return "UNKNOWN"
    if value <= 10.0:
        return "SMALL"
    if value <= 25.0:
        return "MEDIUM"
    return "LARGE"


def _suggest_relax_type(failed_dimension: str, near_miss_reason: str) -> str:
    reason = str(near_miss_reason or "").strip().lower()
    if failed_dimension == "TREND" or "trend" in reason:
        return "RELAX_TREND_SCORE"
    if failed_dimension == "BREAKOUT" or "breakout" in reason:
        return "RELAX_BREAKOUT_SCORE"
    if failed_dimension == "RISK_REWARD" or "risk_reward" in reason or "risk-reward" in reason:
        return "RELAX_RISK_REWARD"
    if failed_dimension == "MULTIPLE":
        return "RELAX_NEAR_MISS_THRESHOLD"
    return "KEEP_STRICT"


def diagnose_near_miss_strict_gap(
    *,
    observation_samples_csv: str = "reports/observation_sample_store/observation_samples.csv",
    shadow_universe_candidates_csv: str = "reports/shadow_universe_collection/shadow_universe_candidates.csv",
    near_miss_scores_csv: str = "reports/shadow_near_miss/near_miss_scores.csv",
    output_dir: str = "reports/near_miss_strict_gap",
    min_trend_score: float = 60.0,
    min_breakout_score: float = 60.0,
    min_risk_reward_score: float = 60.0,
) -> dict[str, Any]:
    observation_rows = read_csv_rows(Path(observation_samples_csv))
    _ = read_csv_rows(Path(shadow_universe_candidates_csv))
    near_rows = read_csv_rows(Path(near_miss_scores_csv))
    near_index = {
        str(row.get("shadow_candidate_id", "")).strip(): row
        for row in near_rows
        if str(row.get("shadow_candidate_id", "")).strip()
    }

    per_strategy_counts: dict[str, int] = {}
    for row in observation_rows:
        key = str(row.get("strategy_key", "")).strip()
        if key:
            per_strategy_counts[key] = int(per_strategy_counts.get(key, 0)) + 1

    out_rows: list[dict[str, Any]] = []
    for row in observation_rows:
        cid = str(row.get("shadow_candidate_id", "")).strip()
        near_row = near_index.get(cid, {})
        trend_score = to_float_nan(row.get("trend_score", near_row.get("trend_score")))
        breakout_score = to_float_nan(row.get("breakout_score", near_row.get("breakout_score")))
        rr_score = to_float_nan(row.get("risk_reward_score", near_row.get("risk_reward_score")))
        signal_strength = to_float_nan(row.get("signal_strength_score", near_row.get("signal_strength_score")))
        trend_gap = max(0.0, float(min_trend_score) - trend_score) if math.isfinite(trend_score) else float("nan")
        breakout_gap = max(0.0, float(min_breakout_score) - breakout_score) if math.isfinite(breakout_score) else float("nan")
        rr_gap = max(0.0, float(min_risk_reward_score) - rr_score) if math.isfinite(rr_score) else float("nan")
        failed_dimension = _failed_dimension(trend_gap=trend_gap if math.isfinite(trend_gap) else 0.0, breakout_gap=breakout_gap if math.isfinite(breakout_gap) else 0.0, rr_gap=rr_gap if math.isfinite(rr_gap) else 0.0)
        max_gap = max([gap for gap in [trend_gap, breakout_gap, rr_gap] if math.isfinite(gap)] + [float("nan")])
        gap_severity = _gap_severity(max_gap)
        near_reason = str(row.get("near_miss_reason", near_row.get("near_miss_reason", ""))).strip()
        primary_gap_reason = near_reason or failed_dimension.lower()
        secondary = []
        if failed_dimension == "MULTIPLE":
            if math.isfinite(trend_gap) and trend_gap > 0:
                secondary.append("trend")
            if math.isfinite(breakout_gap) and breakout_gap > 0:
                secondary.append("breakout")
            if math.isfinite(rr_gap) and rr_gap > 0:
                secondary.append("risk_reward")
        suggested = _suggest_relax_type(failed_dimension, near_reason)
        promotion_hint = str(row.get("near_miss_promotion_hint", near_row.get("near_miss_promotion_hint", ""))).strip().upper()
        primary_r = to_float_nan(row.get("primary_horizon_realized_r", near_row.get("primary_horizon_realized_r")))
        strategy_key = str(row.get("strategy_key", "")).strip()
        sample_count = int(per_strategy_counts.get(strategy_key, 0))
        safe_to_experiment = (
            gap_severity == "SMALL"
            and promotion_hint not in {"IGNORE"}
            and (not math.isfinite(primary_r) or primary_r > -0.2)
            and sample_count >= 3
        )
        reasons: list[str] = []
        if sample_count < 3:
            reasons.append("insufficient_observation_samples")
        if promotion_hint == "IGNORE":
            reasons.append("promotion_hint_ignore")
        if math.isfinite(primary_r) and primary_r <= -0.2:
            reasons.append("negative_outcome")
        if failed_dimension == "UNKNOWN":
            reasons.append("unable_to_classify_gap")
        if not reasons:
            reasons.append("safe_small_gap")

        out_rows.append(
            {
                "observation_sample_id": str(row.get("observation_sample_id", f"obs_{cid}")).strip(),
                "shadow_candidate_id": cid,
                "symbol": str(row.get("symbol", "")).strip().upper(),
                "side": str(row.get("side", "")).strip().upper(),
                "timeframe": str(row.get("timeframe", "5m")).strip() or "5m",
                "strategy_key": strategy_key,
                "trend_score": round(trend_score, 8) if math.isfinite(trend_score) else float("nan"),
                "breakout_score": round(breakout_score, 8) if math.isfinite(breakout_score) else float("nan"),
                "risk_reward_score": round(rr_score, 8) if math.isfinite(rr_score) else float("nan"),
                "signal_strength_score": round(signal_strength, 8) if math.isfinite(signal_strength) else float("nan"),
                "failed_dimension": failed_dimension,
                "gap_to_strict_threshold": round(max_gap, 8) if math.isfinite(max_gap) else float("nan"),
                "gap_severity": gap_severity,
                "primary_gap_reason": primary_gap_reason,
                "secondary_gap_reasons": ";".join(secondary),
                "suggested_relaxation_type": suggested,
                "safe_to_experiment": bool(safe_to_experiment),
                "reason": ";".join(sorted(set(reasons))),
            }
        )

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "near_miss_strict_gap.csv"
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
        "row_count": len(out_rows),
        "safe_to_experiment_count": sum(1 for row in out_rows if str(row.get("safe_to_experiment")).strip().lower() in {"true", "1"}),
        "failed_dimension_counts": {
            "TREND": sum(1 for row in out_rows if str(row.get("failed_dimension", "")).strip().upper() == "TREND"),
            "BREAKOUT": sum(1 for row in out_rows if str(row.get("failed_dimension", "")).strip().upper() == "BREAKOUT"),
            "RISK_REWARD": sum(1 for row in out_rows if str(row.get("failed_dimension", "")).strip().upper() == "RISK_REWARD"),
            "MULTIPLE": sum(1 for row in out_rows if str(row.get("failed_dimension", "")).strip().upper() == "MULTIPLE"),
            "UNKNOWN": sum(1 for row in out_rows if str(row.get("failed_dimension", "")).strip().upper() == "UNKNOWN"),
        },
        "csv_path": str(csv_path),
        "summary_json": str(summary_json),
        "summary_md": str(summary_md),
    }
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Near-Miss Strict Gap",
        "",
        f"- final_verdict: {summary['final_verdict']}",
        f"- row_count: {summary['row_count']}",
        f"- safe_to_experiment_count: {summary['safe_to_experiment_count']}",
    ]
    summary_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Diagnose how near-miss samples differ from strict thresholds")
    parser.add_argument("--observation-samples-csv", default="reports/observation_sample_store/observation_samples.csv")
    parser.add_argument("--shadow-universe-candidates-csv", default="reports/shadow_universe_collection/shadow_universe_candidates.csv")
    parser.add_argument("--near-miss-scores-csv", default="reports/shadow_near_miss/near_miss_scores.csv")
    parser.add_argument("--output-dir", default="reports/near_miss_strict_gap")
    parser.add_argument("--min-trend-score", type=float, default=60.0)
    parser.add_argument("--min-breakout-score", type=float, default=60.0)
    parser.add_argument("--min-risk-reward-score", type=float, default=60.0)
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    mode = normalize_execution_mode(os.environ.get("QQ_RUNTIME_MODE"))
    assert_dry_run_required(mode)
    args = build_arg_parser().parse_args()
    result = diagnose_near_miss_strict_gap(
        observation_samples_csv=str(args.observation_samples_csv or "reports/observation_sample_store/observation_samples.csv"),
        shadow_universe_candidates_csv=str(
            args.shadow_universe_candidates_csv or "reports/shadow_universe_collection/shadow_universe_candidates.csv"
        ),
        near_miss_scores_csv=str(args.near_miss_scores_csv or "reports/shadow_near_miss/near_miss_scores.csv"),
        output_dir=str(args.output_dir or "reports/near_miss_strict_gap"),
        min_trend_score=float(args.min_trend_score if args.min_trend_score is not None else 60.0),
        min_breakout_score=float(args.min_breakout_score if args.min_breakout_score is not None else 60.0),
        min_risk_reward_score=float(args.min_risk_reward_score if args.min_risk_reward_score is not None else 60.0),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"final_verdict={result.get('final_verdict', '')}")
    print(f"row_count={result.get('row_count', 0)}")


if __name__ == "__main__":
    main()
