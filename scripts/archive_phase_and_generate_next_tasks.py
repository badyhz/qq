from __future__ import annotations

import argparse
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


def archive_phase_and_generate_next_tasks(
    *,
    phase_control_v2_json: str = "reports/phase_control/phase_control_report_v2.json",
    remediation_result_json: str = "reports/remediation_result/remediation_result.json",
    shadow_research_kpi_json: str = "reports/shadow_research_kpi/kpi_dashboard.json",
    testnet_dry_run_phase_review_json: str = "reports/testnet_dry_run_phase_review/testnet_dry_run_phase_review.json",
    experiment_history_dashboard_json: str = "reports/shadow_experiment_history_dashboard/history_dashboard.json",
    output_dir: str = "reports/phase_archive",
) -> dict[str, Any]:
    phase_v2 = _read_json(Path(phase_control_v2_json))
    remediation = _read_json(Path(remediation_result_json))
    kpi = _read_json(Path(shadow_research_kpi_json))
    phase_review = _read_json(Path(testnet_dry_run_phase_review_json))
    history_dashboard = _read_json(Path(experiment_history_dashboard_json))

    recommended_next_action = str(
        remediation.get("recommended_next_action", phase_v2.get("recommended_next_action", "CONTINUE_REMEDIATION_SHADOW_ONLY_LOOP"))
    ).strip() or "CONTINUE_REMEDIATION_SHADOW_ONLY_LOOP"

    index = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "archive_range": "T208-T360",
        "phase_name": "SHADOW_RESEARCH_AND_TESTNET_SAFETY_PREPARATION",
        "final_verdict": str(phase_v2.get("final_verdict", "SHADOW_ONLY_CONTINUE")).strip().upper() or "SHADOW_ONLY_CONTINUE",
        "core_reports": [
            "reports/phase_control/phase_control_report_v2.json",
            "reports/testnet_dry_run_phase_review/testnet_dry_run_phase_review.json",
        ],
        "safety_summary": {
            "submit_attempted": False,
            "cancel_attempted": False,
            "flatten_attempted": False,
            "testnet_submit_allowed": False,
            "real_submit_allowed": False,
        },
        "next_recommended_task_range": "T361-T365",
        "recommended_next_action": recommended_next_action,
        "context": {
            "kpi_readiness_verdict": str(kpi.get("readiness_verdict", "")).strip().upper() or "UNKNOWN",
            "phase_review_verdict": str(phase_review.get("final_verdict", "")).strip().upper() or "UNKNOWN",
            "experiment_count": int(history_dashboard.get("experiment_count", 0) or 0),
        },
    }

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    index_json = out_dir / "phase_archive_index.json"
    next_tasks_md = out_dir / "next_tasks_T361_T365.md"
    summary_md = out_dir / "summary.md"
    index_json.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")

    task_lines = [
        "# Next Tasks T361-T365",
        "",
        "1. T361：remediation loop 多轮运行历史",
        "2. T362：remediation gap 收敛趋势分析",
        "3. T363：shadow sample target auto allocator",
        "4. T364：dry-run readiness 再评估 v2",
        "5. T365：是否继续 SHADOW_ONLY 或准备 TESTNET_DRY_RUN_ONLY 的决策报告",
        "",
        f"- recommended_next_action: {recommended_next_action}",
    ]
    next_tasks_md.write_text("\n".join(task_lines) + "\n", encoding="utf-8")

    summary_lines = [
        "# Phase Archive Summary",
        "",
        f"- archive_range: {index['archive_range']}",
        f"- phase_name: {index['phase_name']}",
        f"- final_verdict: {index['final_verdict']}",
        f"- next_recommended_task_range: {index['next_recommended_task_range']}",
        f"- recommended_next_action: {index['recommended_next_action']}",
        "- testnet_submit_allowed: false",
        "- real_submit_allowed: false",
        "- submit_attempted: false",
        "- cancel_attempted: false",
        "- flatten_attempted: false",
    ]
    summary_md.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
    return index


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Archive current phase and generate next task suggestions")
    parser.add_argument("--phase-control-v2-json", default="reports/phase_control/phase_control_report_v2.json")
    parser.add_argument("--remediation-result-json", default="reports/remediation_result/remediation_result.json")
    parser.add_argument("--shadow-research-kpi-json", default="reports/shadow_research_kpi/kpi_dashboard.json")
    parser.add_argument("--testnet-dry-run-phase-review-json", default="reports/testnet_dry_run_phase_review/testnet_dry_run_phase_review.json")
    parser.add_argument("--experiment-history-dashboard-json", default="reports/shadow_experiment_history_dashboard/history_dashboard.json")
    parser.add_argument("--output-dir", default="reports/phase_archive")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = archive_phase_and_generate_next_tasks(
        phase_control_v2_json=str(args.phase_control_v2_json or "reports/phase_control/phase_control_report_v2.json"),
        remediation_result_json=str(args.remediation_result_json or "reports/remediation_result/remediation_result.json"),
        shadow_research_kpi_json=str(args.shadow_research_kpi_json or "reports/shadow_research_kpi/kpi_dashboard.json"),
        testnet_dry_run_phase_review_json=str(
            args.testnet_dry_run_phase_review_json or "reports/testnet_dry_run_phase_review/testnet_dry_run_phase_review.json"
        ),
        experiment_history_dashboard_json=str(
            args.experiment_history_dashboard_json or "reports/shadow_experiment_history_dashboard/history_dashboard.json"
        ),
        output_dir=str(args.output_dir or "reports/phase_archive"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"archive_range={result.get('archive_range', '')}")
    print(f"final_verdict={result.get('final_verdict', '')}")


if __name__ == "__main__":
    main()
