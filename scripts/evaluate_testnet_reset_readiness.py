from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.strategy_edge_common import read_csv_rows, read_json_file


def evaluate_testnet_reset_readiness(
    *,
    system_health_json: str = "reports/system_health/trading_system_health_dashboard.json",
    gate_dashboard_json: str = "reports/gate_dashboard/gate_decision_dashboard.json",
    runner_dry_run_report_json: str = "reports/runner_dry_run/runner_dry_run_report.json",
    strategy_candidate_csv: str = "reports/strategy_candidate_score/strategy_candidate_score.csv",
    symbol_side_csv: str = "reports/symbol_side_recommendations/symbol_side_recommendations.csv",
    strategy_promotion_csv: str = "reports/strategy_promotion/strategy_promotion_decisions.csv",
    output_dir: str = "reports/testnet_reset_readiness",
) -> dict[str, Any]:
    system_health = read_json_file(Path(system_health_json))
    gate_dashboard = read_json_file(Path(gate_dashboard_json))
    runner_report = read_json_file(Path(runner_dry_run_report_json))
    strategy_rows = read_csv_rows(Path(strategy_candidate_csv))
    symbol_side_rows = read_csv_rows(Path(symbol_side_csv))
    promotion_rows = read_csv_rows(Path(strategy_promotion_csv))

    system_health_pass = str(system_health.get("final_verdict", "UNKNOWN")).strip().upper() == "PASS"
    orphan_status = str(dict(system_health.get("account_state", {})).get("orphan_status", "UNKNOWN")).strip().upper()
    no_unclean_orphan = orphan_status in {"CLEAN", "FLAT_CLEAN"}
    gate_by_decision = dict(gate_dashboard.get("by_decision", {})) if isinstance(gate_dashboard.get("by_decision", {}), dict) else {}
    no_critical_gate_blocks = int(gate_by_decision.get("BLOCK_SYSTEM_HEALTH", 0) or 0) == 0
    has_approved_candidate = int(runner_report.get("approved_candidate_count", 0) or 0) > 0
    sample_levels = [str(row.get("sample_confidence_level", "")).strip().upper() for row in strategy_rows]
    sample_confidence_not_too_small = bool(sample_levels) and all(level not in {"", "UNKNOWN", "TOO_SMALL"} for level in sample_levels)
    symbol_side_not_rejected = not any(
        str(row.get("recommendation", "")).strip().upper() in {"REJECT", "BLACKLIST", "PAUSE"}
        for row in symbol_side_rows
    )
    promotion_not_rejected = not any(
        str(row.get("promotion_decision", "")).strip().upper() in {"REJECT_STRATEGY", "PAUSE_STRATEGY"}
        for row in promotion_rows
    )
    runner_dry_run_safe = str(runner_report.get("safety_verdict", "UNKNOWN")).strip().upper() == "PASS"

    minimum_conditions = {
        "system_health_pass": bool(system_health_pass),
        "no_unclean_orphan": bool(no_unclean_orphan),
        "no_critical_gate_blocks": bool(no_critical_gate_blocks),
        "has_approved_candidate": bool(has_approved_candidate),
        "sample_confidence_not_too_small": bool(sample_confidence_not_too_small),
        "symbol_side_not_rejected": bool(symbol_side_not_rejected),
        "promotion_not_rejected": bool(promotion_not_rejected),
        "runner_dry_run_safe": bool(runner_dry_run_safe),
    }

    blocking_reasons: list[str] = []
    if not minimum_conditions["system_health_pass"]:
        blocking_reasons.append("system_health_not_pass")
    if not minimum_conditions["no_unclean_orphan"]:
        blocking_reasons.append("orphan_not_clean")
    if not minimum_conditions["no_critical_gate_blocks"]:
        blocking_reasons.append("critical_gate_blocks_present")
    if not minimum_conditions["has_approved_candidate"]:
        blocking_reasons.append("no_approved_candidate")
    if not minimum_conditions["sample_confidence_not_too_small"]:
        blocking_reasons.append("sample_confidence_too_small")
    if not minimum_conditions["symbol_side_not_rejected"]:
        blocking_reasons.append("symbol_side_rejected")
    if not minimum_conditions["promotion_not_rejected"]:
        blocking_reasons.append("strategy_promotion_rejected")
    if not minimum_conditions["runner_dry_run_safe"]:
        blocking_reasons.append("runner_dry_run_not_safe")

    can_submit_after_reset = all(minimum_conditions.values())
    readiness_verdict = "READY" if can_submit_after_reset else "NOT_READY"
    allowed_actions_after_reset = (
        ["TESTNET_SUBMIT_ALLOWED_AFTER_RESET", "TESTNET_DRY_RUN_ONLY"]
        if can_submit_after_reset
        else ["OBSERVE_ONLY", "TESTNET_DRY_RUN_ONLY"]
    )

    output = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "readiness_verdict": readiness_verdict,
        "can_submit_after_reset": bool(can_submit_after_reset),
        "minimum_conditions": minimum_conditions,
        "blocking_reasons": blocking_reasons,
        "allowed_actions_after_reset": allowed_actions_after_reset,
        "source_paths": {
            "system_health_json": system_health_json,
            "gate_dashboard_json": gate_dashboard_json,
            "runner_dry_run_report_json": runner_dry_run_report_json,
            "strategy_candidate_csv": strategy_candidate_csv,
            "symbol_side_csv": symbol_side_csv,
            "strategy_promotion_csv": strategy_promotion_csv,
        },
    }

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_json = out_dir / "testnet_reset_readiness.json"
    summary_md = out_dir / "summary.md"
    out_json.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Testnet Reset Readiness",
        "",
        f"- readiness_verdict: {readiness_verdict}",
        f"- can_submit_after_reset: {can_submit_after_reset}",
        f"- blocking_reasons: {', '.join(blocking_reasons) if blocking_reasons else 'none'}",
        "",
        "## Allowed Actions After Reset",
    ]
    for item in allowed_actions_after_reset:
        lines.append(f"- {item}")
    summary_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    output["output_paths"] = {
        "testnet_reset_readiness_json": str(out_json),
        "summary_md": str(summary_md),
    }
    return output


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate minimal safety conditions after testnet submit reset")
    parser.add_argument("--system-health-json", default="reports/system_health/trading_system_health_dashboard.json")
    parser.add_argument("--gate-dashboard-json", default="reports/gate_dashboard/gate_decision_dashboard.json")
    parser.add_argument("--runner-dry-run-report-json", default="reports/runner_dry_run/runner_dry_run_report.json")
    parser.add_argument("--strategy-candidate-csv", default="reports/strategy_candidate_score/strategy_candidate_score.csv")
    parser.add_argument("--symbol-side-csv", default="reports/symbol_side_recommendations/symbol_side_recommendations.csv")
    parser.add_argument("--strategy-promotion-csv", default="reports/strategy_promotion/strategy_promotion_decisions.csv")
    parser.add_argument("--output-dir", default="reports/testnet_reset_readiness")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = evaluate_testnet_reset_readiness(
        system_health_json=str(args.system_health_json or "reports/system_health/trading_system_health_dashboard.json"),
        gate_dashboard_json=str(args.gate_dashboard_json or "reports/gate_dashboard/gate_decision_dashboard.json"),
        runner_dry_run_report_json=str(args.runner_dry_run_report_json or "reports/runner_dry_run/runner_dry_run_report.json"),
        strategy_candidate_csv=str(args.strategy_candidate_csv or "reports/strategy_candidate_score/strategy_candidate_score.csv"),
        symbol_side_csv=str(args.symbol_side_csv or "reports/symbol_side_recommendations/symbol_side_recommendations.csv"),
        strategy_promotion_csv=str(args.strategy_promotion_csv or "reports/strategy_promotion/strategy_promotion_decisions.csv"),
        output_dir=str(args.output_dir or "reports/testnet_reset_readiness"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"readiness_verdict={result.get('readiness_verdict', 'UNKNOWN')}")
    print(f"can_submit_after_reset={result.get('can_submit_after_reset', False)}")
    print(f"output_json={result.get('output_paths', {}).get('testnet_reset_readiness_json', '')}")


if __name__ == "__main__":
    main()
