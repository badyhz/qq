from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.strategy_edge_common import to_float_nan


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _to_int(value: Any, default: int = 0) -> int:
    parsed = to_float_nan(value)
    if not math.isfinite(parsed):
        return int(default)
    return int(parsed)


def _to_float(value: Any, default: float = float("nan")) -> float:
    parsed = to_float_nan(value)
    if not math.isfinite(parsed):
        return float(default)
    return float(parsed)


def generate_shadow_research_kpi_dashboard(
    *,
    daily_shadow_research_control_json: str = "reports/daily_shadow_research_control/daily_shadow_research_control_report.json",
    readiness_gaps_summary_json: str = "reports/testnet_dry_run_readiness_gaps/summary.json",
    remediation_summary_json: str = "reports/testnet_dry_run_remediation/summary.json",
    experiment_history_dashboard_json: str = "reports/shadow_experiment_history_dashboard/history_dashboard.json",
    experiment_sample_tracker_summary_json: str = "reports/shadow_experiment_sample_tracker/summary.json",
    experiment_stability_summary_json: str = "reports/shadow_experiment_stability/summary.json",
    shadow_research_history_summary_json: str = "reports/shadow_research_history/summary.json",
    phase_review_json: str = "reports/testnet_dry_run_phase_review/testnet_dry_run_phase_review.json",
    output_dir: str = "reports/shadow_research_kpi",
) -> dict[str, Any]:
    daily = _read_json(Path(daily_shadow_research_control_json))
    gaps = _read_json(Path(readiness_gaps_summary_json))
    remediation = _read_json(Path(remediation_summary_json))
    history_dashboard = _read_json(Path(experiment_history_dashboard_json))
    tracker = _read_json(Path(experiment_sample_tracker_summary_json))
    stability = _read_json(Path(experiment_stability_summary_json))
    research_history = _read_json(Path(shadow_research_history_summary_json))
    phase = _read_json(Path(phase_review_json))

    weighted_sample_count = _to_float(
        phase.get("metrics", {}).get("avg_weighted_sample_count"),
        _to_float(daily.get("weighted_sample_count"), 0.0),
    )
    if not math.isfinite(weighted_sample_count):
        weighted_sample_count = 0.0
    shadow_research_history_days = _to_int(
        research_history.get("history_row_count"),
        _to_int(phase.get("metrics", {}).get("history_days"), 0),
    )

    kpi = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "final_verdict": "PARTIAL",
        "current_phase": str(daily.get("current_phase", "SHADOW_EXPERIMENT_COLLECTION")).strip().upper() or "SHADOW_EXPERIMENT_COLLECTION",
        "readiness_verdict": str(phase.get("final_verdict", "NOT_READY")).strip().upper() or "NOT_READY",
        "sample_kpis": {
            "experiment_sample_count": _to_int(
                history_dashboard.get("history_row_count"),
                _to_int(tracker.get("total_current_sample_count"), 0),
            ),
            "sample_gap_total": _to_int(daily.get("sample_gap_total"), 0),
            "weighted_sample_count": round(weighted_sample_count, 8),
        },
        "history_kpis": {
            "shadow_research_history_days": shadow_research_history_days,
            "required_history_days": 3,
        },
        "stability_kpis": {
            "needs_more_data_count": _to_int(
                stability.get("needs_more_data_count"),
                _to_int(history_dashboard.get("needs_more_data_count"), 0),
            ),
            "avg_stability_score": _to_float(
                stability.get("avg_stability_score"),
                _to_float(history_dashboard.get("avg_stability_score"), 0.0),
            ),
        },
        "gap_kpis": {
            "blocking_gap_count": _to_int(gaps.get("blocking_gap_count"), 0),
            "p0_gap_count": _to_int(gaps.get("p0_gap_count"), 0),
            "p1_gap_count": _to_int(gaps.get("p1_gap_count"), 0),
        },
        "remediation_kpis": {
            "remediation_action_count": _to_int(remediation.get("remediation_action_count"), 0),
            "estimated_runs_needed": _to_int(remediation.get("estimated_runs_needed"), 0),
        },
        "allowed_mode": "SHADOW_ONLY",
        "submit_allowed": False,
        "testnet_submit_allowed": False,
        "real_submit_allowed": False,
        "recommended_next_action": str(
            remediation.get("recommended_next_action", daily.get("recommended_next_action", "RUN_REMEDIATION_SHADOW_ONLY_LOOP"))
        ).strip()
        or "RUN_REMEDIATION_SHADOW_ONLY_LOOP",
    }

    if kpi["readiness_verdict"] == "READY_FOR_TESTNET_DRY_RUN_ONLY":
        kpi["final_verdict"] = "PASS"

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "kpi_dashboard.json"
    md_path = out_dir / "summary.md"
    json_path.write_text(json.dumps(kpi, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Shadow Research KPI Dashboard",
        "",
        f"- final_verdict: {kpi['final_verdict']}",
        f"- current_phase: {kpi['current_phase']}",
        f"- readiness_verdict: {kpi['readiness_verdict']}",
        f"- sample_gap_total: {kpi['sample_kpis']['sample_gap_total']}",
        f"- blocking_gap_count: {kpi['gap_kpis']['blocking_gap_count']}",
        f"- recommended_next_action: {kpi['recommended_next_action']}",
        "- allowed_mode: SHADOW_ONLY",
        "- submit_allowed: false",
        "- testnet_submit_allowed: false",
        "- real_submit_allowed: false",
    ]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return kpi


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate KPI dashboard for shadow research progress")
    parser.add_argument("--daily-shadow-research-control-json", default="reports/daily_shadow_research_control/daily_shadow_research_control_report.json")
    parser.add_argument("--readiness-gaps-summary-json", default="reports/testnet_dry_run_readiness_gaps/summary.json")
    parser.add_argument("--remediation-summary-json", default="reports/testnet_dry_run_remediation/summary.json")
    parser.add_argument("--experiment-history-dashboard-json", default="reports/shadow_experiment_history_dashboard/history_dashboard.json")
    parser.add_argument("--experiment-sample-tracker-summary-json", default="reports/shadow_experiment_sample_tracker/summary.json")
    parser.add_argument("--experiment-stability-summary-json", default="reports/shadow_experiment_stability/summary.json")
    parser.add_argument("--shadow-research-history-summary-json", default="reports/shadow_research_history/summary.json")
    parser.add_argument("--phase-review-json", default="reports/testnet_dry_run_phase_review/testnet_dry_run_phase_review.json")
    parser.add_argument("--output-dir", default="reports/shadow_research_kpi")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = generate_shadow_research_kpi_dashboard(
        daily_shadow_research_control_json=str(
            args.daily_shadow_research_control_json or "reports/daily_shadow_research_control/daily_shadow_research_control_report.json"
        ),
        readiness_gaps_summary_json=str(
            args.readiness_gaps_summary_json or "reports/testnet_dry_run_readiness_gaps/summary.json"
        ),
        remediation_summary_json=str(args.remediation_summary_json or "reports/testnet_dry_run_remediation/summary.json"),
        experiment_history_dashboard_json=str(
            args.experiment_history_dashboard_json or "reports/shadow_experiment_history_dashboard/history_dashboard.json"
        ),
        experiment_sample_tracker_summary_json=str(
            args.experiment_sample_tracker_summary_json or "reports/shadow_experiment_sample_tracker/summary.json"
        ),
        experiment_stability_summary_json=str(
            args.experiment_stability_summary_json or "reports/shadow_experiment_stability/summary.json"
        ),
        shadow_research_history_summary_json=str(
            args.shadow_research_history_summary_json or "reports/shadow_research_history/summary.json"
        ),
        phase_review_json=str(args.phase_review_json or "reports/testnet_dry_run_phase_review/testnet_dry_run_phase_review.json"),
        output_dir=str(args.output_dir or "reports/shadow_research_kpi"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"final_verdict={result.get('final_verdict', '')}")
    print(f"readiness_verdict={result.get('readiness_verdict', '')}")


if __name__ == "__main__":
    main()
