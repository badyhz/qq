from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.strategy_edge_common import read_csv_rows, to_float_nan


FIELDS = [
    "remediation_id",
    "requirement_key",
    "priority",
    "action_type",
    "action_name",
    "recommended_command",
    "target_metric",
    "current_value",
    "target_value",
    "estimated_runs_needed",
    "allowed_mode",
    "submit_permission",
    "risk_level",
    "status",
    "reason",
]


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _to_float(value: Any, default: float = float("nan")) -> float:
    parsed = to_float_nan(value)
    if not math.isfinite(parsed):
        return float(default)
    return float(parsed)


def _to_int(value: Any, default: int = 0) -> int:
    parsed = _to_float(value, float(default))
    if not math.isfinite(parsed):
        return int(default)
    return int(parsed)


def _action_for_requirement(requirement_key: str) -> tuple[str, str, str]:
    mapping = {
        "experiment_total_samples": (
            "COLLECT_MORE_SHADOW_SAMPLES",
            "Collect More Shadow Experiment Samples",
            "PYTHONPATH=. ./.venv/bin/python scripts/run_next_shadow_experiment_plan.py --plan-csv reports/next_shadow_experiment_run_plan_v2/next_shadow_experiment_run_plan_v2.csv --json",
        ),
        "shadow_research_history_days": (
            "BUILD_HISTORY_DAYS",
            "Build Shadow Research History Days",
            "PYTHONPATH=. ./.venv/bin/python scripts/update_shadow_research_history.py --json",
        ),
        "stability_ready_count": (
            "RECOMPUTE_STABILITY",
            "Recompute Stability After More Samples",
            "PYTHONPATH=. ./.venv/bin/python scripts/calculate_shadow_experiment_stability_score.py --json",
        ),
        "strategy_weighted_sample_count": (
            "RUN_SHADOW_ONLY_LOOP",
            "Run Shadow-Only Loop For Weighted Sample Growth",
            "PYTHONPATH=. ./.venv/bin/python scripts/run_next_shadow_experiment_plan.py --plan-csv reports/next_shadow_experiment_run_plan_v2/next_shadow_experiment_run_plan_v2.csv --json",
        ),
        "system_health_pass": (
            "KEEP_SYSTEM_HEALTH_PASS",
            "Keep System Health PASS",
            "PYTHONPATH=. ./.venv/bin/python scripts/generate_trading_system_health_dashboard.py --json",
        ),
        "no_trade_actions_attempted": (
            "RUN_SHADOW_ONLY_LOOP",
            "Run Shadow-Only Loop With Trade Actions Disabled",
            "PYTHONPATH=. ./.venv/bin/python scripts/generate_shadow_only_loop_plan.py --json",
        ),
        "testnet_dry_run_readiness_not_fail": (
            "RECOMPUTE_PHASE_REVIEW",
            "Recompute Testnet Dry-Run Phase Review",
            "PYTHONPATH=. ./.venv/bin/python scripts/generate_testnet_dry_run_phase_review.py --json",
        ),
    }
    return mapping.get(
        requirement_key,
        (
            "UNKNOWN",
            "Unknown Remediation Action",
            "PYTHONPATH=. ./.venv/bin/python scripts/generate_testnet_dry_run_phase_review.py --json",
        ),
    )


def generate_testnet_dry_run_remediation_plan(
    *,
    readiness_gaps_csv: str = "reports/testnet_dry_run_readiness_gaps/readiness_gaps.csv",
    phase_review_json: str = "reports/testnet_dry_run_phase_review/testnet_dry_run_phase_review.json",
    tuning_suggestions_csv: str = "reports/shadow_experiment_tuning/tuning_suggestions.csv",
    next_run_plan_v2_csv: str = "reports/next_shadow_experiment_run_plan_v2/next_shadow_experiment_run_plan_v2.csv",
    shadow_only_loop_plan_json: str = "reports/shadow_only_loop_plan/shadow_only_loop_plan.json",
    output_dir: str = "reports/testnet_dry_run_remediation",
) -> dict[str, Any]:
    gap_rows = read_csv_rows(Path(readiness_gaps_csv))
    phase = _read_json(Path(phase_review_json))
    tuning_rows = read_csv_rows(Path(tuning_suggestions_csv))
    plan_rows = read_csv_rows(Path(next_run_plan_v2_csv))
    _ = _read_json(Path(shadow_only_loop_plan_json))

    total_target_per_run = sum(max(0, _to_int(row.get("target_samples_this_run"), 0)) for row in plan_rows)
    if total_target_per_run <= 0:
        total_target_per_run = max(1, len(plan_rows))

    out_rows: list[dict[str, Any]] = []
    for idx, gap in enumerate(gap_rows, start=1):
        if not bool(str(gap.get("blocking", "")).strip().lower() in {"1", "true", "yes"}):
            continue
        requirement_key = str(gap.get("requirement_key", "")).strip()
        action_type, action_name, command = _action_for_requirement(requirement_key)
        current_value = gap.get("current_value", "")
        target_value = gap.get("required_value", "")
        gap_value = _to_float(gap.get("gap_value"), 0.0)
        gap_unit = str(gap.get("gap_unit", "")).strip()

        estimated_runs_needed = 1
        if gap_unit == "samples":
            estimated_runs_needed = max(1, int(math.ceil(max(0.0, gap_value) / max(1, total_target_per_run))))
        elif gap_unit == "days":
            estimated_runs_needed = max(1, int(math.ceil(max(0.0, gap_value))))
        elif gap_unit == "weighted_samples":
            estimated_runs_needed = max(1, int(math.ceil(max(0.0, gap_value) / 0.3)))
        elif gap_unit == "experiments":
            estimated_runs_needed = max(1, int(math.ceil(max(0.0, gap_value))))

        out_rows.append(
            {
                "remediation_id": f"remediation_{idx:03d}_{requirement_key}",
                "requirement_key": requirement_key,
                "priority": str(gap.get("priority", "P2")).strip().upper() or "P2",
                "action_type": action_type,
                "action_name": action_name,
                "recommended_command": command,
                "target_metric": requirement_key,
                "current_value": current_value,
                "target_value": target_value,
                "estimated_runs_needed": estimated_runs_needed,
                "allowed_mode": "SHADOW_ONLY",
                "submit_permission": "NO_SUBMIT",
                "risk_level": "LOW_CONFIDENCE",
                "status": "OPEN",
                "reason": str(gap.get("remediation_hint", "")).strip() or "need_more_shadow_research_data",
            }
        )

    if not out_rows and str(phase.get("final_verdict", "")).strip().upper() == "NOT_READY":
        out_rows.append(
            {
                "remediation_id": "remediation_000_phase_review",
                "requirement_key": "phase_review_not_ready",
                "priority": "P1",
                "action_type": "RECOMPUTE_PHASE_REVIEW",
                "action_name": "Recompute Phase Review",
                "recommended_command": "PYTHONPATH=. ./.venv/bin/python scripts/generate_testnet_dry_run_phase_review.py --json",
                "target_metric": "phase_review_final_verdict",
                "current_value": "NOT_READY",
                "target_value": "READY_FOR_TESTNET_DRY_RUN_ONLY",
                "estimated_runs_needed": 1,
                "allowed_mode": "SHADOW_ONLY",
                "submit_permission": "NO_SUBMIT",
                "risk_level": "LOW_CONFIDENCE",
                "status": "OPEN",
                "reason": "phase_review_not_ready",
            }
        )

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "remediation_plan.csv"
    summary_json = out_dir / "summary.json"
    summary_md = out_dir / "summary.md"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for row in out_rows:
            writer.writerow({field: row.get(field, "") for field in FIELDS})

    estimated_runs_total = sum(max(0, _to_int(row.get("estimated_runs_needed"), 0)) for row in out_rows)
    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "final_verdict": "PASS" if out_rows else "PARTIAL",
        "remediation_action_count": len(out_rows),
        "estimated_runs_needed": estimated_runs_total,
        "recommended_next_action": "RUN_REMEDIATION_SHADOW_ONLY_LOOP",
        "allow_testnet_submit": False,
        "allow_real_submit": False,
        "submit_attempted": False,
        "cancel_attempted": False,
        "flatten_attempted": False,
        "csv_path": str(csv_path),
        "summary_json": str(summary_json),
        "summary_md": str(summary_md),
        "input_counts": {
            "gap_rows": len(gap_rows),
            "tuning_rows": len(tuning_rows),
            "plan_rows": len(plan_rows),
        },
    }
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Testnet Dry-Run Remediation Plan",
        "",
        f"- final_verdict: {summary['final_verdict']}",
        f"- remediation_action_count: {summary['remediation_action_count']}",
        f"- estimated_runs_needed: {summary['estimated_runs_needed']}",
        f"- recommended_next_action: {summary['recommended_next_action']}",
        "- allow_testnet_submit: false",
        "- allow_real_submit: false",
        "- submit_attempted: false",
        "- cancel_attempted: false",
        "- flatten_attempted: false",
    ]
    summary_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate remediation plan from NOT_READY dry-run phase review gaps")
    parser.add_argument("--readiness-gaps-csv", default="reports/testnet_dry_run_readiness_gaps/readiness_gaps.csv")
    parser.add_argument("--phase-review-json", default="reports/testnet_dry_run_phase_review/testnet_dry_run_phase_review.json")
    parser.add_argument("--tuning-suggestions-csv", default="reports/shadow_experiment_tuning/tuning_suggestions.csv")
    parser.add_argument("--next-run-plan-v2-csv", default="reports/next_shadow_experiment_run_plan_v2/next_shadow_experiment_run_plan_v2.csv")
    parser.add_argument("--shadow-only-loop-plan-json", default="reports/shadow_only_loop_plan/shadow_only_loop_plan.json")
    parser.add_argument("--output-dir", default="reports/testnet_dry_run_remediation")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = generate_testnet_dry_run_remediation_plan(
        readiness_gaps_csv=str(args.readiness_gaps_csv or "reports/testnet_dry_run_readiness_gaps/readiness_gaps.csv"),
        phase_review_json=str(args.phase_review_json or "reports/testnet_dry_run_phase_review/testnet_dry_run_phase_review.json"),
        tuning_suggestions_csv=str(args.tuning_suggestions_csv or "reports/shadow_experiment_tuning/tuning_suggestions.csv"),
        next_run_plan_v2_csv=str(
            args.next_run_plan_v2_csv or "reports/next_shadow_experiment_run_plan_v2/next_shadow_experiment_run_plan_v2.csv"
        ),
        shadow_only_loop_plan_json=str(
            args.shadow_only_loop_plan_json or "reports/shadow_only_loop_plan/shadow_only_loop_plan.json"
        ),
        output_dir=str(args.output_dir or "reports/testnet_dry_run_remediation"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"final_verdict={result.get('final_verdict', '')}")
    print(f"remediation_action_count={result.get('remediation_action_count', 0)}")


if __name__ == "__main__":
    main()
