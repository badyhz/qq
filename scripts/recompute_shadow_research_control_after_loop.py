from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.strategy_edge_common import to_float_nan


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


def recompute_shadow_research_control_after_loop(
    *,
    next_run_summary_json: str = "reports/next_shadow_experiment_run/summary.json",
    experiment_outcomes_summary_json: str = "reports/shadow_experiment_outcomes/summary.json",
    next_run_applied_summary_json: str = "reports/next_shadow_experiment_run_applied/summary.json",
    progress_gap_summary_json: str = "reports/shadow_experiment_progress_gap/summary.json",
    trends_summary_json: str = "reports/shadow_experiment_trends/summary.json",
    tuning_summary_json: str = "reports/shadow_experiment_tuning/summary.json",
    daily_research_control_json: str = "reports/daily_shadow_research_control/daily_shadow_research_control_report.json",
    output_dir: str = "reports/shadow_research_recompute",
) -> dict[str, Any]:
    next_run = _read_json(Path(next_run_summary_json))
    outcomes = _read_json(Path(experiment_outcomes_summary_json))
    applied = _read_json(Path(next_run_applied_summary_json))
    gap = _read_json(Path(progress_gap_summary_json))
    trends = _read_json(Path(trends_summary_json))
    tuning = _read_json(Path(tuning_summary_json))
    control = _read_json(Path(daily_research_control_json))

    recomputed = []
    for name, payload in [
        ("shadow_experiment_progress_gap", gap),
        ("shadow_experiment_trends", trends),
        ("shadow_experiment_tuning", tuning),
        ("daily_shadow_research_control", control),
    ]:
        if payload:
            recomputed.append(name)

    apply_status = "DRY_RUN_ONLY"
    if bool(applied.get("apply", False)):
        apply_status = "APPLIED_CONFIRMED_SHADOW_ONLY"
    if bool(applied.get("error")):
        apply_status = "APPLY_FAILED"

    missing = []
    for name, payload in [
        ("next_run_summary", next_run),
        ("outcomes_summary", outcomes),
        ("applied_summary", applied),
        ("daily_research_control", control),
    ]:
        if not payload:
            missing.append(name)

    final_verdict = "PASS"
    if missing:
        final_verdict = "PARTIAL"
    if str(control.get("final_verdict", "")).strip().upper() == "PARTIAL":
        final_verdict = "PARTIAL"

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "final_verdict": final_verdict,
        "recomputed_reports": recomputed,
        "next_run_candidate_count": _to_int(next_run.get("next_run_candidate_count"), 0),
        "evaluated_count": _to_int(outcomes.get("evaluated_count"), 0),
        "apply_status": apply_status,
        "research_control_verdict": str(control.get("final_verdict", "PARTIAL")).strip().upper() or "PARTIAL",
        "recommended_next_action": str(control.get("recommended_next_action", "RUN_SHADOW_ONLY_LOOP_ONCE")).strip().upper() or "RUN_SHADOW_ONLY_LOOP_ONCE",
        "submit_attempted": False,
        "cancel_attempted": False,
        "flatten_attempted": False,
        "allowed_mode": "SHADOW_ONLY",
        "missing_dependencies": missing,
    }

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "recompute_report.json"
    md_path = out_dir / "summary.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Shadow Research Recompute Report",
        "",
        f"- final_verdict: {report['final_verdict']}",
        f"- next_run_candidate_count: {report['next_run_candidate_count']}",
        f"- evaluated_count: {report['evaluated_count']}",
        f"- apply_status: {report['apply_status']}",
        f"- research_control_verdict: {report['research_control_verdict']}",
        f"- recommended_next_action: {report['recommended_next_action']}",
        "- allowed_mode: SHADOW_ONLY",
        "- submit_attempted: false",
        "- cancel_attempted: false",
        "- flatten_attempted: false",
    ]
    if missing:
        lines.append(f"- missing_dependencies: {', '.join(missing)}")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Recompute shadow research control report after a loop run")
    parser.add_argument("--next-run-summary-json", default="reports/next_shadow_experiment_run/summary.json")
    parser.add_argument("--experiment-outcomes-summary-json", default="reports/shadow_experiment_outcomes/summary.json")
    parser.add_argument("--next-run-applied-summary-json", default="reports/next_shadow_experiment_run_applied/summary.json")
    parser.add_argument("--progress-gap-summary-json", default="reports/shadow_experiment_progress_gap/summary.json")
    parser.add_argument("--trends-summary-json", default="reports/shadow_experiment_trends/summary.json")
    parser.add_argument("--tuning-summary-json", default="reports/shadow_experiment_tuning/summary.json")
    parser.add_argument("--daily-research-control-json", default="reports/daily_shadow_research_control/daily_shadow_research_control_report.json")
    parser.add_argument("--output-dir", default="reports/shadow_research_recompute")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = recompute_shadow_research_control_after_loop(
        next_run_summary_json=str(args.next_run_summary_json or "reports/next_shadow_experiment_run/summary.json"),
        experiment_outcomes_summary_json=str(args.experiment_outcomes_summary_json or "reports/shadow_experiment_outcomes/summary.json"),
        next_run_applied_summary_json=str(args.next_run_applied_summary_json or "reports/next_shadow_experiment_run_applied/summary.json"),
        progress_gap_summary_json=str(args.progress_gap_summary_json or "reports/shadow_experiment_progress_gap/summary.json"),
        trends_summary_json=str(args.trends_summary_json or "reports/shadow_experiment_trends/summary.json"),
        tuning_summary_json=str(args.tuning_summary_json or "reports/shadow_experiment_tuning/summary.json"),
        daily_research_control_json=str(
            args.daily_research_control_json or "reports/daily_shadow_research_control/daily_shadow_research_control_report.json"
        ),
        output_dir=str(args.output_dir or "reports/shadow_research_recompute"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"final_verdict={result.get('final_verdict', '')}")
    print(f"apply_status={result.get('apply_status', '')}")


if __name__ == "__main__":
    main()
