from __future__ import annotations

import argparse
import csv
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


def generate_shadow_experiment_eod_report(
    *,
    experiment_runs_summary_json: str = "reports/shadow_observation_experiment_runs/summary.json",
    experiment_outcomes_summary_json: str = "reports/shadow_experiment_outcomes/summary.json",
    experiment_comparison_summary_json: str = "reports/shadow_experiment_comparison/summary.json",
    experiment_promotion_summary_json: str = "reports/shadow_experiment_promotion/summary.json",
    experiment_promotion_decisions_csv: str = "reports/shadow_experiment_promotion/experiment_promotion_decisions.csv",
    observation_experiment_dashboard_json: str = "reports/observation_experiment_dashboard/observation_experiment_dashboard.json",
    output_dir: str = "reports/shadow_experiment_eod",
) -> dict[str, Any]:
    runs = _read_json(Path(experiment_runs_summary_json))
    outcomes = _read_json(Path(experiment_outcomes_summary_json))
    comparison = _read_json(Path(experiment_comparison_summary_json))
    promotion = _read_json(Path(experiment_promotion_summary_json))
    dashboard = _read_json(Path(observation_experiment_dashboard_json))
    decision_rows = read_csv_rows(Path(experiment_promotion_decisions_csv))

    experiment_count = int(runs.get("experiment_count", 0) or 0)
    candidate_count = int(runs.get("experiment_candidate_count", 0) or 0)
    evaluated_count = int(outcomes.get("evaluated_count", 0) or 0)
    keep_collecting_count = sum(
        1 for row in decision_rows if str(row.get("promotion_decision", "")).strip().upper() == "KEEP_COLLECTING"
    )
    promote_count = sum(
        1
        for row in decision_rows
        if str(row.get("promotion_decision", "")).strip().upper()
        in {"PROMOTE_TO_SHADOW_OBSERVATION", "PROMOTE_TO_STRICT_CANDIDATE_TEST"}
    )
    reject_count = sum(
        1 for row in decision_rows if str(row.get("promotion_decision", "")).strip().upper() == "REJECT_EXPERIMENT"
    )

    next_round_suggestions: list[str] = []
    if candidate_count <= 0:
        next_round_suggestions.append("Increase scan frequency and collect shadow experiment candidates.")
    if evaluated_count <= 0:
        next_round_suggestions.append("Ensure experiment candidates have enough bars for outcome evaluation.")
    if keep_collecting_count > 0:
        next_round_suggestions.append("Continue collecting observation samples before relaxing strict rules.")
    if not next_round_suggestions:
        next_round_suggestions.append("Continue SHADOW_ONLY experiment loop and monitor promotion thresholds.")

    final_verdict = "PASS"
    if experiment_count <= 0 or candidate_count <= 0 or evaluated_count <= 0:
        final_verdict = "PARTIAL"
    if str(comparison.get("final_verdict", "")).strip().upper() == "PARTIAL":
        final_verdict = "PARTIAL"
    if str(promotion.get("final_verdict", "")).strip().upper() == "PARTIAL":
        final_verdict = "PARTIAL"

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "final_verdict": final_verdict,
        "experiment_count": experiment_count,
        "experiment_candidate_count": candidate_count,
        "evaluated_experiment_count": evaluated_count,
        "keep_collecting_count": keep_collecting_count,
        "promote_count": promote_count,
        "reject_count": reject_count,
        "recommended_next_action": "CONTINUE_SHADOW_EXPERIMENT_COLLECTION",
        "next_round_suggestions": next_round_suggestions,
        "submit_attempted": False,
        "cancel_attempted": False,
        "flatten_attempted": False,
        "allowed_mode": "SHADOW_ONLY",
        "testnet_submit_allowed": False,
        "real_submit_allowed": False,
        "inputs": {
            "runs_final_verdict": str(runs.get("final_verdict", "")).strip().upper(),
            "outcomes_final_verdict": str(outcomes.get("final_verdict", "")).strip().upper(),
            "comparison_final_verdict": str(comparison.get("final_verdict", "")).strip().upper(),
            "promotion_final_verdict": str(promotion.get("final_verdict", "")).strip().upper(),
            "dashboard_final_verdict": str(dashboard.get("final_verdict", "")).strip().upper(),
        },
    }

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "experiment_eod_report.json"
    md_path = out_dir / "summary.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Shadow Experiment EOD Report",
        "",
        f"- final_verdict: {report['final_verdict']}",
        f"- experiment_count: {report['experiment_count']}",
        f"- experiment_candidate_count: {report['experiment_candidate_count']}",
        f"- evaluated_experiment_count: {report['evaluated_experiment_count']}",
        f"- keep_collecting_count: {report['keep_collecting_count']}",
        f"- promote_count: {report['promote_count']}",
        f"- reject_count: {report['reject_count']}",
        f"- recommended_next_action: {report['recommended_next_action']}",
        "- allowed_mode: SHADOW_ONLY",
        "- submit_attempted: false",
        "- cancel_attempted: false",
        "- flatten_attempted: false",
    ]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate EOD report for shadow experiments")
    parser.add_argument("--experiment-runs-summary-json", default="reports/shadow_observation_experiment_runs/summary.json")
    parser.add_argument("--experiment-outcomes-summary-json", default="reports/shadow_experiment_outcomes/summary.json")
    parser.add_argument("--experiment-comparison-summary-json", default="reports/shadow_experiment_comparison/summary.json")
    parser.add_argument("--experiment-promotion-summary-json", default="reports/shadow_experiment_promotion/summary.json")
    parser.add_argument(
        "--experiment-promotion-decisions-csv",
        default="reports/shadow_experiment_promotion/experiment_promotion_decisions.csv",
    )
    parser.add_argument(
        "--observation-experiment-dashboard-json",
        default="reports/observation_experiment_dashboard/observation_experiment_dashboard.json",
    )
    parser.add_argument("--output-dir", default="reports/shadow_experiment_eod")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = generate_shadow_experiment_eod_report(
        experiment_runs_summary_json=str(
            args.experiment_runs_summary_json or "reports/shadow_observation_experiment_runs/summary.json"
        ),
        experiment_outcomes_summary_json=str(
            args.experiment_outcomes_summary_json or "reports/shadow_experiment_outcomes/summary.json"
        ),
        experiment_comparison_summary_json=str(
            args.experiment_comparison_summary_json or "reports/shadow_experiment_comparison/summary.json"
        ),
        experiment_promotion_summary_json=str(
            args.experiment_promotion_summary_json or "reports/shadow_experiment_promotion/summary.json"
        ),
        experiment_promotion_decisions_csv=str(
            args.experiment_promotion_decisions_csv
            or "reports/shadow_experiment_promotion/experiment_promotion_decisions.csv"
        ),
        observation_experiment_dashboard_json=str(
            args.observation_experiment_dashboard_json
            or "reports/observation_experiment_dashboard/observation_experiment_dashboard.json"
        ),
        output_dir=str(args.output_dir or "reports/shadow_experiment_eod"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"final_verdict={result.get('final_verdict', '')}")
    print(f"recommended_next_action={result.get('recommended_next_action', '')}")


if __name__ == "__main__":
    main()
