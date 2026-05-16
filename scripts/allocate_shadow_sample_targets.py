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


def allocate_shadow_sample_targets(
    *,
    convergence_summary_json: str = "reports/remediation_gap_convergence/summary.json",
    progress_gap_summary_json: str = "reports/shadow_experiment_progress_gap/summary.json",
    next_run_plan_csv: str = "reports/next_shadow_experiment_run_plan/next_shadow_experiment_run_plan.csv",
    daily_control_json: str = "reports/daily_shadow_research_control/daily_shadow_research_control_report.json",
    output_dir: str = "reports/shadow_sample_targets",
) -> dict[str, Any]:
    convergence = _read_json(Path(convergence_summary_json))
    progress_gap = _read_json(Path(progress_gap_summary_json))
    next_run_rows = _read_csv_rows(Path(next_run_plan_csv))
    daily_control = _read_json(Path(daily_control_json))

    current_gap = int(convergence.get("current_sample_gap", 0) or 0)
    if current_gap == 0:
        current_gap = int(progress_gap.get("sample_gap_total", 0) or 0)

    gap_trend_slope = float(convergence.get("gap_trend_slope", 0.0) or 0.0)
    convergence_detected = bool(convergence.get("convergence_detected", False))
    stagnation_detected = bool(convergence.get("stagnation_detected", False))
    divergence_detected = bool(convergence.get("divergence_detected", False))

    total_experiments = int(daily_control.get("total_experiments", 0) or 0)
    next_run_candidate_count = int(daily_control.get("next_run_candidate_count", 0) or 0)

    # Allocation logic based on convergence state
    base_allocation = max(10, next_run_candidate_count)

    if convergence_detected:
        # Reduce allocation as we converge
        multiplier = 0.7
        allocation = int(base_allocation * multiplier)
        allocation_strategy = "CONVERGENCE_REDUCTION"
    elif stagnation_detected:
        # Increase allocation to break stagnation
        multiplier = 1.5
        allocation = int(base_allocation * multiplier)
        allocation_strategy = "STAGNATION_BREAKER"
    elif divergence_detected:
        # Aggressive allocation to reverse divergence
        multiplier = 2.0
        allocation = int(base_allocation * multiplier)
        allocation_strategy = "DIVERGENCE_REVERSAL"
    elif gap_trend_slope > 0:
        # Early divergence warning
        multiplier = 1.3
        allocation = int(base_allocation * multiplier)
        allocation_strategy = "EARLY_DIV_PREVENTION"
    else:
        # Standard allocation
        multiplier = 1.0
        allocation = base_allocation
        allocation_strategy = "STANDARD"

    allocation = max(5, min(allocation, 50))

    # Distribute across experiments
    target_allocations: list[dict[str, Any]] = []
    if next_run_rows:
        for row in next_run_rows:
            experiment_key = str(row.get("experiment_key", "")).strip() or f"exp_{len(target_allocations)}"
            target_allocations.append(
                {
                    "experiment_key": experiment_key,
                    "symbol": str(row.get("symbol", "")).strip() or "BTCUSDT",
                    "side": str(row.get("side", "")).strip() or "LONG",
                    "target_samples": max(1, allocation // max(1, len(next_run_rows))),
                    "allocation_strategy": allocation_strategy,
                    "priority": str(row.get("priority", "P2")).strip() or "P2",
                }
            )
    else:
        # Default allocation if no experiments
        target_allocations.append(
            {
                "experiment_key": "default_exp",
                "symbol": "BTCUSDT",
                "side": "LONG",
                "target_samples": allocation,
                "allocation_strategy": allocation_strategy,
                "priority": "P2",
            }
        )

    # Cap per-experiment targets
    max_per_experiment = min(allocation, 20)
    for item in target_allocations:
        item["target_samples"] = min(int(item["target_samples"]), max_per_experiment)

    final_verdict = "PASS" if target_allocations else "PARTIAL"

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_json = out_dir / "summary.json"
    allocation_csv = out_dir / "target_allocation.csv"
    summary_md = out_dir / "summary.md"

    # Write allocation CSV
    with allocation_csv.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = ["experiment_key", "symbol", "side", "target_samples", "allocation_strategy", "priority"]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for item in target_allocations:
            writer.writerow({k: item.get(k, "") for k in fieldnames})

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "final_verdict": final_verdict,
        "current_sample_gap": current_gap,
        "gap_trend_slope": round(gap_trend_slope, 6),
        "convergence_detected": convergence_detected,
        "stagnation_detected": stagnation_detected,
        "divergence_detected": divergence_detected,
        "allocation_strategy": allocation_strategy,
        "base_allocation": base_allocation,
        "multiplier": round(multiplier, 3),
        "final_allocation": allocation,
        "total_experiments": total_experiments,
        "next_run_candidate_count": next_run_candidate_count,
        "experiments_allocated": len(target_allocations),
        "total_target_samples": sum(int(item.get("target_samples", 0)) for item in target_allocations),
        "allowed_mode": "SHADOW_ONLY",
        "submit_allowed": False,
        "testnet_submit_allowed": False,
        "real_submit_allowed": False,
        "submit_attempted": False,
        "cancel_attempted": False,
        "flatten_attempted": False,
    }

    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    summary_lines = [
        "# Shadow Sample Target Allocation",
        "",
        f"- final_verdict: {summary['final_verdict']}",
        f"- current_sample_gap: {summary['current_sample_gap']}",
        f"- gap_trend_slope: {summary['gap_trend_slope']}",
        f"- convergence_detected: {summary['convergence_detected']}",
        f"- stagnation_detected: {summary['stagnation_detected']}",
        f"- divergence_detected: {summary['divergence_detected']}",
        f"- allocation_strategy: {summary['allocation_strategy']}",
        f"- final_allocation: {summary['final_allocation']}",
        f"- total_experiments: {summary['total_experiments']}",
        f"- experiments_allocated: {summary['experiments_allocated']}",
        f"- total_target_samples: {summary['total_target_samples']}",
        "- allowed_mode: SHADOW_ONLY",
        "- testnet_submit_allowed: false",
        "- real_submit_allowed: false",
        "- submit_attempted: false",
        "- cancel_attempted: false",
        "- flatten_attempted: false",
    ]
    summary_md.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    return summary


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Auto-allocate shadow sample targets based on convergence")
    parser.add_argument("--convergence-summary-json", default="reports/remediation_gap_convergence/summary.json")
    parser.add_argument("--progress-gap-summary-json", default="reports/shadow_experiment_progress_gap/summary.json")
    parser.add_argument("--next-run-plan-csv", default="reports/next_shadow_experiment_run_plan/next_shadow_experiment_run_plan.csv")
    parser.add_argument("--daily-control-json", default="reports/daily_shadow_research_control/daily_shadow_research_control_report.json")
    parser.add_argument("--output-dir", default="reports/shadow_sample_targets")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = allocate_shadow_sample_targets(
        convergence_summary_json=str(args.convergence_summary_json or "reports/remediation_gap_convergence/summary.json"),
        progress_gap_summary_json=str(args.progress_gap_summary_json or "reports/shadow_experiment_progress_gap/summary.json"),
        next_run_plan_csv=str(args.next_run_plan_csv or "reports/next_shadow_experiment_run_plan/next_shadow_experiment_run_plan.csv"),
        daily_control_json=str(args.daily_control_json or "reports/daily_shadow_research_control/daily_shadow_research_control_report.json"),
        output_dir=str(args.output_dir or "reports/shadow_sample_targets"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"final_verdict={result.get('final_verdict', '')}")
    print(f"allocation_strategy={result.get('allocation_strategy', '')}")
    print(f"final_allocation={result.get('final_allocation', 0)}")


if __name__ == "__main__":
    main()
