from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.strategy_edge_common import read_csv_rows


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def generate_shadow_loop_execution_packet(
    *,
    next_run_plan_v2_summary_json: str = "reports/next_shadow_experiment_run_plan_v2/summary.json",
    next_run_plan_v2_csv: str = "reports/next_shadow_experiment_run_plan_v2/next_shadow_experiment_run_plan_v2.csv",
    shadow_only_loop_plan_json: str = "reports/shadow_only_loop_plan/shadow_only_loop_plan.json",
    daily_research_control_json: str = "reports/daily_shadow_research_control/daily_shadow_research_control_report.json",
    testnet_dry_run_readiness_json: str = "reports/testnet_dry_run_readiness/testnet_dry_run_readiness_report.json",
    output_dir: str = "reports/shadow_loop_execution_packet",
) -> dict[str, Any]:
    v2_summary = _read_json(Path(next_run_plan_v2_summary_json))
    v2_rows = read_csv_rows(Path(next_run_plan_v2_csv))
    loop_plan = _read_json(Path(shadow_only_loop_plan_json))
    research = _read_json(Path(daily_research_control_json))
    readiness = _read_json(Path(testnet_dry_run_readiness_json))

    commands = [
        {
            "step": 1,
            "name": "run_next_shadow_experiment_plan_v2",
            "command": "PYTHONPATH=. ./.venv/bin/python scripts/run_next_shadow_experiment_plan.py --plan-csv reports/next_shadow_experiment_run_plan_v2/next_shadow_experiment_run_plan_v2.csv --json",
            "expected_outputs": ["reports/next_shadow_experiment_run/summary.json"],
            "stop_on_failure": True,
        },
        {
            "step": 2,
            "name": "evaluate_shadow_experiment_outcomes",
            "command": "PYTHONPATH=. ./.venv/bin/python scripts/evaluate_shadow_experiment_outcomes.py --include-next-run-candidates --horizons 30,60,120 --primary-horizon 60 --json",
            "expected_outputs": ["reports/shadow_experiment_outcomes/summary.json"],
            "stop_on_failure": True,
        },
        {
            "step": 3,
            "name": "apply_next_shadow_experiment_run_results_preview",
            "command": "PYTHONPATH=. ./.venv/bin/python scripts/apply_next_shadow_experiment_run_results.py --json",
            "expected_outputs": ["reports/next_shadow_experiment_run_applied/summary.json"],
            "stop_on_failure": True,
        },
        {
            "step": 4,
            "name": "generate_shadow_experiment_progress_gap_report",
            "command": "PYTHONPATH=. ./.venv/bin/python scripts/generate_shadow_experiment_progress_gap_report.py --json",
            "expected_outputs": ["reports/shadow_experiment_progress_gap/summary.json"],
            "stop_on_failure": True,
        },
        {
            "step": 5,
            "name": "analyze_shadow_experiment_trends",
            "command": "PYTHONPATH=. ./.venv/bin/python scripts/analyze_shadow_experiment_trends.py --json",
            "expected_outputs": ["reports/shadow_experiment_trends/summary.json"],
            "stop_on_failure": True,
        },
        {
            "step": 6,
            "name": "generate_shadow_experiment_tuning_suggestions",
            "command": "PYTHONPATH=. ./.venv/bin/python scripts/generate_shadow_experiment_tuning_suggestions.py --json",
            "expected_outputs": ["reports/shadow_experiment_tuning/summary.json"],
            "stop_on_failure": True,
        },
        {
            "step": 7,
            "name": "generate_daily_shadow_research_control_report",
            "command": "PYTHONPATH=. ./.venv/bin/python scripts/generate_daily_shadow_research_control_report.py --json",
            "expected_outputs": ["reports/daily_shadow_research_control/daily_shadow_research_control_report.json"],
            "stop_on_failure": True,
        },
    ]

    packet = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "final_verdict": "PASS",
        "packet_mode": "SHADOW_ONLY",
        "plan_version": "v2",
        "commands_total": len(commands),
        "preflight_checks": [
            "allowed_mode_is_shadow_only",
            "submit_disabled",
            "public_data_only",
        ],
        "commands": commands,
        "manual_apply_command": "PYTHONPATH=. ./.venv/bin/python scripts/apply_next_shadow_experiment_run_results.py --apply --confirm-shadow-only --json",
        "prohibited_actions": [
            "NO_TESTNET_SUBMIT",
            "NO_REAL_SUBMIT",
            "NO_CANCEL",
            "NO_FLATTEN",
            "NO_BYPASS_STRATEGY_GATE",
        ],
        "submit_attempted": False,
        "cancel_attempted": False,
        "flatten_attempted": False,
        "context": {
            "plan_v2_row_count": int(v2_summary.get("plan_v2_row_count", len(v2_rows)) or 0),
            "research_final_verdict": str(research.get("final_verdict", "")).strip().upper(),
            "testnet_readiness_final_verdict": str(readiness.get("final_verdict", "")).strip().upper(),
            "loop_mode": str(loop_plan.get("loop_mode", "SHADOW_ONLY")).strip().upper(),
        },
    }

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    packet_json = out_dir / "execution_packet.json"
    commands_md = out_dir / "execution_commands.md"
    summary_md = out_dir / "summary.md"
    packet_json.write_text(json.dumps(packet, ensure_ascii=False, indent=2), encoding="utf-8")

    command_lines = ["# Shadow Loop Execution Commands", ""]
    for item in commands:
        command_lines.append(f"## Step {item['step']}: {item['name']}")
        command_lines.append("")
        command_lines.append(f"`{item['command']}`")
        command_lines.append("")
    command_lines.append("## Manual Apply (Optional, Requires Confirmation)")
    command_lines.append("")
    command_lines.append(f"`{packet['manual_apply_command']}`")
    command_lines.append("")
    commands_md.write_text("\n".join(command_lines), encoding="utf-8")

    lines = [
        "# Shadow Loop Execution Packet",
        "",
        f"- final_verdict: {packet['final_verdict']}",
        f"- packet_mode: {packet['packet_mode']}",
        f"- plan_version: {packet['plan_version']}",
        f"- commands_total: {packet['commands_total']}",
        "- submit_attempted: false",
        "- cancel_attempted: false",
        "- flatten_attempted: false",
    ]
    summary_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return packet


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate execution packet for SHADOW_ONLY loop")
    parser.add_argument("--next-run-plan-v2-summary-json", default="reports/next_shadow_experiment_run_plan_v2/summary.json")
    parser.add_argument("--next-run-plan-v2-csv", default="reports/next_shadow_experiment_run_plan_v2/next_shadow_experiment_run_plan_v2.csv")
    parser.add_argument("--shadow-only-loop-plan-json", default="reports/shadow_only_loop_plan/shadow_only_loop_plan.json")
    parser.add_argument("--daily-research-control-json", default="reports/daily_shadow_research_control/daily_shadow_research_control_report.json")
    parser.add_argument("--testnet-dry-run-readiness-json", default="reports/testnet_dry_run_readiness/testnet_dry_run_readiness_report.json")
    parser.add_argument("--output-dir", default="reports/shadow_loop_execution_packet")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = generate_shadow_loop_execution_packet(
        next_run_plan_v2_summary_json=str(args.next_run_plan_v2_summary_json or "reports/next_shadow_experiment_run_plan_v2/summary.json"),
        next_run_plan_v2_csv=str(args.next_run_plan_v2_csv or "reports/next_shadow_experiment_run_plan_v2/next_shadow_experiment_run_plan_v2.csv"),
        shadow_only_loop_plan_json=str(args.shadow_only_loop_plan_json or "reports/shadow_only_loop_plan/shadow_only_loop_plan.json"),
        daily_research_control_json=str(
            args.daily_research_control_json or "reports/daily_shadow_research_control/daily_shadow_research_control_report.json"
        ),
        testnet_dry_run_readiness_json=str(
            args.testnet_dry_run_readiness_json or "reports/testnet_dry_run_readiness/testnet_dry_run_readiness_report.json"
        ),
        output_dir=str(args.output_dir or "reports/shadow_loop_execution_packet"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"final_verdict={result.get('final_verdict', '')}")
    print(f"commands_total={result.get('commands_total', 0)}")


if __name__ == "__main__":
    main()
