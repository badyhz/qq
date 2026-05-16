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
    "rank",
    "experiment_id",
    "strategy_key",
    "symbol",
    "side",
    "timeframe",
    "experiment_type",
    "sample_count",
    "sample_gap_to_20",
    "stability_score",
    "stability_verdict",
    "near_miss_count",
    "experiment_priority_score",
    "priority_bucket",
    "recommended_action",
    "reason",
]


def _to_int(value: Any, default: int = 0) -> int:
    parsed = to_float_nan(value)
    if not math.isfinite(parsed):
        return int(default)
    return int(parsed)


def _priority_bonus(scan_priority: str) -> float:
    text = str(scan_priority or "").strip().upper()
    if text == "P0":
        return 100.0
    if text == "P1":
        return 80.0
    if text == "P2":
        return 60.0
    if text == "P3":
        return 40.0
    return 50.0


def rank_shadow_experiment_priorities(
    *,
    history_dashboard_by_experiment_csv: str = "reports/shadow_experiment_history_dashboard/by_experiment.csv",
    stability_scores_csv: str = "reports/shadow_experiment_stability/stability_scores.csv",
    observation_samples_csv: str = "reports/observation_sample_store/observation_samples.csv",
    adjusted_shadow_scan_universe_csv: str = "reports/shadow_universe_adjustment/adjusted_shadow_scan_universe.csv",
    output_dir: str = "reports/shadow_experiment_priorities",
) -> dict[str, Any]:
    by_rows = read_csv_rows(Path(history_dashboard_by_experiment_csv))
    stability_rows = read_csv_rows(Path(stability_scores_csv))
    observation_rows = read_csv_rows(Path(observation_samples_csv))
    universe_rows = read_csv_rows(Path(adjusted_shadow_scan_universe_csv))

    stability_by_exp = {
        str(row.get("experiment_id", "")).strip(): row
        for row in stability_rows
        if str(row.get("experiment_id", "")).strip()
    }
    universe_by_key = {
        str(row.get("strategy_key", "")).strip(): row
        for row in universe_rows
        if str(row.get("strategy_key", "")).strip()
    }

    near_miss_by_strategy: dict[str, int] = {}
    for row in observation_rows:
        key = str(row.get("strategy_key", "")).strip()
        if not key:
            continue
        is_near = str(row.get("near_miss", "")).strip().lower() in {"1", "true", "yes", "y"}
        if is_near:
            near_miss_by_strategy[key] = int(near_miss_by_strategy.get(key, 0)) + 1

    scored: list[dict[str, Any]] = []
    for row in by_rows:
        exp_id = str(row.get("experiment_id", "")).strip()
        strategy_key = str(row.get("strategy_key", "")).strip()
        sample_count = _to_int(row.get("sample_count"), 0)
        sample_gap_to_20 = max(0, 20 - sample_count)
        near_miss_count = int(near_miss_by_strategy.get(strategy_key, 0))
        stability = stability_by_exp.get(exp_id, {})
        stability_score = to_float_nan(stability.get("stability_score", row.get("stability_score")))
        if not math.isfinite(stability_score):
            stability_score = 0.0
        stability_verdict = str(stability.get("stability_verdict", row.get("stability_verdict", "NEEDS_MORE_DATA"))).strip().upper() or "NEEDS_MORE_DATA"
        universe = universe_by_key.get(strategy_key, {})
        universe_priority = _priority_bonus(universe.get("scan_priority", "P2"))

        sample_urgency = min(100.0, (sample_gap_to_20 / 20.0) * 100.0)
        clue_score = min(100.0, near_miss_count * 40.0)
        stability_non_negative = 100.0 if stability_verdict in {"NEEDS_MORE_DATA", "UNSTABLE_PROMISING", "STABLE_PROMISING"} else 20.0
        risk_penalty = 0.0
        if stability_verdict == "UNSTABLE_BAD":
            risk_penalty = 100.0
        elif stability_verdict == "NEEDS_MORE_DATA":
            risk_penalty = 40.0
        priority_score = (
            sample_urgency * 0.30
            + clue_score * 0.25
            + stability_non_negative * 0.20
            + universe_priority * 0.15
            + (100.0 - risk_penalty) * 0.10
        )

        priority_bucket = "P2"
        if stability_verdict == "UNSTABLE_BAD":
            priority_bucket = "PAUSED"
        elif priority_score >= 75:
            priority_bucket = "P0"
        elif priority_score >= 60:
            priority_bucket = "P1"
        elif priority_score >= 45:
            priority_bucket = "P2"
        else:
            priority_bucket = "P3"

        # Conservative cap while sample size remains small.
        if sample_count < 20 and priority_bucket in {"P0", "P1"}:
            priority_bucket = "P1" if near_miss_count > 0 else "P2"

        recommended_action = "KEEP_COLLECTING_SHADOW_SAMPLES"
        reasons: list[str] = []
        if priority_bucket == "PAUSED":
            recommended_action = "PAUSE_AND_REVIEW_SHADOW_EXPERIMENT"
            reasons.append("unstable_bad_requires_pause")
        else:
            reasons.append("collect_more_experiment_samples")
            if sample_gap_to_20 > 0:
                reasons.append("minimum_decision_samples_not_met")
            if near_miss_count > 0:
                reasons.append("near_miss_signal_present")

        scored.append(
            {
                "experiment_id": exp_id,
                "strategy_key": strategy_key,
                "symbol": str(row.get("symbol", "")).strip().upper(),
                "side": str(row.get("side", "")).strip().upper(),
                "timeframe": str(row.get("timeframe", "5m")).strip() or "5m",
                "experiment_type": str(row.get("experiment_type", "UNKNOWN")).strip().upper() or "UNKNOWN",
                "sample_count": sample_count,
                "sample_gap_to_20": sample_gap_to_20,
                "stability_score": round(stability_score, 8),
                "stability_verdict": stability_verdict,
                "near_miss_count": near_miss_count,
                "experiment_priority_score": round(priority_score, 8),
                "priority_bucket": priority_bucket,
                "recommended_action": recommended_action,
                "reason": ";".join(sorted(set(reasons))),
            }
        )

    scored.sort(
        key=lambda row: (
            -float(row.get("experiment_priority_score", 0.0) or 0.0),
            str(row.get("experiment_id", "")),
        )
    )
    out_rows: list[dict[str, Any]] = []
    for idx, row in enumerate(scored, start=1):
        payload = dict(row)
        payload["rank"] = idx
        out_rows.append(payload)

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "experiment_priority_rank.csv"
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
        "p0_count": sum(1 for row in out_rows if str(row.get("priority_bucket", "")).strip().upper() == "P0"),
        "p1_count": sum(1 for row in out_rows if str(row.get("priority_bucket", "")).strip().upper() == "P1"),
        "p2_count": sum(1 for row in out_rows if str(row.get("priority_bucket", "")).strip().upper() == "P2"),
        "p3_count": sum(1 for row in out_rows if str(row.get("priority_bucket", "")).strip().upper() == "P3"),
        "paused_count": sum(1 for row in out_rows if str(row.get("priority_bucket", "")).strip().upper() == "PAUSED"),
        "promote_like_actions_count": 0,
        "recommended_action_default": "KEEP_COLLECTING_SHADOW_SAMPLES",
        "csv_path": str(csv_path),
        "summary_json": str(summary_json),
        "summary_md": str(summary_md),
    }
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Shadow Experiment Priority Rank",
        "",
        f"- final_verdict: {summary['final_verdict']}",
        f"- experiment_count: {summary['experiment_count']}",
        f"- p0_count: {summary['p0_count']}",
        f"- p1_count: {summary['p1_count']}",
        f"- p2_count: {summary['p2_count']}",
        f"- p3_count: {summary['p3_count']}",
        f"- paused_count: {summary['paused_count']}",
    ]
    summary_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Rank shadow experiments by collection priority")
    parser.add_argument("--history-dashboard-by-experiment-csv", default="reports/shadow_experiment_history_dashboard/by_experiment.csv")
    parser.add_argument("--stability-scores-csv", default="reports/shadow_experiment_stability/stability_scores.csv")
    parser.add_argument("--observation-samples-csv", default="reports/observation_sample_store/observation_samples.csv")
    parser.add_argument(
        "--adjusted-shadow-scan-universe-csv",
        default="reports/shadow_universe_adjustment/adjusted_shadow_scan_universe.csv",
    )
    parser.add_argument("--output-dir", default="reports/shadow_experiment_priorities")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = rank_shadow_experiment_priorities(
        history_dashboard_by_experiment_csv=str(
            args.history_dashboard_by_experiment_csv or "reports/shadow_experiment_history_dashboard/by_experiment.csv"
        ),
        stability_scores_csv=str(args.stability_scores_csv or "reports/shadow_experiment_stability/stability_scores.csv"),
        observation_samples_csv=str(args.observation_samples_csv or "reports/observation_sample_store/observation_samples.csv"),
        adjusted_shadow_scan_universe_csv=str(
            args.adjusted_shadow_scan_universe_csv or "reports/shadow_universe_adjustment/adjusted_shadow_scan_universe.csv"
        ),
        output_dir=str(args.output_dir or "reports/shadow_experiment_priorities"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"final_verdict={result.get('final_verdict', '')}")
    print(f"experiment_count={result.get('experiment_count', 0)}")


if __name__ == "__main__":
    main()
