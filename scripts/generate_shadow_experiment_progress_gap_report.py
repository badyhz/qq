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
    "target_samples_this_run",
    "actual_new_candidates",
    "sample_gap",
    "gap_ratio",
    "gap_reason",
    "suggested_next_target",
    "suggested_collector_mode",
    "suggested_near_miss_threshold",
    "priority_adjustment",
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


def _to_float(value: Any, default: float = 0.0) -> float:
    parsed = to_float_nan(value)
    if not math.isfinite(parsed):
        return float(default)
    return float(parsed)


def _reason_from_run_summary(run_summary: dict[str, Any], applied_summary: dict[str, Any]) -> str:
    missing_cache_count = _to_int(run_summary.get("missing_cache_count"), 0)
    if missing_cache_count > 0:
        return "MISSING_CACHE"
    filter_fail = run_summary.get("filter_fail_summary")
    if isinstance(filter_fail, dict):
        strict_hits = (
            _to_int(filter_fail.get("trend_not_aligned"), 0)
            + _to_int(filter_fail.get("breakout_not_confirmed"), 0)
            + _to_int(filter_fail.get("risk_reward_too_low"), 0)
        )
        if strict_hits > 0:
            return "FILTER_TOO_STRICT"
    duplicate_skipped = _to_int(applied_summary.get("duplicate_candidate_skipped_count"), 0)
    if duplicate_skipped > 0:
        return "DUPLICATE_OR_COOLDOWN"
    status_reason = str(run_summary.get("status_reason", "")).strip().lower()
    if status_reason in {"no_next_run_candidates", "no_signal"}:
        return "NO_SIGNAL"
    return "INSUFFICIENT_MARKET_MOVEMENT"


def generate_shadow_experiment_progress_gap_report(
    *,
    next_run_plan_csv: str = "reports/next_shadow_experiment_run_plan/next_shadow_experiment_run_plan.csv",
    next_run_candidates_csv: str = "reports/next_shadow_experiment_run/next_run_candidates.csv",
    next_run_summary_json: str = "reports/next_shadow_experiment_run/summary.json",
    next_run_applied_summary_json: str = "reports/next_shadow_experiment_run_applied/summary.json",
    experiment_sample_tracker_csv: str = "reports/shadow_experiment_sample_tracker/experiment_sample_tracker.csv",
    output_dir: str = "reports/shadow_experiment_progress_gap",
) -> dict[str, Any]:
    plan_rows = read_csv_rows(Path(next_run_plan_csv))
    candidate_rows = read_csv_rows(Path(next_run_candidates_csv))
    run_summary = _read_json(Path(next_run_summary_json))
    applied_summary = _read_json(Path(next_run_applied_summary_json))
    tracker_rows = read_csv_rows(Path(experiment_sample_tracker_csv))

    candidates_by_exp: dict[str, set[str]] = {}
    for row in candidate_rows:
        exp_id = str(row.get("experiment_id", "")).strip()
        cid = str(row.get("next_run_candidate_id", "")).strip()
        if not exp_id or not cid:
            continue
        candidates_by_exp.setdefault(exp_id, set()).add(cid)
    tracker_by_exp = {
        str(row.get("experiment_id", "")).strip(): row
        for row in tracker_rows
        if str(row.get("experiment_id", "")).strip()
    }

    out_rows: list[dict[str, Any]] = []
    for plan in plan_rows:
        exp_id = str(plan.get("experiment_id", "")).strip()
        if not exp_id:
            continue
        target = max(0, _to_int(plan.get("target_samples_this_run"), 0))
        actual = len(candidates_by_exp.get(exp_id, set()))
        sample_gap = max(0, target - actual)
        gap_ratio = (float(sample_gap) / float(target)) if target > 0 else 0.0
        gap_reason = "UNKNOWN"
        if sample_gap > 0:
            gap_reason = _reason_from_run_summary(run_summary, applied_summary)

        suggested_next_target = target
        if sample_gap > 0 and gap_ratio >= 0.8:
            suggested_next_target = max(target, target + max(1, int(round(target * 0.25))))
        elif sample_gap > 0 and gap_ratio >= 0.4:
            suggested_next_target = max(target, target + max(1, int(round(target * 0.1))))

        collector_mode = str(plan.get("collector_mode", "observation")).strip().lower() or "observation"
        suggested_near_miss_threshold = 0.75 if collector_mode == "observation" else 1.0
        priority_adjustment = "KEEP"
        if sample_gap > 0 and gap_reason in {"FILTER_TOO_STRICT", "NO_SIGNAL"} and gap_ratio >= 0.8:
            priority_adjustment = "REDUCE"

        reason_parts: list[str] = []
        if sample_gap > 0:
            reason_parts.append("target_not_met")
            reason_parts.append(gap_reason.lower())
        else:
            reason_parts.append("target_met")
        if priority_adjustment == "REDUCE":
            reason_parts.append("conservative_priority_reduce")

        out_rows.append(
            {
                "experiment_id": exp_id,
                "strategy_key": str(plan.get("strategy_key", "")).strip(),
                "symbol": str(plan.get("symbol", "")).strip().upper(),
                "side": str(plan.get("side", "")).strip().upper(),
                "timeframe": str(plan.get("timeframe", "5m")).strip() or "5m",
                "experiment_type": str(plan.get("experiment_type", "UNKNOWN")).strip().upper() or "UNKNOWN",
                "target_samples_this_run": target,
                "actual_new_candidates": actual,
                "sample_gap": sample_gap,
                "gap_ratio": round(gap_ratio, 8),
                "gap_reason": gap_reason,
                "suggested_next_target": suggested_next_target,
                "suggested_collector_mode": collector_mode,
                "suggested_near_miss_threshold": suggested_near_miss_threshold,
                "priority_adjustment": priority_adjustment,
                "reason": ";".join(sorted(set(reason_parts))),
            }
        )

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "progress_gap_report.csv"
    summary_json = out_dir / "summary.json"
    summary_md = out_dir / "summary.md"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for row in out_rows:
            writer.writerow({field: row.get(field, "") for field in FIELDS})

    rows_with_gap = [row for row in out_rows if _to_int(row.get("sample_gap"), 0) > 0]
    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "final_verdict": "PASS" if out_rows else "PARTIAL",
        "experiment_count": len(out_rows),
        "target_total": sum(max(0, _to_int(row.get("target_samples_this_run"), 0)) for row in out_rows),
        "actual_total": sum(max(0, _to_int(row.get("actual_new_candidates"), 0)) for row in out_rows),
        "sample_gap_total": sum(max(0, _to_int(row.get("sample_gap"), 0)) for row in out_rows),
        "gap_experiment_count": len(rows_with_gap),
        "gap_reason_breakdown": {
            reason: sum(1 for row in rows_with_gap if str(row.get("gap_reason", "")).strip().upper() == reason)
            for reason in {
                "NO_SIGNAL",
                "FILTER_TOO_STRICT",
                "MISSING_CACHE",
                "DUPLICATE_OR_COOLDOWN",
                "MAX_CANDIDATES_LIMIT",
                "INSUFFICIENT_MARKET_MOVEMENT",
                "UNKNOWN",
            }
        },
        "recommended_next_action": "CONTINUE_SHADOW_EXPERIMENT_COLLECTION",
        "submit_allowed": False,
        "real_submit_allowed": False,
        "submit_attempted": False,
        "cancel_attempted": False,
        "flatten_attempted": False,
        "csv_path": str(csv_path),
        "summary_json": str(summary_json),
        "summary_md": str(summary_md),
    }
    if out_rows and summary["sample_gap_total"] > 0:
        summary["final_verdict"] = "PARTIAL"
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Shadow Experiment Progress Gap Report",
        "",
        f"- final_verdict: {summary['final_verdict']}",
        f"- experiment_count: {summary['experiment_count']}",
        f"- target_total: {summary['target_total']}",
        f"- actual_total: {summary['actual_total']}",
        f"- sample_gap_total: {summary['sample_gap_total']}",
        f"- recommended_next_action: {summary['recommended_next_action']}",
        "- submit_allowed: false",
        "- real_submit_allowed: false",
    ]
    summary_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate gap report between planned and collected shadow experiment samples")
    parser.add_argument("--next-run-plan-csv", default="reports/next_shadow_experiment_run_plan/next_shadow_experiment_run_plan.csv")
    parser.add_argument("--next-run-candidates-csv", default="reports/next_shadow_experiment_run/next_run_candidates.csv")
    parser.add_argument("--next-run-summary-json", default="reports/next_shadow_experiment_run/summary.json")
    parser.add_argument("--next-run-applied-summary-json", default="reports/next_shadow_experiment_run_applied/summary.json")
    parser.add_argument("--experiment-sample-tracker-csv", default="reports/shadow_experiment_sample_tracker/experiment_sample_tracker.csv")
    parser.add_argument("--output-dir", default="reports/shadow_experiment_progress_gap")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = generate_shadow_experiment_progress_gap_report(
        next_run_plan_csv=str(args.next_run_plan_csv or "reports/next_shadow_experiment_run_plan/next_shadow_experiment_run_plan.csv"),
        next_run_candidates_csv=str(args.next_run_candidates_csv or "reports/next_shadow_experiment_run/next_run_candidates.csv"),
        next_run_summary_json=str(args.next_run_summary_json or "reports/next_shadow_experiment_run/summary.json"),
        next_run_applied_summary_json=str(
            args.next_run_applied_summary_json or "reports/next_shadow_experiment_run_applied/summary.json"
        ),
        experiment_sample_tracker_csv=str(
            args.experiment_sample_tracker_csv or "reports/shadow_experiment_sample_tracker/experiment_sample_tracker.csv"
        ),
        output_dir=str(args.output_dir or "reports/shadow_experiment_progress_gap"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"final_verdict={result.get('final_verdict', '')}")
    print(f"sample_gap_total={result.get('sample_gap_total', 0)}")


if __name__ == "__main__":
    main()
