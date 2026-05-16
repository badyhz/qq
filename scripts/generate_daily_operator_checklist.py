from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _checkbox(value: bool) -> str:
    return "x" if value else " "


def generate_daily_operator_checklist(
    *,
    system_health_json: str = "reports/system_health/trading_system_health_dashboard.json",
    gate_dashboard_json: str = "reports/gate_dashboard/gate_decision_dashboard.json",
    runner_dry_run_report_json: str = "reports/runner_dry_run/runner_dry_run_report.json",
    testnet_reset_readiness_json: str = "reports/testnet_reset_readiness/testnet_reset_readiness.json",
    next_day_plan_summary_json: str = "reports/next_trading_day_strategy_plan/summary.json",
    output_dir: str = "reports/daily_operator_checklist",
) -> dict[str, Any]:
    system_health = _load_json(Path(system_health_json))
    gate_dashboard = _load_json(Path(gate_dashboard_json))
    runner_report = _load_json(Path(runner_dry_run_report_json))
    readiness = _load_json(Path(testnet_reset_readiness_json))
    next_day_plan = _load_json(Path(next_day_plan_summary_json))

    account_state = dict(system_health.get("account_state", {})) if isinstance(system_health.get("account_state", {}), dict) else {}
    anomaly_summary = dict(system_health.get("anomaly_summary", {})) if isinstance(system_health.get("anomaly_summary", {}), dict) else {}
    quality_summary = dict(system_health.get("quality_summary", {})) if isinstance(system_health.get("quality_summary", {}), dict) else {}
    gate_by_decision = dict(gate_dashboard.get("by_decision", {})) if isinstance(gate_dashboard.get("by_decision", {}), dict) else {}

    checks = {
        "account_flat_clean": str(account_state.get("position_status", "")).strip().upper() == "FLAT_CLEAN",
        "no_orphan_orders": str(account_state.get("orphan_status", "")).strip().upper() == "CLEAN",
        "no_pending_or_approved_candidate": int(account_state.get("pending_candidate_count", 0) or 0) == 0
        and int(account_state.get("approved_candidate_count", 0) or 0) == 0,
        "system_health_pass": str(system_health.get("final_verdict", "UNKNOWN")).strip().upper() == "PASS",
        "execution_quality_ge_90": float(quality_summary.get("avg_execution_quality_score", 0.0) or 0.0) >= 90.0,
        "no_critical_anomalies": int(anomaly_summary.get("critical_count", 0) or 0) == 0,
        "gate_dashboard_reviewed": bool(gate_dashboard),
        "no_block_system_health": int(gate_by_decision.get("BLOCK_SYSTEM_HEALTH", 0) or 0) == 0,
        "low_sample_acknowledged": int(gate_by_decision.get("BLOCK_LOW_SAMPLE", 0) or 0) >= 0,
        "reset_readiness_ready": str(readiness.get("readiness_verdict", "NOT_READY")).strip().upper() == "READY",
        "approved_candidate_exists": bool(dict(readiness.get("minimum_conditions", {})).get("has_approved_candidate", False)),
        "strategy_gate_allows_submit": bool(readiness.get("can_submit_after_reset", False)),
        "runner_dry_run_safe": str(runner_report.get("safety_verdict", "UNKNOWN")).strip().upper() == "PASS",
    }

    allowed_actions = list(readiness.get("allowed_actions_after_reset", []))
    if not allowed_actions:
        allowed_actions = ["OBSERVE_ONLY", "TESTNET_DRY_RUN_ONLY"]

    prohibited_actions = [
        "NO_REAL_SUBMIT",
        "NO_TESTNET_SUBMIT" if not bool(readiness.get("can_submit_after_reset", False)) else "NO_TESTNET_SUBMIT_UNLESS_GATE_ALLOWS",
        "DO_NOT_BYPASS_STRATEGY_GATE",
        "NO_CANCEL_OR_FLATTEN_WITHOUT_ORPHAN_DIAGNOSIS",
    ]

    final_verdict = "PASS"
    if not checks["runner_dry_run_safe"] or not checks["system_health_pass"]:
        final_verdict = "PARTIAL"
    if str(readiness.get("readiness_verdict", "NOT_READY")).strip().upper() != "READY":
        final_verdict = "PARTIAL"

    checklist_json = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "final_verdict": final_verdict,
        "checks": checks,
        "allowed_actions": allowed_actions,
        "prohibited_actions": prohibited_actions,
        "context": {
            "system_health_verdict": str(system_health.get("final_verdict", "UNKNOWN")),
            "gate_dashboard_verdict": str(gate_dashboard.get("final_verdict", "UNKNOWN")),
            "runner_safety_verdict": str(runner_report.get("safety_verdict", "UNKNOWN")),
            "reset_readiness_verdict": str(readiness.get("readiness_verdict", "UNKNOWN")),
            "next_day_plan_final_verdict": str(next_day_plan.get("final_verdict", "UNKNOWN")),
        },
    }

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    md_path = out_dir / "operator_checklist.md"
    json_path = out_dir / "operator_checklist.json"
    checklist_json["output_paths"] = {
        "operator_checklist_md": str(md_path),
        "operator_checklist_json": str(json_path),
    }
    json_path.write_text(json.dumps(checklist_json, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Daily Operator Checklist",
        "",
        "## 1. Account Safety",
        f"- [{_checkbox(checks['account_flat_clean'])}] Account is FLAT_CLEAN",
        f"- [{_checkbox(checks['no_orphan_orders'])}] No orphan orders",
        f"- [{_checkbox(checks['no_pending_or_approved_candidate'])}] No pending approved candidate",
        "",
        "## 2. System Health",
        f"- [{_checkbox(checks['system_health_pass'])}] system_health final_verdict is PASS",
        f"- [{_checkbox(checks['execution_quality_ge_90'])}] execution quality average >= 90",
        f"- [{_checkbox(checks['no_critical_anomalies'])}] no critical anomalies",
        "",
        "## 3. Strategy Gate",
        f"- [{_checkbox(checks['gate_dashboard_reviewed'])}] gate dashboard reviewed",
        f"- [{_checkbox(checks['no_block_system_health'])}] no BLOCK_SYSTEM_HEALTH",
        f"- [{_checkbox(checks['low_sample_acknowledged'])}] LOW_SAMPLE blocks acknowledged",
        "",
        "## 4. Reset Readiness",
        f"- [{_checkbox(checks['reset_readiness_ready'])}] readiness_verdict is READY",
        f"- [{_checkbox(checks['approved_candidate_exists'])}] approved candidate exists",
        f"- [{_checkbox(checks['strategy_gate_allows_submit'])}] strategy gate allows submit",
        f"- [{_checkbox(checks['runner_dry_run_safe'])}] runner dry-run safety is PASS",
        "",
        "## 5. Allowed Actions Today",
    ]
    for item in allowed_actions:
        lines.append(f"- {item}")
    lines.extend(["", "## 6. Explicit Prohibited Actions"])
    for item in prohibited_actions:
        lines.append(f"- {item}")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return checklist_json


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate daily operator checklist from gate/system reports")
    parser.add_argument("--system-health-json", default="reports/system_health/trading_system_health_dashboard.json")
    parser.add_argument("--gate-dashboard-json", default="reports/gate_dashboard/gate_decision_dashboard.json")
    parser.add_argument("--runner-dry-run-report-json", default="reports/runner_dry_run/runner_dry_run_report.json")
    parser.add_argument("--testnet-reset-readiness-json", default="reports/testnet_reset_readiness/testnet_reset_readiness.json")
    parser.add_argument("--next-day-plan-summary-json", default="reports/next_trading_day_strategy_plan/summary.json")
    parser.add_argument("--output-dir", default="reports/daily_operator_checklist")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = generate_daily_operator_checklist(
        system_health_json=str(args.system_health_json or "reports/system_health/trading_system_health_dashboard.json"),
        gate_dashboard_json=str(args.gate_dashboard_json or "reports/gate_dashboard/gate_decision_dashboard.json"),
        runner_dry_run_report_json=str(args.runner_dry_run_report_json or "reports/runner_dry_run/runner_dry_run_report.json"),
        testnet_reset_readiness_json=str(args.testnet_reset_readiness_json or "reports/testnet_reset_readiness/testnet_reset_readiness.json"),
        next_day_plan_summary_json=str(args.next_day_plan_summary_json or "reports/next_trading_day_strategy_plan/summary.json"),
        output_dir=str(args.output_dir or "reports/daily_operator_checklist"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"final_verdict={result.get('final_verdict', 'UNKNOWN')}")
    print(f"operator_checklist_md={result.get('output_paths', {}).get('operator_checklist_md', '')}")


if __name__ == "__main__":
    main()
