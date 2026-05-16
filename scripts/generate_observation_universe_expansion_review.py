from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.strategy_edge_common import read_csv_rows, to_float_nan


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
    if parsed != parsed:
        return int(default)
    return int(parsed)


def generate_observation_universe_expansion_review(
    *,
    stability_scores_csv: str = "reports/shadow_experiment_stability/stability_scores.csv",
    experiment_history_csv: str = "reports/shadow_experiment_history/experiment_history.csv",
    shadow_universe_adjustment_summary_json: str = "reports/shadow_universe_adjustment/summary.json",
    observation_experiment_dashboard_json: str = "reports/observation_experiment_dashboard/observation_experiment_dashboard.json",
    shadow_scan_daily_schedule_json: str = "reports/shadow_scan_schedule/shadow_scan_daily_schedule.json",
    output_dir: str = "reports/observation_universe_expansion",
) -> dict[str, Any]:
    stability_rows = read_csv_rows(Path(stability_scores_csv))
    history_rows = read_csv_rows(Path(experiment_history_csv))
    adjustment_summary = _read_json(Path(shadow_universe_adjustment_summary_json))
    experiment_dashboard = _read_json(Path(observation_experiment_dashboard_json))
    schedule = _read_json(Path(shadow_scan_daily_schedule_json))

    total_samples = sum(max(0, _to_int(row.get("total_sample_count"), 0)) for row in stability_rows)
    if total_samples <= 0:
        total_samples = sum(max(0, _to_int(row.get("sample_count"), 0)) for row in history_rows)
    avg_stability_score = float("nan")
    if stability_rows:
        values = [to_float_nan(row.get("stability_score")) for row in stability_rows]
        valid = [value for value in values if value == value]
        if valid:
            avg_stability_score = sum(valid) / len(valid)
    needs_more_data_count = sum(
        1 for row in stability_rows if str(row.get("stability_verdict", "")).strip().upper() == "NEEDS_MORE_DATA"
    )
    unstable_bad_count = sum(
        1 for row in stability_rows if str(row.get("stability_verdict", "")).strip().upper() == "UNSTABLE_BAD"
    )
    stable_promising_count = sum(
        1 for row in stability_rows if str(row.get("stability_verdict", "")).strip().upper() == "STABLE_PROMISING"
    )

    allow_expand_observation_universe = (
        total_samples >= 20 and needs_more_data_count < len(stability_rows) and unstable_bad_count == 0 and len(stability_rows) > 0
    )
    allow_increase_max_candidates = allow_expand_observation_universe and total_samples >= 50 and (avg_stability_score == avg_stability_score and avg_stability_score >= 60.0)
    allow_lower_near_miss_threshold = (
        allow_expand_observation_universe and total_samples >= 30 and stable_promising_count > 0 and unstable_bad_count == 0
    )

    blocking_reasons: list[str] = []
    if not stability_rows:
        blocking_reasons.append("no_stability_scores")
    if total_samples < 20:
        blocking_reasons.append("insufficient_experiment_samples")
    if needs_more_data_count >= max(1, len(stability_rows)):
        blocking_reasons.append("stability_score_not_ready")
    if unstable_bad_count > 0:
        blocking_reasons.append("unstable_bad_experiments_present")
    if str(experiment_dashboard.get("final_verdict", "")).strip().upper() == "PARTIAL":
        blocking_reasons.append("observation_dashboard_partial")
    if str(schedule.get("allowed_mode", "SHADOW_ONLY")).strip().upper() != "SHADOW_ONLY":
        blocking_reasons.append("schedule_mode_not_shadow_only")

    allowed_actions = ["KEEP_CURRENT_UNIVERSE", "CONTINUE_SHADOW_OBSERVATION"]
    if allow_expand_observation_universe:
        allowed_actions.append("EXPAND_OBSERVATION_UNIVERSE_MINIMALLY")
    if allow_increase_max_candidates:
        allowed_actions.append("INCREASE_MAX_CANDIDATES_GRADUALLY")
    if allow_lower_near_miss_threshold:
        allowed_actions.append("LOWER_NEAR_MISS_THRESHOLD_STEPWISE")

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "final_verdict": "PARTIAL" if (not allow_expand_observation_universe or blocking_reasons) else "PASS",
        "allow_expand_observation_universe": bool(allow_expand_observation_universe),
        "allow_increase_max_candidates": bool(allow_increase_max_candidates),
        "allow_lower_near_miss_threshold": bool(allow_lower_near_miss_threshold),
        "allowed_mode": "SHADOW_ONLY",
        "submit_allowed": False,
        "real_submit_allowed": False,
        "blocking_reasons": sorted(set(blocking_reasons)),
        "allowed_expansion_actions": allowed_actions,
        "prohibited_actions": ["NO_TESTNET_SUBMIT", "NO_REAL_SUBMIT", "NO_BYPASS_STRATEGY_GATE"],
        "submit_attempted": False,
        "cancel_attempted": False,
        "flatten_attempted": False,
        "metrics": {
            "stability_rows": len(stability_rows),
            "history_rows": len(history_rows),
            "total_samples": total_samples,
            "needs_more_data_count": needs_more_data_count,
            "unstable_bad_count": unstable_bad_count,
            "stable_promising_count": stable_promising_count,
            "avg_stability_score": avg_stability_score,
            "universe_adjustment_final_verdict": str(adjustment_summary.get("final_verdict", "")).strip().upper(),
            "observation_dashboard_final_verdict": str(experiment_dashboard.get("final_verdict", "")).strip().upper(),
        },
    }

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "observation_universe_expansion_review.json"
    md_path = out_dir / "summary.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Observation Universe Expansion Review",
        "",
        f"- final_verdict: {report['final_verdict']}",
        f"- allow_expand_observation_universe: {str(report['allow_expand_observation_universe']).lower()}",
        f"- allow_increase_max_candidates: {str(report['allow_increase_max_candidates']).lower()}",
        f"- allow_lower_near_miss_threshold: {str(report['allow_lower_near_miss_threshold']).lower()}",
        "- allowed_mode: SHADOW_ONLY",
        "- submit_allowed: false",
        "- real_submit_allowed: false",
    ]
    if report["blocking_reasons"]:
        lines.append(f"- blocking_reasons: {', '.join(report['blocking_reasons'])}")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate review for expanding shadow observation universe")
    parser.add_argument("--stability-scores-csv", default="reports/shadow_experiment_stability/stability_scores.csv")
    parser.add_argument("--experiment-history-csv", default="reports/shadow_experiment_history/experiment_history.csv")
    parser.add_argument(
        "--shadow-universe-adjustment-summary-json",
        default="reports/shadow_universe_adjustment/summary.json",
    )
    parser.add_argument(
        "--observation-experiment-dashboard-json",
        default="reports/observation_experiment_dashboard/observation_experiment_dashboard.json",
    )
    parser.add_argument(
        "--shadow-scan-daily-schedule-json",
        default="reports/shadow_scan_schedule/shadow_scan_daily_schedule.json",
    )
    parser.add_argument("--output-dir", default="reports/observation_universe_expansion")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = generate_observation_universe_expansion_review(
        stability_scores_csv=str(args.stability_scores_csv or "reports/shadow_experiment_stability/stability_scores.csv"),
        experiment_history_csv=str(args.experiment_history_csv or "reports/shadow_experiment_history/experiment_history.csv"),
        shadow_universe_adjustment_summary_json=str(
            args.shadow_universe_adjustment_summary_json or "reports/shadow_universe_adjustment/summary.json"
        ),
        observation_experiment_dashboard_json=str(
            args.observation_experiment_dashboard_json or "reports/observation_experiment_dashboard/observation_experiment_dashboard.json"
        ),
        shadow_scan_daily_schedule_json=str(
            args.shadow_scan_daily_schedule_json or "reports/shadow_scan_schedule/shadow_scan_daily_schedule.json"
        ),
        output_dir=str(args.output_dir or "reports/observation_universe_expansion"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"final_verdict={result.get('final_verdict', '')}")
    print(f"allow_expand_observation_universe={str(result.get('allow_expand_observation_universe', False)).lower()}")


if __name__ == "__main__":
    main()
