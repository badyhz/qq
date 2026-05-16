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


def _action_to_command(action_type: str) -> tuple[str, str, list[str]]:
    action = action_type.strip().upper()
    if action == "RUN_SHADOW_ONLY_LOOP":
        return (
            "run_shadow_loop_once",
            "PYTHONPATH=. ./.venv/bin/python scripts/run_next_shadow_experiment_plan.py --json",
            ["reports/next_shadow_experiment_run/summary.json"],
        )
    if action == "COLLECT_MORE_SHADOW_SAMPLES":
        return (
            "collect_more_shadow_samples",
            "PYTHONPATH=. ./.venv/bin/python scripts/run_next_shadow_experiment_plan.py --json",
            ["reports/next_shadow_experiment_run/summary.json"],
        )
    if action == "BUILD_HISTORY_DAYS":
        return (
            "update_shadow_research_history",
            "PYTHONPATH=. ./.venv/bin/python scripts/update_shadow_research_history.py --json",
            ["reports/shadow_research_history/summary.json"],
        )
    if action == "RECOMPUTE_STABILITY":
        return (
            "recompute_experiment_stability",
            "PYTHONPATH=. ./.venv/bin/python scripts/calculate_shadow_experiment_stability_score.py --json",
            ["reports/shadow_experiment_stability/summary.json"],
        )
    if action == "RECOMPUTE_PHASE_REVIEW":
        return (
            "recompute_phase_review",
            "PYTHONPATH=. ./.venv/bin/python scripts/generate_testnet_dry_run_phase_review.py --json",
            ["reports/testnet_dry_run_phase_review/testnet_dry_run_phase_review.json"],
        )
    if action == "KEEP_SYSTEM_HEALTH_PASS":
        return (
            "refresh_system_health_dashboard",
            "PYTHONPATH=. ./.venv/bin/python scripts/generate_trading_system_health_dashboard.py --json",
            ["reports/system_health/trading_system_health_dashboard.json"],
        )
    return (
        "unknown_action",
        "PYTHONPATH=. ./.venv/bin/python scripts/generate_daily_shadow_research_control_report.py --json",
        ["reports/daily_shadow_research_control/daily_shadow_research_control_report.json"],
    )


def generate_remediation_loop_packet(
    *,
    remediation_plan_csv: str = "reports/testnet_dry_run_remediation/remediation_plan.csv",
    remediation_summary_json: str = "reports/testnet_dry_run_remediation/summary.json",
    shadow_loop_execution_packet_json: str = "reports/shadow_loop_execution_packet/execution_packet.json",
    phase_control_v1_json: str = "reports/phase_control/phase_control_report_v1.json",
    output_dir: str = "reports/remediation_loop_packet",
) -> dict[str, Any]:
    remediation_rows = read_csv_rows(Path(remediation_plan_csv))
    remediation_summary = _read_json(Path(remediation_summary_json))
    previous_packet = _read_json(Path(shadow_loop_execution_packet_json))
    phase_control_v1 = _read_json(Path(phase_control_v1_json))

    commands: list[dict[str, Any]] = []
    seen_actions: set[str] = set()
    for row in remediation_rows:
        action_type = str(row.get("action_type", "UNKNOWN")).strip().upper() or "UNKNOWN"
        if action_type in seen_actions:
            continue
        seen_actions.add(action_type)
        name, command, expected_outputs = _action_to_command(action_type)
        commands.append(
            {
                "step": len(commands) + 1,
                "action_type": action_type,
                "name": name,
                "command": command,
                "expected_outputs": expected_outputs,
                "stop_on_failure": True,
            }
        )

    # Append a research-control refresh command to close the loop.
    commands.append(
        {
            "step": len(commands) + 1,
            "action_type": "RECOMPUTE_CONTROL",
            "name": "refresh_daily_shadow_research_control",
            "command": "PYTHONPATH=. ./.venv/bin/python scripts/generate_daily_shadow_research_control_report.py --json",
            "expected_outputs": ["reports/daily_shadow_research_control/daily_shadow_research_control_report.json"],
            "stop_on_failure": True,
        }
    )
    for idx, row in enumerate(commands, start=1):
        row["step"] = idx

    final_verdict = "PASS" if remediation_rows else "PARTIAL"
    packet = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "final_verdict": final_verdict,
        "packet_mode": "SHADOW_ONLY",
        "remediation_action_count": len(remediation_rows),
        "commands_total": len(commands),
        "commands": commands,
        "preflight_checks": [
            "allowed_mode_is_shadow_only",
            "submit_disabled",
            "no_secret_required",
        ],
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
            "recommended_next_action": str(
                remediation_summary.get(
                    "recommended_next_action",
                    phase_control_v1.get("recommended_next_action", "RUN_REMEDIATION_SHADOW_ONLY_LOOP"),
                )
            ).strip()
            or "RUN_REMEDIATION_SHADOW_ONLY_LOOP",
            "previous_packet_commands_total": int(previous_packet.get("commands_total", 0) or 0),
        },
    }

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    packet_json = out_dir / "remediation_loop_packet.json"
    commands_md = out_dir / "remediation_commands.md"
    summary_md = out_dir / "summary.md"
    packet_json.write_text(json.dumps(packet, ensure_ascii=False, indent=2), encoding="utf-8")

    cmd_lines = ["# Remediation Loop Commands", ""]
    for row in commands:
        cmd_lines.append(f"{row['step']}. `{row['command']}`")
    commands_md.write_text("\n".join(cmd_lines) + "\n", encoding="utf-8")

    summary_lines = [
        "# Remediation Loop Packet",
        "",
        f"- final_verdict: {packet['final_verdict']}",
        f"- packet_mode: {packet['packet_mode']}",
        f"- remediation_action_count: {packet['remediation_action_count']}",
        f"- commands_total: {packet['commands_total']}",
        "- submit_attempted: false",
        "- cancel_attempted: false",
        "- flatten_attempted: false",
    ]
    summary_md.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
    return packet


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate executable remediation loop packet (shadow-only)")
    parser.add_argument("--remediation-plan-csv", default="reports/testnet_dry_run_remediation/remediation_plan.csv")
    parser.add_argument("--remediation-summary-json", default="reports/testnet_dry_run_remediation/summary.json")
    parser.add_argument("--shadow-loop-execution-packet-json", default="reports/shadow_loop_execution_packet/execution_packet.json")
    parser.add_argument("--phase-control-v1-json", default="reports/phase_control/phase_control_report_v1.json")
    parser.add_argument("--output-dir", default="reports/remediation_loop_packet")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = generate_remediation_loop_packet(
        remediation_plan_csv=str(args.remediation_plan_csv or "reports/testnet_dry_run_remediation/remediation_plan.csv"),
        remediation_summary_json=str(args.remediation_summary_json or "reports/testnet_dry_run_remediation/summary.json"),
        shadow_loop_execution_packet_json=str(
            args.shadow_loop_execution_packet_json or "reports/shadow_loop_execution_packet/execution_packet.json"
        ),
        phase_control_v1_json=str(args.phase_control_v1_json or "reports/phase_control/phase_control_report_v1.json"),
        output_dir=str(args.output_dir or "reports/remediation_loop_packet"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"final_verdict={result.get('final_verdict', '')}")
    print(f"commands_total={result.get('commands_total', 0)}")


if __name__ == "__main__":
    main()
