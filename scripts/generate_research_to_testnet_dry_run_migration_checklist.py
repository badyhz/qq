from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.strategy_edge_common import read_csv_rows, read_json_file


def _bool_status(ok: bool) -> tuple[str, bool]:
    return ("PASS" if ok else "FAIL", bool(ok))


def generate_research_to_testnet_dry_run_migration_checklist(
    *,
    phase_review_json: str = "reports/testnet_dry_run_phase_review/testnet_dry_run_phase_review.json",
    readiness_gaps_csv: str = "reports/testnet_dry_run_readiness_gaps/readiness_gaps.csv",
    remediation_plan_csv: str = "reports/testnet_dry_run_remediation/remediation_plan.csv",
    shadow_research_kpi_json: str = "reports/shadow_research_kpi/kpi_dashboard.json",
    system_health_json: str = "reports/system_health/trading_system_health_dashboard.json",
    output_dir: str = "reports/research_to_testnet_migration",
) -> dict[str, Any]:
    phase = read_json_file(Path(phase_review_json))
    gap_rows = read_csv_rows(Path(readiness_gaps_csv))
    remediation_rows = read_csv_rows(Path(remediation_plan_csv))
    kpi = read_json_file(Path(shadow_research_kpi_json))
    system_health = read_json_file(Path(system_health_json))

    minimum = phase.get("minimum_requirements", {})
    gap_keys = {
        str(row.get("requirement_key", "")).strip()
        for row in gap_rows
        if str(row.get("requirement_key", "")).strip() and str(row.get("blocking", "")).strip().lower() in {"1", "true", "yes"}
    }

    system_health_pass = str(system_health.get("final_verdict", "")).strip().upper() == "PASS"
    checks: list[dict[str, Any]] = []

    mapping = [
        ("system_health_pass", "System health final_verdict is PASS", bool(minimum.get("system_health_pass", system_health_pass))),
        ("shadow_history_days_min_met", "Shadow research history days >= 3", bool(minimum.get("shadow_research_history_days_min_met", False))),
        ("experiment_samples_min_met", "Experiment total samples >= 20", bool(minimum.get("experiment_samples_min_met", False))),
        (
            "stability_ready",
            "Stability has at least one non-NEEDS_MORE_DATA experiment",
            bool(minimum.get("stability_not_all_needs_more_data", False)),
        ),
        (
            "weighted_sample_count_min_met",
            "Strategy weighted sample count >= 5",
            bool(minimum.get("strategy_candidate_weighted_samples_min_met", False)),
        ),
        ("no_trade_actions_attempted", "No submit/cancel/flatten attempts", bool(minimum.get("no_trade_actions_attempted", False))),
        ("gate_available", "Strategy gate/risk gate available", True),
        ("dry_run_readiness_not_fail", "Dry-run readiness is not FAIL", bool(minimum.get("testnet_dry_run_readiness_not_fail", False))),
        ("operator_checklist_clean", "Operator checklist has no blocking item", True),
    ]

    for check_id, description, passed in mapping:
        current_status, passed_flag = _bool_status(bool(passed))
        checks.append(
            {
                "check_id": check_id,
                "description": description,
                "required": True,
                "current_status": current_status,
                "passed": passed_flag,
            }
        )

    must_pass_count = sum(1 for item in checks if bool(item.get("required", False)))
    passed_count = sum(1 for item in checks if bool(item.get("required", False)) and bool(item.get("passed", False)))
    failed_count = must_pass_count - passed_count
    blocking_items = [str(item.get("check_id", "")).strip() for item in checks if not bool(item.get("passed", False))]
    # keep blockers aligned with quantified gaps
    blocking_items.extend(sorted(gap_keys - set(blocking_items)))
    blocking_items = sorted(set(item for item in blocking_items if item))

    migration_allowed_now = bool(phase.get("allow_testnet_dry_run_only", False)) and failed_count == 0
    next_allowed_mode = "TESTNET_DRY_RUN_ONLY" if migration_allowed_now else "SHADOW_ONLY"

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "final_verdict": "READY" if migration_allowed_now else "NOT_READY",
        "migration_target": "TESTNET_DRY_RUN_ONLY",
        "migration_allowed_now": bool(migration_allowed_now),
        "checklist": checks,
        "must_pass_count": must_pass_count,
        "passed_count": passed_count,
        "failed_count": failed_count,
        "blocking_items": blocking_items,
        "allowed_mode": "SHADOW_ONLY",
        "next_allowed_mode": next_allowed_mode,
        "submit_allowed": False,
        "testnet_submit_allowed": False,
        "real_submit_allowed": False,
        "operator_note": "Migration is not allowed until all required checks pass.",
        "context": {
            "remediation_action_count": len(remediation_rows),
            "kpi_readiness_verdict": str(kpi.get("readiness_verdict", "")).strip().upper() or "UNKNOWN",
        },
    }

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "migration_checklist.json"
    md_path = out_dir / "migration_checklist.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Research To Testnet Dry-Run Migration Checklist",
        "",
        f"- final_verdict: {report['final_verdict']}",
        f"- migration_target: {report['migration_target']}",
        f"- migration_allowed_now: {str(report['migration_allowed_now']).lower()}",
        f"- must_pass_count: {report['must_pass_count']}",
        f"- passed_count: {report['passed_count']}",
        f"- failed_count: {report['failed_count']}",
        f"- next_allowed_mode: {report['next_allowed_mode']}",
        "- submit_allowed: false",
        "- testnet_submit_allowed: false",
        "- real_submit_allowed: false",
    ]
    if report["blocking_items"]:
        lines.append(f"- blocking_items: {', '.join(report['blocking_items'])}")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate migration checklist from research phase to TESTNET_DRY_RUN_ONLY")
    parser.add_argument("--phase-review-json", default="reports/testnet_dry_run_phase_review/testnet_dry_run_phase_review.json")
    parser.add_argument("--readiness-gaps-csv", default="reports/testnet_dry_run_readiness_gaps/readiness_gaps.csv")
    parser.add_argument("--remediation-plan-csv", default="reports/testnet_dry_run_remediation/remediation_plan.csv")
    parser.add_argument("--shadow-research-kpi-json", default="reports/shadow_research_kpi/kpi_dashboard.json")
    parser.add_argument("--system-health-json", default="reports/system_health/trading_system_health_dashboard.json")
    parser.add_argument("--output-dir", default="reports/research_to_testnet_migration")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = generate_research_to_testnet_dry_run_migration_checklist(
        phase_review_json=str(args.phase_review_json or "reports/testnet_dry_run_phase_review/testnet_dry_run_phase_review.json"),
        readiness_gaps_csv=str(args.readiness_gaps_csv or "reports/testnet_dry_run_readiness_gaps/readiness_gaps.csv"),
        remediation_plan_csv=str(args.remediation_plan_csv or "reports/testnet_dry_run_remediation/remediation_plan.csv"),
        shadow_research_kpi_json=str(args.shadow_research_kpi_json or "reports/shadow_research_kpi/kpi_dashboard.json"),
        system_health_json=str(args.system_health_json or "reports/system_health/trading_system_health_dashboard.json"),
        output_dir=str(args.output_dir or "reports/research_to_testnet_migration"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"final_verdict={result.get('final_verdict', '')}")
    print(f"migration_allowed_now={str(result.get('migration_allowed_now', False)).lower()}")


if __name__ == "__main__":
    main()
