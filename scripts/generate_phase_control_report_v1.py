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


def generate_phase_control_report_v1(
    *,
    shadow_research_kpi_json: str = "reports/shadow_research_kpi/kpi_dashboard.json",
    migration_checklist_json: str = "reports/research_to_testnet_migration/migration_checklist.json",
    testnet_dry_run_phase_review_json: str = "reports/testnet_dry_run_phase_review/testnet_dry_run_phase_review.json",
    daily_shadow_research_control_json: str = "reports/daily_shadow_research_control/daily_shadow_research_control_report.json",
    system_health_json: str = "reports/system_health/trading_system_health_dashboard.json",
    shadow_only_loop_plan_json: str = "reports/shadow_only_loop_plan/shadow_only_loop_plan.json",
    output_dir: str = "reports/phase_control",
) -> dict[str, Any]:
    kpi = _read_json(Path(shadow_research_kpi_json))
    migration = _read_json(Path(migration_checklist_json))
    phase_review = _read_json(Path(testnet_dry_run_phase_review_json))
    daily = _read_json(Path(daily_shadow_research_control_json))
    system_health = _read_json(Path(system_health_json))
    loop_plan = _read_json(Path(shadow_only_loop_plan_json))

    migration_allowed_now = bool(migration.get("migration_allowed_now", False))
    current_phase = str(
        daily.get("current_phase", kpi.get("current_phase", "SHADOW_EXPERIMENT_COLLECTION"))
    ).strip().upper() or "SHADOW_EXPERIMENT_COLLECTION"
    not_ready_reasons = list(phase_review.get("blocking_reasons", []))
    if not isinstance(not_ready_reasons, list):
        not_ready_reasons = []

    final_verdict = "TESTNET_DRY_RUN_ONLY_READY" if migration_allowed_now else "SHADOW_ONLY_CONTINUE"
    recommended_next_action = str(
        kpi.get("recommended_next_action", daily.get("recommended_next_action", "RUN_REMEDIATION_SHADOW_ONLY_LOOP"))
    ).strip() or "RUN_REMEDIATION_SHADOW_ONLY_LOOP"

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "final_verdict": final_verdict,
        "completed_range": "T208-T355",
        "current_phase": current_phase,
        "completed_layers": [
            "testnet_execution_safety",
            "protection_order_lifecycle",
            "trade_lifecycle_reporting",
            "strategy_gate",
            "shadow_sample_collection",
            "shadow_experiment_pipeline",
            "shadow_research_control",
        ],
        "not_ready_reasons": sorted(set(str(item).strip() for item in not_ready_reasons if str(item).strip())),
        "recommended_next_action": recommended_next_action,
        "allowed_mode": "SHADOW_ONLY",
        "next_allowed_mode": str(migration.get("next_allowed_mode", "SHADOW_ONLY")).strip().upper() or "SHADOW_ONLY",
        "submit_allowed": False,
        "testnet_submit_allowed": False,
        "real_submit_allowed": False,
        "prohibited_actions": [
            "NO_REAL_SUBMIT",
            "NO_TESTNET_SUBMIT",
            "NO_CANCEL",
            "NO_FLATTEN",
            "NO_BYPASS_STRATEGY_GATE",
        ],
        "submit_attempted": False,
        "cancel_attempted": False,
        "flatten_attempted": False,
        "context": {
            "readiness_verdict": str(phase_review.get("final_verdict", "")).strip().upper() or "UNKNOWN",
            "kpi_verdict": str(kpi.get("final_verdict", "")).strip().upper() or "UNKNOWN",
            "migration_verdict": str(migration.get("final_verdict", "")).strip().upper() or "UNKNOWN",
            "system_health_verdict": str(system_health.get("final_verdict", "")).strip().upper() or "UNKNOWN",
            "loop_mode": str(loop_plan.get("loop_mode", "SHADOW_ONLY")).strip().upper() or "SHADOW_ONLY",
        },
    }

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "phase_control_report_v1.json"
    md_path = out_dir / "summary.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Phase Control Report V1",
        "",
        f"- final_verdict: {report['final_verdict']}",
        f"- completed_range: {report['completed_range']}",
        f"- current_phase: {report['current_phase']}",
        f"- recommended_next_action: {report['recommended_next_action']}",
        f"- next_allowed_mode: {report['next_allowed_mode']}",
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
    parser = argparse.ArgumentParser(description="Generate stage-level phase control report")
    parser.add_argument("--shadow-research-kpi-json", default="reports/shadow_research_kpi/kpi_dashboard.json")
    parser.add_argument("--migration-checklist-json", default="reports/research_to_testnet_migration/migration_checklist.json")
    parser.add_argument("--testnet-dry-run-phase-review-json", default="reports/testnet_dry_run_phase_review/testnet_dry_run_phase_review.json")
    parser.add_argument("--daily-shadow-research-control-json", default="reports/daily_shadow_research_control/daily_shadow_research_control_report.json")
    parser.add_argument("--system-health-json", default="reports/system_health/trading_system_health_dashboard.json")
    parser.add_argument("--shadow-only-loop-plan-json", default="reports/shadow_only_loop_plan/shadow_only_loop_plan.json")
    parser.add_argument("--output-dir", default="reports/phase_control")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    mode = normalize_execution_mode(os.environ.get("QQ_RUNTIME_MODE"))
    assert_dry_run_required(mode)
    args = build_arg_parser().parse_args()
    result = generate_phase_control_report_v1(
        shadow_research_kpi_json=str(args.shadow_research_kpi_json or "reports/shadow_research_kpi/kpi_dashboard.json"),
        migration_checklist_json=str(
            args.migration_checklist_json or "reports/research_to_testnet_migration/migration_checklist.json"
        ),
        testnet_dry_run_phase_review_json=str(
            args.testnet_dry_run_phase_review_json or "reports/testnet_dry_run_phase_review/testnet_dry_run_phase_review.json"
        ),
        daily_shadow_research_control_json=str(
            args.daily_shadow_research_control_json or "reports/daily_shadow_research_control/daily_shadow_research_control_report.json"
        ),
        system_health_json=str(args.system_health_json or "reports/system_health/trading_system_health_dashboard.json"),
        shadow_only_loop_plan_json=str(args.shadow_only_loop_plan_json or "reports/shadow_only_loop_plan/shadow_only_loop_plan.json"),
        output_dir=str(args.output_dir or "reports/phase_control"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"final_verdict={result.get('final_verdict', '')}")
    print(f"recommended_next_action={result.get('recommended_next_action', '')}")


if __name__ == "__main__":
    main()
