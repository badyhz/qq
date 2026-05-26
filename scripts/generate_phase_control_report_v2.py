from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.execution_guards import assert_dry_run_required, normalize_execution_mode


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def generate_phase_control_report_v2(
    *,
    phase_control_v1_json: str = "reports/phase_control/phase_control_report_v1.json",
    remediation_loop_packet_json: str = "reports/remediation_loop_packet/remediation_loop_packet.json",
    remediation_loop_run_report_json: str = "reports/remediation_loop_run/remediation_loop_run_report.json",
    remediation_result_json: str = "reports/remediation_result/remediation_result.json",
    shadow_research_kpi_json: str = "reports/shadow_research_kpi/kpi_dashboard.json",
    migration_checklist_json: str = "reports/research_to_testnet_migration/migration_checklist.json",
    output_dir: str = "reports/phase_control",
) -> dict[str, Any]:
    v1 = _read_json(Path(phase_control_v1_json))
    packet = _read_json(Path(remediation_loop_packet_json))
    run_report = _read_json(Path(remediation_loop_run_report_json))
    remediation_result = _read_json(Path(remediation_result_json))
    kpi = _read_json(Path(shadow_research_kpi_json))
    migration = _read_json(Path(migration_checklist_json))

    remediation_loop_completed = int(run_report.get("steps_total", 0) or 0) > 0
    not_ready_reasons = list(remediation_result.get("blocking_reasons_remaining", []))
    if not isinstance(not_ready_reasons, list):
        not_ready_reasons = []
    if not not_ready_reasons:
        not_ready_reasons = list(v1.get("not_ready_reasons", []))
        if not isinstance(not_ready_reasons, list):
            not_ready_reasons = []

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "final_verdict": "SHADOW_ONLY_CONTINUE",
        "completed_range": "T208-T360",
        "previous_report": "phase_control_report_v1",
        "remediation_loop_completed": bool(remediation_loop_completed),
        "remediation_effective": bool(remediation_result.get("remediation_effective", False)),
        "current_phase": "SHADOW_EXPERIMENT_REMEDIATION",
        "not_ready_reasons": sorted(set(str(item).strip() for item in not_ready_reasons if str(item).strip())),
        "recommended_next_action": str(
            remediation_result.get("recommended_next_action", v1.get("recommended_next_action", "CONTINUE_REMEDIATION_SHADOW_ONLY_LOOP"))
        ).strip()
        or "CONTINUE_REMEDIATION_SHADOW_ONLY_LOOP",
        "allowed_mode": "SHADOW_ONLY",
        "next_allowed_mode": str(migration.get("next_allowed_mode", "SHADOW_ONLY")).strip().upper() or "SHADOW_ONLY",
        "submit_allowed": False,
        "testnet_submit_allowed": False,
        "real_submit_allowed": False,
        "submit_attempted": False,
        "cancel_attempted": False,
        "flatten_attempted": False,
        "context": {
            "packet_commands_total": int(packet.get("commands_total", 0) or 0),
            "run_final_verdict": str(run_report.get("final_verdict", "")).strip().upper() or "UNKNOWN",
            "kpi_readiness_verdict": str(kpi.get("readiness_verdict", "")).strip().upper() or "UNKNOWN",
            "migration_verdict": str(migration.get("final_verdict", "")).strip().upper() or "UNKNOWN",
        },
    }

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "phase_control_report_v2.json"
    md_path = out_dir / "summary_v2.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Phase Control Report V2",
        "",
        f"- final_verdict: {report['final_verdict']}",
        f"- completed_range: {report['completed_range']}",
        f"- remediation_loop_completed: {str(report['remediation_loop_completed']).lower()}",
        f"- remediation_effective: {str(report['remediation_effective']).lower()}",
        f"- current_phase: {report['current_phase']}",
        f"- recommended_next_action: {report['recommended_next_action']}",
        "- allowed_mode: SHADOW_ONLY",
        "- submit_allowed: false",
        "- testnet_submit_allowed: false",
        "- real_submit_allowed: false",
    ]
    if report["not_ready_reasons"]:
        lines.append(f"- not_ready_reasons: {', '.join(report['not_ready_reasons'])}")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate phase control report v2 with remediation context")
    parser.add_argument("--phase-control-v1-json", default="reports/phase_control/phase_control_report_v1.json")
    parser.add_argument("--remediation-loop-packet-json", default="reports/remediation_loop_packet/remediation_loop_packet.json")
    parser.add_argument("--remediation-loop-run-report-json", default="reports/remediation_loop_run/remediation_loop_run_report.json")
    parser.add_argument("--remediation-result-json", default="reports/remediation_result/remediation_result.json")
    parser.add_argument("--shadow-research-kpi-json", default="reports/shadow_research_kpi/kpi_dashboard.json")
    parser.add_argument("--migration-checklist-json", default="reports/research_to_testnet_migration/migration_checklist.json")
    parser.add_argument("--output-dir", default="reports/phase_control")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    mode = normalize_execution_mode(os.environ.get("QQ_RUNTIME_MODE"))
    assert_dry_run_required(mode)
    args = build_arg_parser().parse_args()
    result = generate_phase_control_report_v2(
        phase_control_v1_json=str(args.phase_control_v1_json or "reports/phase_control/phase_control_report_v1.json"),
        remediation_loop_packet_json=str(args.remediation_loop_packet_json or "reports/remediation_loop_packet/remediation_loop_packet.json"),
        remediation_loop_run_report_json=str(
            args.remediation_loop_run_report_json or "reports/remediation_loop_run/remediation_loop_run_report.json"
        ),
        remediation_result_json=str(args.remediation_result_json or "reports/remediation_result/remediation_result.json"),
        shadow_research_kpi_json=str(args.shadow_research_kpi_json or "reports/shadow_research_kpi/kpi_dashboard.json"),
        migration_checklist_json=str(args.migration_checklist_json or "reports/research_to_testnet_migration/migration_checklist.json"),
        output_dir=str(args.output_dir or "reports/phase_control"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"final_verdict={result.get('final_verdict', '')}")
    print(f"recommended_next_action={result.get('recommended_next_action', '')}")


if __name__ == "__main__":
    main()
