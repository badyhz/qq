from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_csv_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            return [row for row in reader if row]
    except (OSError, csv.Error):
        return []


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _calculate_slope(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    n = len(values)
    x_sum = sum(range(n))
    y_sum = sum(values)
    xy_sum = sum(i * val for i, val in enumerate(values))
    x_sq_sum = sum(i * i for i in range(n))
    denominator = n * x_sq_sum - x_sum * x_sum
    if abs(denominator) < 1e-9:
        return 0.0
    slope = (n * xy_sum - x_sum * y_sum) / denominator
    return slope


def _calculate_moving_average(values: list[float], window: int = 3) -> list[float]:
    if window <= 0:
        return values[:]
    result: list[float] = []
    for i in range(len(values)):
        start = max(0, i - window + 1)
        slice_vals = values[start : i + 1]
        result.append(sum(slice_vals) / len(slice_vals))
    return result


def analyze_remediation_gap_convergence(
    *,
    history_csv: str = "reports/remediation_loop_history/remediation_loop_history.csv",
    remediation_summary_json: str = "reports/testnet_dry_run_remediation/summary.json",
    progress_gap_summary_json: str = "reports/shadow_experiment_progress_gap/summary.json",
    output_dir: str = "reports/remediation_gap_convergence",
) -> dict[str, Any]:
    history_rows = _read_csv_rows(Path(history_csv))
    remediation_summary = _read_json(Path(remediation_summary_json))
    progress_gap = _read_json(Path(progress_gap_summary_json))

    sample_gaps = [_to_float(row.get("sample_gap_after", 0)) for row in history_rows]
    gap_deltas = [_to_float(row.get("gap_delta", 0)) for row in history_rows]
    candidates = [_to_float(row.get("new_candidates_collected", 0)) for row in history_rows]

    current_gap = int(progress_gap.get("sample_gap_total", 0) or 0)
    if sample_gaps:
        current_gap = int(sample_gaps[-1])

    gap_trend_slope = _calculate_slope(sample_gaps) if sample_gaps else 0.0
    gap_ma3 = _calculate_moving_average(sample_gaps, 3) if sample_gaps else []

    convergence_detected = False
    convergence_reason = ""
    if len(sample_gaps) >= 3:
        if gap_trend_slope < -0.5 and all(d <= 0 for d in gap_deltas[-3:]):
            convergence_detected = True
            convergence_reason = "negative_slope_and_declining_gaps"
        elif len(gap_ma3) >= 3 and gap_ma3[-1] < max(sample_gaps) * 0.8:
            convergence_detected = True
            convergence_reason = "moving_average_declining"

    stagnation_detected = False
    stagnation_reason = ""
    if len(sample_gaps) >= 3 and len(gap_deltas) >= 3:
        recent_deltas = gap_deltas[-3:]
        if all(abs(d) < 1.0 for d in recent_deltas):
            stagnation_detected = True
            stagnation_reason = "gap_delta_near_zero"

    divergence_detected = False
    divergence_reason = ""
    if len(gap_deltas) >= 3:
        if all(d > 0 for d in gap_deltas[-3:]):
            divergence_detected = True
            divergence_reason = "gap_increasing"
        elif gap_trend_slope > 0.5 and sum(gap_deltas[-3:]) > 5:
            divergence_detected = True
            divergence_reason = "positive_slope"

    total_candidates = sum(int(c or 0) for c in candidates)
    avg_candidates_per_run = total_candidates / len(candidates) if candidates else 0.0

    final_verdict = "IN_PROGRESS"
    if convergence_detected and current_gap < 10:
        final_verdict = "CONVERGING"
    elif stagnation_detected:
        final_verdict = "STAGNANT"
    elif divergence_detected:
        final_verdict = "DIVERGING"
    elif current_gap == 0:
        final_verdict = "CONVERGED"

    blocking_reasons_remaining = remediation_summary.get("blocking_reasons_remaining", [])
    blocking_gaps_count = len(blocking_reasons_remaining)

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_json = out_dir / "summary.json"
    trends_json = out_dir / "trend_data.json"
    summary_md = out_dir / "summary.md"

    trend_data = {
        "sample_gaps": sample_gaps,
        "gap_deltas": gap_deltas,
        "candidates_collected": candidates,
        "gap_trend_slope": gap_trend_slope,
        "gap_moving_average_3": gap_ma3,
    }

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "final_verdict": final_verdict,
        "current_sample_gap": current_gap,
        "total_runs_analyzed": len(history_rows),
        "total_candidates_collected": total_candidates,
        "avg_candidates_per_run": round(avg_candidates_per_run, 4),
        "gap_trend_slope": round(gap_trend_slope, 6),
        "convergence_detected": convergence_detected,
        "convergence_reason": convergence_reason,
        "stagnation_detected": stagnation_detected,
        "stagnation_reason": stagnation_reason,
        "divergence_detected": divergence_detected,
        "divergence_reason": divergence_reason,
        "blocking_gaps_count": blocking_gaps_count,
        "recommended_next_action": "CONTINUE_REMEDIATION_SHADOW_ONLY_LOOP"
        if not convergence_detected or current_gap >= 10
        else "EVALUATE_DRY_RUN_READINESS",
        "allowed_mode": "SHADOW_ONLY",
        "submit_allowed": False,
        "testnet_submit_allowed": False,
        "real_submit_allowed": False,
        "submit_attempted": False,
        "cancel_attempted": False,
        "flatten_attempted": False,
    }

    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    trends_json.write_text(json.dumps(trend_data, ensure_ascii=False, indent=2), encoding="utf-8")

    summary_lines = [
        "# Remediation Gap Convergence Analysis",
        "",
        f"- final_verdict: {summary['final_verdict']}",
        f"- current_sample_gap: {summary['current_sample_gap']}",
        f"- total_runs_analyzed: {summary['total_runs_analyzed']}",
        f"- total_candidates_collected: {summary['total_candidates_collected']}",
        f"- avg_candidates_per_run: {summary['avg_candidates_per_run']}",
        f"- gap_trend_slope: {summary['gap_trend_slope']}",
        f"- convergence_detected: {summary['convergence_detected']}",
        f"- stagnation_detected: {summary['stagnation_detected']}",
        f"- divergence_detected: {summary['divergence_detected']}",
        f"- recommended_next_action: {summary['recommended_next_action']}",
        "- allowed_mode: SHADOW_ONLY",
        "- testnet_submit_allowed: false",
        "- real_submit_allowed: false",
        "- submit_attempted: false",
        "- cancel_attempted: false",
        "- flatten_attempted: false",
    ]
    summary_md.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    return summary


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Analyze remediation gap convergence trends")
    parser.add_argument("--history-csv", default="reports/remediation_loop_history/remediation_loop_history.csv")
    parser.add_argument("--remediation-summary-json", default="reports/testnet_dry_run_remediation/summary.json")
    parser.add_argument("--progress-gap-summary-json", default="reports/shadow_experiment_progress_gap/summary.json")
    parser.add_argument("--output-dir", default="reports/remediation_gap_convergence")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = analyze_remediation_gap_convergence(
        history_csv=str(args.history_csv or "reports/remediation_loop_history/remediation_loop_history.csv"),
        remediation_summary_json=str(args.remediation_summary_json or "reports/testnet_dry_run_remediation/summary.json"),
        progress_gap_summary_json=str(args.progress_gap_summary_json or "reports/shadow_experiment_progress_gap/summary.json"),
        output_dir=str(args.output_dir or "reports/remediation_gap_convergence"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"final_verdict={result.get('final_verdict', '')}")
    print(f"current_sample_gap={result.get('current_sample_gap', 0)}")
    print(f"convergence_detected={result.get('convergence_detected', False)}")


if __name__ == "__main__":
    main()
