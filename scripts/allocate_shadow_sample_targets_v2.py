from __future__ import annotations

import argparse
import csv
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


def _read_csv_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            return [row for row in reader if row]
    except (OSError, csv.Error):
        return []


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _collect_missing_inputs(
    *,
    convergence_v2_summary_json: str,
    previous_targets_summary_json: str,
    shadow_outcomes_summary_json: str,
    next_run_plan_csv: str,
) -> list[str]:
    missing: list[str] = []
    for label, p in [
        ("convergence_v2_summary_json", Path(convergence_v2_summary_json)),
        ("previous_targets_summary_json", Path(previous_targets_summary_json)),
        ("shadow_outcomes_summary_json", Path(shadow_outcomes_summary_json)),
        ("next_run_plan_csv", Path(next_run_plan_csv)),
    ]:
        if not p.exists():
            missing.append(label)
    return missing


def allocate_shadow_sample_targets_v2(
    *,
    convergence_v2_summary_json: str = "reports/remediation_gap_convergence_v2/summary.json",
    previous_targets_summary_json: str = "reports/shadow_sample_targets/summary.json",
    shadow_outcomes_summary_json: str = "reports/shadow_candidate_outcomes/summary.json",
    next_run_plan_csv: str = "reports/next_shadow_experiment_run_plan/next_shadow_experiment_run_plan.csv",
    output_dir: str = "reports/shadow_sample_targets_v2",
) -> dict[str, Any]:
    missing_inputs = _collect_missing_inputs(
        convergence_v2_summary_json=convergence_v2_summary_json,
        previous_targets_summary_json=previous_targets_summary_json,
        shadow_outcomes_summary_json=shadow_outcomes_summary_json,
        next_run_plan_csv=next_run_plan_csv,
    )

    # Safety flags
    allowed_mode = "SHADOW_ONLY"
    submit_permission = "NO_SUBMIT"
    testnet_submit_allowed = False
    real_submit_allowed = False
    submit_attempted = False
    cancel_attempted = False
    flatten_attempted = False

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Read convergence v2
    conv_v2 = _read_json(Path(convergence_v2_summary_json))
    gap_latest = _to_int(conv_v2.get("gap_latest", 0))
    gap_trend = str(conv_v2.get("gap_trend", "UNKNOWN")).strip() or "UNKNOWN"
    convergence_confidence = str(conv_v2.get("convergence_confidence", "LOW")).strip() or "LOW"

    # Read previous allocator
    prev_targets = _read_json(Path(previous_targets_summary_json))
    prev_strategy = str(prev_targets.get("allocation_strategy", "STANDARD")).strip() or "STANDARD"

    # Read shadow outcomes
    shadow_out = _read_json(Path(shadow_outcomes_summary_json))
    total_shadow_samples = _to_int(shadow_out.get("shadow_sample_count", 0))
    weighted_samples = _to_float(shadow_out.get("weighted_sample_count", 0.0))

    # Read next-run plan
    next_run_rows = _read_csv_rows(Path(next_run_plan_csv))

    # Determine allocation strategy
    allocation_strategy = "GAP_WEIGHTED"

    if missing_inputs and not next_run_rows:
        allocation_strategy = "FALLBACK"
    elif gap_latest == 0:
        allocation_strategy = "EVEN"
    elif gap_trend == "WORSENING":
        allocation_strategy = "GAP_WEIGHTED"
    elif gap_trend == "IMPROVING":
        allocation_strategy = "GAP_WEIGHTED"
    elif gap_trend in ("FLAT", "UNKNOWN"):
        allocation_strategy = "EVEN"

    # Build allocations
    allocations: list[dict[str, Any]] = []

    total_allocated = 0
    base_per_symbol = max(5, min(20, max(1, gap_latest // max(1, len(next_run_rows) if next_run_rows else 1))))

    if next_run_rows:
        for row in next_run_rows:
            symbol = str(row.get("symbol", "")).strip() or "BTCUSDT"
            timeframe = str(row.get("timeframe", "")).strip() or str(row.get("interval", "")).strip() or "1h"
            setup = str(row.get("setup", "")).strip() or str(row.get("side", "")).strip() or "LONG"
            experiment_key = str(row.get("experiment_key", "")).strip() or f"{symbol}_{timeframe}_{setup}"

            current_samples = _to_int(row.get("current_samples", 0))
            if current_samples <= 0:
                current_samples = _to_int(row.get("target_samples", 0))

            target_samples_next = base_per_symbol

            # Priority based on gap and trend
            priority = "MEDIUM"
            if gap_trend == "WORSENING":
                priority = "HIGH"
            elif gap_trend == "IMPROVING" and convergence_confidence == "HIGH":
                priority = "LOW"

            allocations.append({
                "symbol": symbol,
                "timeframe": timeframe,
                "setup": setup,
                "experiment_key": experiment_key,
                "current_samples": current_samples,
                "target_samples_next_run": target_samples_next,
                "priority": priority,
                "reason": f"gap_{gap_trend}_conv_{convergence_confidence}",
            })
            total_allocated += target_samples_next

        if total_allocated == 0:
            total_allocated = base_per_symbol * max(1, len(next_run_rows))
            for alloc in allocations:
                alloc["target_samples_next_run"] = base_per_symbol
    else:
        # Fallback: create default allocations
        fallback_symbols = [
            ("BTCUSDT", "1h", "LONG"),
            ("BTCUSDT", "1h", "SHORT"),
            ("ETHUSDT", "1h", "LONG"),
        ]
        for sym, tf, setup in fallback_symbols:
            allocations.append({
                "symbol": sym,
                "timeframe": tf,
                "setup": setup,
                "experiment_key": f"{sym}_{tf}_{setup}",
                "current_samples": 0,
                "target_samples_next_run": max(5, gap_latest // 3),
                "priority": "MEDIUM",
                "reason": "fallback_default",
            })
            total_allocated += max(5, gap_latest // 3)

        total_allocated = max(0, total_allocated)
        allocation_strategy = "FALLBACK"

    unallocated_gap = max(0, gap_latest - total_allocated)

    # still_not_ready: if gap remains
    still_not_ready = gap_latest > 0 or unallocated_gap > 0

    # Final verdict
    final_verdict = "PASS"
    if missing_inputs and not allocations:
        final_verdict = "PARTIAL"
    elif missing_inputs:
        final_verdict = "PARTIAL"

    allocation_count = len(allocations)
    total_allocated_target_samples_next_run = sum(
        int(a.get("target_samples_next_run", 0)) for a in allocations
    )

    report: dict[str, Any] = {
        "task_id": "T368",
        "phase": "SHADOW_SAMPLE_TARGET_ALLOCATOR_V2",
        "allowed_mode": allowed_mode,
        "submit_permission": submit_permission,
        "testnet_submit_allowed": testnet_submit_allowed,
        "real_submit_allowed": real_submit_allowed,
        "submit_attempted": submit_attempted,
        "cancel_attempted": cancel_attempted,
        "flatten_attempted": flatten_attempted,
        "allocation_strategy": allocation_strategy,
        "total_allocated_target_samples_next_run": total_allocated_target_samples_next_run,
        "allocations": allocations,
        "allocation_count": allocation_count,
        "unallocated_gap": unallocated_gap,
        "gap_latest": gap_latest,
        "gap_trend": gap_trend,
        "convergence_confidence": convergence_confidence,
        "still_not_ready": still_not_ready,
        "final_verdict": final_verdict,
        "missing_inputs": missing_inputs,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }

    summary_json = out_dir / "summary.json"
    alloc_csv = out_dir / "target_allocation_v2.csv"
    summary_md = out_dir / "summary.md"

    summary_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    csv_fields = ["symbol", "timeframe", "setup", "experiment_key", "current_samples", "target_samples_next_run", "priority", "reason"]
    with alloc_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=csv_fields)
        writer.writeheader()
        for alloc in allocations:
            writer.writerow({k: alloc.get(k, "") for k in csv_fields})

    md_lines = [
        "# Shadow Sample Target Allocation V2",
        "",
        f"- task_id: {report['task_id']}",
        f"- final_verdict: {report['final_verdict']}",
        f"- allocation_strategy: {report['allocation_strategy']}",
        f"- total_allocated_target_samples_next_run: {report['total_allocated_target_samples_next_run']}",
        f"- unallocated_gap: {report['unallocated_gap']}",
        f"- gap_latest: {report['gap_latest']}",
        f"- gap_trend: {report['gap_trend']}",
        f"- convergence_confidence: {report['convergence_confidence']}",
        f"- allocation_count: {report['allocation_count']}",
        f"- still_not_ready: {report['still_not_ready']}",
        f"- missing_inputs: {report['missing_inputs']}",
        "- allowed_mode: SHADOW_ONLY",
        "- submit_permission: NO_SUBMIT",
        "- testnet_submit_allowed: false",
        "- real_submit_allowed: false",
        "- submit_attempted: false",
        "- cancel_attempted: false",
        "- flatten_attempted: false",
    ]
    summary_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    return report


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Auto-allocate shadow sample targets v2 based on round-2 convergence")
    parser.add_argument("--convergence-v2-summary-json", default="reports/remediation_gap_convergence_v2/summary.json")
    parser.add_argument("--previous-targets-summary-json", default="reports/shadow_sample_targets/summary.json")
    parser.add_argument("--shadow-outcomes-summary-json", default="reports/shadow_candidate_outcomes/summary.json")
    parser.add_argument("--next-run-plan-csv", default="reports/next_shadow_experiment_run_plan/next_shadow_experiment_run_plan.csv")
    parser.add_argument("--output-dir", default="reports/shadow_sample_targets_v2")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = allocate_shadow_sample_targets_v2(
        convergence_v2_summary_json=str(args.convergence_v2_summary_json or "reports/remediation_gap_convergence_v2/summary.json"),
        previous_targets_summary_json=str(args.previous_targets_summary_json or "reports/shadow_sample_targets/summary.json"),
        shadow_outcomes_summary_json=str(args.shadow_outcomes_summary_json or "reports/shadow_candidate_outcomes/summary.json"),
        next_run_plan_csv=str(args.next_run_plan_csv or "reports/next_shadow_experiment_run_plan/next_shadow_experiment_run_plan.csv"),
        output_dir=str(args.output_dir or "reports/shadow_sample_targets_v2"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"task_id={result.get('task_id','')}")
    print(f"final_verdict={result.get('final_verdict','')}")
    print(f"allocation_strategy={result.get('allocation_strategy','')}")
    print(f"total_allocated={result.get('total_allocated_target_samples_next_run',0)}")


if __name__ == "__main__":
    main()
