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
    "recent_candidate_trend",
    "recent_quality_trend",
    "recent_stability_trend",
    "progress_gap_trend",
    "trend_verdict",
    "recommended_action",
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


def _trend_by_pair(previous: float, current: float, tolerance: float = 1e-8) -> str:
    if (not math.isfinite(previous)) or (not math.isfinite(current)):
        return "INSUFFICIENT_HISTORY"
    if current > previous + tolerance:
        return "IMPROVING"
    if current < previous - tolerance:
        return "DETERIORATING"
    return "FLAT"


def analyze_shadow_experiment_trends(
    *,
    experiment_history_csv: str = "reports/shadow_experiment_history/experiment_history.csv",
    applied_history_delta_csv: str = "reports/next_shadow_experiment_run_applied/applied_history_delta.csv",
    stability_scores_csv: str = "reports/shadow_experiment_stability/stability_scores.csv",
    progress_gap_report_csv: str = "reports/shadow_experiment_progress_gap/progress_gap_report.csv",
    output_dir: str = "reports/shadow_experiment_trends",
) -> dict[str, Any]:
    history_rows = read_csv_rows(Path(experiment_history_csv))
    delta_rows = read_csv_rows(Path(applied_history_delta_csv))
    stability_rows = read_csv_rows(Path(stability_scores_csv))
    gap_rows = read_csv_rows(Path(progress_gap_report_csv))

    history_by_exp: dict[str, list[dict[str, Any]]] = {}
    for row in sorted(
        history_rows,
        key=lambda item: (str(item.get("experiment_id", "")), str(item.get("run_date", "")), str(item.get("created_at", ""))),
    ):
        exp_id = str(row.get("experiment_id", "")).strip()
        if exp_id:
            history_by_exp.setdefault(exp_id, []).append(row)
    delta_by_exp = {
        str(row.get("experiment_id", "")).strip(): row
        for row in delta_rows
        if str(row.get("experiment_id", "")).strip()
    }
    stability_by_exp = {
        str(row.get("experiment_id", "")).strip(): row
        for row in stability_rows
        if str(row.get("experiment_id", "")).strip()
    }
    gap_by_exp = {
        str(row.get("experiment_id", "")).strip(): row
        for row in gap_rows
        if str(row.get("experiment_id", "")).strip()
    }

    experiment_ids = sorted(set(history_by_exp.keys()) | set(delta_by_exp.keys()) | set(stability_by_exp.keys()) | set(gap_by_exp.keys()))
    out_rows: list[dict[str, Any]] = []
    for exp_id in experiment_ids:
        hist = history_by_exp.get(exp_id, [])
        delta = delta_by_exp.get(exp_id, {})
        stability = stability_by_exp.get(exp_id, {})
        gap = gap_by_exp.get(exp_id, {})
        latest = hist[-1] if hist else {}

        sample_series = [_to_int(row.get("sample_count"), 0) for row in hist]
        if delta:
            # delta represents current run progress; append implied next sample point.
            latest_count = sample_series[-1] if sample_series else 0
            sample_series.append(latest_count + _to_int(delta.get("actual_new_candidates"), 0))
        history_run_count = len(sample_series)

        quality_series = [_to_float(row.get("avg_realized_r")) for row in hist]
        cand_trend = "INSUFFICIENT_HISTORY"
        quality_trend = "INSUFFICIENT_HISTORY"
        if len(sample_series) >= 3:
            cand_trend = _trend_by_pair(float(sample_series[-2]), float(sample_series[-1]), tolerance=0.0)
            prev_q = quality_series[-2] if len(quality_series) >= 2 else float("nan")
            curr_q = quality_series[-1] if len(quality_series) >= 1 else float("nan")
            quality_trend = _trend_by_pair(prev_q, curr_q, tolerance=1e-6)

        stability_verdict = str(stability.get("stability_verdict", "NEEDS_MORE_DATA")).strip().upper() or "NEEDS_MORE_DATA"
        if stability_verdict == "STABLE_PROMISING":
            stability_trend = "IMPROVING"
        elif stability_verdict == "UNSTABLE_BAD":
            stability_trend = "DETERIORATING"
        elif stability_verdict in {"NEEDS_MORE_DATA", "UNKNOWN", ""}:
            stability_trend = "INSUFFICIENT_HISTORY"
        else:
            stability_trend = "FLAT"

        gap_ratio = _to_float(gap.get("gap_ratio"))
        if not math.isfinite(gap_ratio):
            progress_gap_trend = "INSUFFICIENT_HISTORY"
        elif gap_ratio >= 0.8:
            progress_gap_trend = "DETERIORATING"
        elif gap_ratio <= 0.2:
            progress_gap_trend = "IMPROVING"
        else:
            progress_gap_trend = "FLAT"

        reasons: list[str] = []
        trend_verdict = "WATCH_MORE"
        recommended_action = "KEEP_COLLECTING_SHADOW_EXPERIMENT_SAMPLES"
        if history_run_count < 3:
            reasons.append("insufficient_history_runs")
        if stability_verdict == "NEEDS_MORE_DATA":
            reasons.append("insufficient_stability_data")

        if history_run_count >= 3 and stability_verdict not in {"NEEDS_MORE_DATA", "UNKNOWN"}:
            deterioration_hits = sum(
                1
                for item in (cand_trend, quality_trend, stability_trend, progress_gap_trend)
                if item == "DETERIORATING"
            )
            improving_hits = sum(
                1
                for item in (cand_trend, quality_trend, stability_trend, progress_gap_trend)
                if item == "IMPROVING"
            )
            if deterioration_hits >= 2:
                trend_verdict = "REDUCE_PRIORITY"
                recommended_action = "REDUCE_SHADOW_EXPERIMENT_PRIORITY"
                reasons.append("multi_dimension_deterioration")
            elif improving_hits >= 2:
                trend_verdict = "CONTINUE"
                recommended_action = "CONTINUE_SHADOW_EXPERIMENT_COLLECTION"
                reasons.append("trend_improving")
            else:
                trend_verdict = "WATCH_MORE"
                recommended_action = "KEEP_COLLECTING_SHADOW_EXPERIMENT_SAMPLES"
                reasons.append("trend_not_significant")
        else:
            trend_verdict = "WATCH_MORE"
            recommended_action = "KEEP_COLLECTING_SHADOW_EXPERIMENT_SAMPLES"

        base = latest if latest else (gap if gap else stability)
        out_rows.append(
            {
                "experiment_id": exp_id,
                "strategy_key": str(base.get("strategy_key", "")).strip(),
                "symbol": str(base.get("symbol", "")).strip().upper(),
                "side": str(base.get("side", "")).strip().upper(),
                "timeframe": str(base.get("timeframe", "5m")).strip() or "5m",
                "experiment_type": str(base.get("experiment_type", "UNKNOWN")).strip().upper() or "UNKNOWN",
                "history_run_count": history_run_count,
                "recent_candidate_trend": cand_trend,
                "recent_quality_trend": quality_trend,
                "recent_stability_trend": stability_trend,
                "progress_gap_trend": progress_gap_trend,
                "trend_verdict": trend_verdict,
                "recommended_action": recommended_action,
                "reason": ";".join(sorted(set(reasons))) if reasons else "ok",
            }
        )

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "experiment_trends.csv"
    summary_json = out_dir / "summary.json"
    summary_md = out_dir / "summary.md"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for row in out_rows:
            writer.writerow({field: row.get(field, "") for field in FIELDS})

    watch_more_count = sum(1 for row in out_rows if str(row.get("trend_verdict", "")).strip().upper() == "WATCH_MORE")
    continue_count = sum(1 for row in out_rows if str(row.get("trend_verdict", "")).strip().upper() == "CONTINUE")
    reduce_count = sum(1 for row in out_rows if str(row.get("trend_verdict", "")).strip().upper() in {"REDUCE_PRIORITY", "PAUSE"})
    insufficient_history_count = sum(
        1 for row in out_rows if "insufficient_history_runs" in str(row.get("reason", ""))
    )
    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "final_verdict": "PASS" if out_rows else "PARTIAL",
        "experiment_count": len(out_rows),
        "watch_more_count": watch_more_count,
        "continue_count": continue_count,
        "reduce_priority_count": reduce_count,
        "insufficient_history_count": insufficient_history_count,
        "max_history_run_count": max([_to_int(row.get("history_run_count"), 0) for row in out_rows] or [0]),
        "recommended_next_action": "CONTINUE_SHADOW_EXPERIMENT_COLLECTION",
        "csv_path": str(csv_path),
        "summary_json": str(summary_json),
        "summary_md": str(summary_md),
    }
    if out_rows and watch_more_count > 0:
        summary["final_verdict"] = "PARTIAL"
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Shadow Experiment Trends",
        "",
        f"- final_verdict: {summary['final_verdict']}",
        f"- experiment_count: {summary['experiment_count']}",
        f"- watch_more_count: {summary['watch_more_count']}",
        f"- continue_count: {summary['continue_count']}",
        f"- reduce_priority_count: {summary['reduce_priority_count']}",
        f"- recommended_next_action: {summary['recommended_next_action']}",
    ]
    summary_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Analyze multi-run shadow experiment trends")
    parser.add_argument("--experiment-history-csv", default="reports/shadow_experiment_history/experiment_history.csv")
    parser.add_argument("--applied-history-delta-csv", default="reports/next_shadow_experiment_run_applied/applied_history_delta.csv")
    parser.add_argument("--stability-scores-csv", default="reports/shadow_experiment_stability/stability_scores.csv")
    parser.add_argument("--progress-gap-report-csv", default="reports/shadow_experiment_progress_gap/progress_gap_report.csv")
    parser.add_argument("--output-dir", default="reports/shadow_experiment_trends")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = analyze_shadow_experiment_trends(
        experiment_history_csv=str(args.experiment_history_csv or "reports/shadow_experiment_history/experiment_history.csv"),
        applied_history_delta_csv=str(
            args.applied_history_delta_csv or "reports/next_shadow_experiment_run_applied/applied_history_delta.csv"
        ),
        stability_scores_csv=str(args.stability_scores_csv or "reports/shadow_experiment_stability/stability_scores.csv"),
        progress_gap_report_csv=str(
            args.progress_gap_report_csv or "reports/shadow_experiment_progress_gap/progress_gap_report.csv"
        ),
        output_dir=str(args.output_dir or "reports/shadow_experiment_trends"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"final_verdict={result.get('final_verdict', '')}")
    print(f"watch_more_count={result.get('watch_more_count', 0)}")


if __name__ == "__main__":
    main()
