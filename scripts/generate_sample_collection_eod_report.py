from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.execution_guards import (
    ExecutionGuardError,
    assert_dry_run_required,
    normalize_execution_mode,
)
from scripts.strategy_edge_common import read_csv_rows


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def generate_sample_collection_eod_report(
    *,
    sample_tracker_csv: str = "reports/sample_collection_tracker/sample_collection_tracker.csv",
    shadow_collection_summary_json: str = "reports/shadow_candidate_collection/summary.json",
    collect_plan_summary_json: str = "reports/collect_more_samples_plan/summary.json",
    shadow_scan_plan_csv: str = "reports/shadow_scan_plan/shadow_scan_plan.csv",
    gate_dashboard_json: str = "reports/gate_dashboard/gate_decision_dashboard.json",
    output_dir: str = "reports/sample_collection_eod",
) -> dict[str, Any]:
    tracker_rows = read_csv_rows(Path(sample_tracker_csv))
    shadow_summary = _load_json(Path(shadow_collection_summary_json))
    collect_summary = _load_json(Path(collect_plan_summary_json))
    scan_rows = read_csv_rows(Path(shadow_scan_plan_csv))
    gate_dashboard = _load_json(Path(gate_dashboard_json))

    collecting_count = sum(1 for row in tracker_rows if str(row.get("collection_status", "")).strip().upper() == "COLLECTING")
    low_confidence_count = sum(1 for row in tracker_rows if str(row.get("collection_status", "")).strip().upper() == "LOW_CONFIDENCE")
    medium_ready_count = sum(1 for row in tracker_rows if str(row.get("collection_status", "")).strip().upper() == "MEDIUM_READY")
    high_confidence_count = sum(1 for row in tracker_rows if str(row.get("collection_status", "")).strip().upper() == "HIGH_CONFIDENCE")

    sorted_tracker = sorted(
        tracker_rows,
        key=lambda row: (
            str(row.get("collection_priority", "P9")).strip().upper(),
            -int(float(str(row.get("samples_needed_for_medium", "0") or "0"))),
            str(row.get("strategy_key", "")),
        ),
    )
    top_priority_collections: list[dict[str, Any]] = []
    tomorrow_focus: list[str] = []
    for row in sorted_tracker[:5]:
        strategy_key = str(row.get("strategy_key", "")).strip()
        needed_medium = int(float(str(row.get("samples_needed_for_medium", "0") or "0")))
        next_action = str(row.get("next_action", "collect_more_shadow_samples")).strip()
        top_priority_collections.append(
            {
                "strategy_key": strategy_key,
                "samples_needed_for_medium": needed_medium,
                "next_action": next_action,
            }
        )
        if strategy_key:
            tomorrow_focus.append(f"Continue SHADOW_ONLY collection for {strategy_key}.")

    if not tomorrow_focus and scan_rows:
        for row in scan_rows[:3]:
            strategy_key = str(row.get("strategy_key", "")).strip()
            if strategy_key:
                tomorrow_focus.append(f"Continue SHADOW_ONLY collection for {strategy_key}.")
    if not tomorrow_focus:
        tomorrow_focus.append("Continue SHADOW_ONLY collection for watchlist strategies.")

    today_shadow_candidates_collected = int(shadow_summary.get("collected_count", 0) or 0)
    active_strategy_keys = len({str(row.get("strategy_key", "")).strip() for row in tracker_rows if str(row.get("strategy_key", "")).strip()})
    final_verdict = "PASS"
    if not tracker_rows:
        final_verdict = "PARTIAL"
    if str(gate_dashboard.get("final_verdict", "PASS")).strip().upper() == "FAIL":
        final_verdict = "PARTIAL"

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "final_verdict": final_verdict,
        "today_shadow_candidates_collected": today_shadow_candidates_collected,
        "active_strategy_keys": active_strategy_keys,
        "collecting_count": collecting_count,
        "low_confidence_count": low_confidence_count,
        "medium_ready_count": medium_ready_count,
        "high_confidence_count": high_confidence_count,
        "top_priority_collections": top_priority_collections,
        "tomorrow_focus": tomorrow_focus,
        "context": {
            "collect_plan_total_rows": int(collect_summary.get("total_rows", 0) or 0),
            "shadow_scan_rows": len(scan_rows),
            "gate_dashboard_verdict": str(gate_dashboard.get("final_verdict", "UNKNOWN")),
        },
    }

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    report_json = out_dir / "sample_collection_eod_report.json"
    summary_md = out_dir / "summary.md"
    report["output_paths"] = {
        "sample_collection_eod_report_json": str(report_json),
        "summary_md": str(summary_md),
    }
    report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Sample Collection EOD Report",
        "",
        f"- final_verdict: {report['final_verdict']}",
        f"- today_shadow_candidates_collected: {report['today_shadow_candidates_collected']}",
        f"- active_strategy_keys: {report['active_strategy_keys']}",
        f"- collecting_count: {report['collecting_count']}",
        f"- low_confidence_count: {report['low_confidence_count']}",
        f"- medium_ready_count: {report['medium_ready_count']}",
        f"- high_confidence_count: {report['high_confidence_count']}",
        "",
        "## Tomorrow Focus",
    ]
    for item in tomorrow_focus:
        lines.append(f"- {item}")
    summary_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate end-of-day sample collection report")
    parser.add_argument("--sample-tracker-csv", default="reports/sample_collection_tracker/sample_collection_tracker.csv")
    parser.add_argument("--shadow-collection-summary-json", default="reports/shadow_candidate_collection/summary.json")
    parser.add_argument("--collect-plan-summary-json", default="reports/collect_more_samples_plan/summary.json")
    parser.add_argument("--shadow-scan-plan-csv", default="reports/shadow_scan_plan/shadow_scan_plan.csv")
    parser.add_argument("--gate-dashboard-json", default="reports/gate_dashboard/gate_decision_dashboard.json")
    parser.add_argument("--output-dir", default="reports/sample_collection_eod")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    mode = normalize_execution_mode(os.environ.get("QQ_RUNTIME_MODE"))
    assert_dry_run_required(mode)
    result = generate_sample_collection_eod_report(
        sample_tracker_csv=str(args.sample_tracker_csv or "reports/sample_collection_tracker/sample_collection_tracker.csv"),
        shadow_collection_summary_json=str(args.shadow_collection_summary_json or "reports/shadow_candidate_collection/summary.json"),
        collect_plan_summary_json=str(args.collect_plan_summary_json or "reports/collect_more_samples_plan/summary.json"),
        shadow_scan_plan_csv=str(args.shadow_scan_plan_csv or "reports/shadow_scan_plan/shadow_scan_plan.csv"),
        gate_dashboard_json=str(args.gate_dashboard_json or "reports/gate_dashboard/gate_decision_dashboard.json"),
        output_dir=str(args.output_dir or "reports/sample_collection_eod"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"final_verdict={result.get('final_verdict', 'UNKNOWN')}")
    print(f"today_shadow_candidates_collected={result.get('today_shadow_candidates_collected', 0)}")


if __name__ == "__main__":
    main()
