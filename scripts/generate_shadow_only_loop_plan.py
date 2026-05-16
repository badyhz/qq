from __future__ import annotations

import argparse
import json
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


def generate_shadow_only_loop_plan(
    *,
    tuning_summary_json: str = "reports/shadow_experiment_tuning/summary.json",
    frequency_review_json: str = "reports/shadow_experiment_frequency_review/frequency_review.json",
    next_run_plan_summary_json: str = "reports/next_shadow_experiment_run_plan/summary.json",
    testnet_dry_run_readiness_json: str = "reports/testnet_dry_run_readiness/testnet_dry_run_readiness_report.json",
    operator_checklist_json: str = "reports/daily_operator_checklist/operator_checklist.json",
    output_dir: str = "reports/shadow_only_loop_plan",
) -> dict[str, Any]:
    tuning = _read_json(Path(tuning_summary_json))
    frequency = _read_json(Path(frequency_review_json))
    next_run = _read_json(Path(next_run_plan_summary_json))
    readiness = _read_json(Path(testnet_dry_run_readiness_json))
    checklist = _read_json(Path(operator_checklist_json))

    allow_frequency_up = bool(frequency.get("allow_increase_shadow_frequency", False))
    recommended_runs = 2 if allow_frequency_up else 1
    max_runs = 3 if allow_frequency_up else 1
    if str(next_run.get("allowed_mode", "SHADOW_ONLY")).strip().upper() != "SHADOW_ONLY":
        recommended_runs = 1
        max_runs = 1

    loop_steps = [
        {
            "step": 1,
            "name": "run_next_shadow_experiment_plan",
            "command": "PYTHONPATH=. ./.venv/bin/python scripts/run_next_shadow_experiment_plan.py --json",
        },
        {
            "step": 2,
            "name": "evaluate_shadow_experiment_outcomes",
            "command": "PYTHONPATH=. ./.venv/bin/python scripts/evaluate_shadow_experiment_outcomes.py --include-next-run-candidates --horizons 30,60,120 --primary-horizon 60 --json",
        },
        {
            "step": 3,
            "name": "generate_shadow_experiment_progress_gap_report",
            "command": "PYTHONPATH=. ./.venv/bin/python scripts/generate_shadow_experiment_progress_gap_report.py --json",
        },
        {
            "step": 4,
            "name": "analyze_shadow_experiment_trends",
            "command": "PYTHONPATH=. ./.venv/bin/python scripts/analyze_shadow_experiment_trends.py --json",
        },
        {
            "step": 5,
            "name": "generate_shadow_experiment_tuning_suggestions",
            "command": "PYTHONPATH=. ./.venv/bin/python scripts/generate_shadow_experiment_tuning_suggestions.py --json",
        },
        {
            "step": 6,
            "name": "generate_daily_shadow_research_control_report",
            "command": "PYTHONPATH=. ./.venv/bin/python scripts/generate_daily_shadow_research_control_report.py --json",
        },
    ]

    stop_conditions = [
        "system_health_fail",
        "missing_cache",
        "unexpected_submit_flag",
        "secret_leak_detected",
    ]
    continue_conditions = [
        "allowed_mode_shadow_only",
        "samples_below_target",
        "no_trade_actions_attempted",
    ]
    if bool(tuning.get("suggestion_count", 0)):
        continue_conditions.append("tuning_suggestions_available")
    if str(readiness.get("final_verdict", "")).strip().upper() == "NOT_READY":
        continue_conditions.append("testnet_not_ready_keep_shadow_only")
    if bool(checklist):
        continue_conditions.append("operator_checklist_loaded")

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "final_verdict": "PASS",
        "loop_mode": "SHADOW_ONLY",
        "recommended_runs_per_day": int(recommended_runs),
        "max_runs_per_day": int(max_runs),
        "allow_auto_submit": False,
        "allow_testnet_submit": False,
        "allow_real_submit": False,
        "stop_conditions": stop_conditions,
        "continue_conditions": continue_conditions,
        "loop_steps": loop_steps,
        "prohibited_actions": ["NO_TESTNET_SUBMIT", "NO_REAL_SUBMIT", "NO_CANCEL", "NO_FLATTEN"],
        "submit_attempted": False,
        "cancel_attempted": False,
        "flatten_attempted": False,
    }

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "shadow_only_loop_plan.json"
    md_path = out_dir / "summary.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Shadow Only Loop Plan",
        "",
        f"- final_verdict: {report['final_verdict']}",
        f"- loop_mode: {report['loop_mode']}",
        f"- recommended_runs_per_day: {report['recommended_runs_per_day']}",
        f"- max_runs_per_day: {report['max_runs_per_day']}",
        "- allow_auto_submit: false",
        "- allow_testnet_submit: false",
        "- allow_real_submit: false",
    ]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate safe SHADOW_ONLY loop execution plan")
    parser.add_argument("--tuning-summary-json", default="reports/shadow_experiment_tuning/summary.json")
    parser.add_argument("--frequency-review-json", default="reports/shadow_experiment_frequency_review/frequency_review.json")
    parser.add_argument("--next-run-plan-summary-json", default="reports/next_shadow_experiment_run_plan/summary.json")
    parser.add_argument("--testnet-dry-run-readiness-json", default="reports/testnet_dry_run_readiness/testnet_dry_run_readiness_report.json")
    parser.add_argument("--operator-checklist-json", default="reports/daily_operator_checklist/operator_checklist.json")
    parser.add_argument("--output-dir", default="reports/shadow_only_loop_plan")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = generate_shadow_only_loop_plan(
        tuning_summary_json=str(args.tuning_summary_json or "reports/shadow_experiment_tuning/summary.json"),
        frequency_review_json=str(args.frequency_review_json or "reports/shadow_experiment_frequency_review/frequency_review.json"),
        next_run_plan_summary_json=str(args.next_run_plan_summary_json or "reports/next_shadow_experiment_run_plan/summary.json"),
        testnet_dry_run_readiness_json=str(
            args.testnet_dry_run_readiness_json or "reports/testnet_dry_run_readiness/testnet_dry_run_readiness_report.json"
        ),
        operator_checklist_json=str(args.operator_checklist_json or "reports/daily_operator_checklist/operator_checklist.json"),
        output_dir=str(args.output_dir or "reports/shadow_only_loop_plan"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"final_verdict={result.get('final_verdict', '')}")
    print(f"recommended_runs_per_day={result.get('recommended_runs_per_day', 0)}")


if __name__ == "__main__":
    main()
