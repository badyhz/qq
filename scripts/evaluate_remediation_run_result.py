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


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return int(default)


def evaluate_remediation_run_result(
    *,
    remediation_loop_run_report_json: str = "reports/remediation_loop_run/remediation_loop_run_report.json",
    readiness_gaps_summary_json: str = "reports/testnet_dry_run_readiness_gaps/summary.json",
    remediation_summary_json: str = "reports/testnet_dry_run_remediation/summary.json",
    shadow_experiment_progress_gap_summary_json: str = "reports/shadow_experiment_progress_gap/summary.json",
    daily_shadow_research_control_json: str = "reports/daily_shadow_research_control/daily_shadow_research_control_report.json",
    testnet_dry_run_phase_review_json: str = "reports/testnet_dry_run_phase_review/testnet_dry_run_phase_review.json",
    output_dir: str = "reports/remediation_result",
) -> dict[str, Any]:
    run_report = _read_json(Path(remediation_loop_run_report_json))
    gaps = _read_json(Path(readiness_gaps_summary_json))
    remediation = _read_json(Path(remediation_summary_json))
    progress_gap = _read_json(Path(shadow_experiment_progress_gap_summary_json))
    daily = _read_json(Path(daily_shadow_research_control_json))
    phase = _read_json(Path(testnet_dry_run_phase_review_json))

    sample_gap_before = _to_int(run_report.get("sample_gap_before"), _to_int(daily.get("sample_gap_total"), 0))
    sample_gap_after = _to_int(run_report.get("sample_gap_after"), _to_int(progress_gap.get("sample_gap_total"), sample_gap_before))
    gap_delta = _to_int(run_report.get("gap_delta"), sample_gap_before - sample_gap_after)
    new_candidates = _to_int(run_report.get("new_experiment_candidates"), 0) + _to_int(run_report.get("new_shadow_candidates"), 0)

    gap_improved = gap_delta > 0 or sample_gap_after < sample_gap_before
    remediation_effective = gap_improved or new_candidates > 0
    still_not_ready = str(phase.get("final_verdict", "NOT_READY")).strip().upper() != "READY_FOR_TESTNET_DRY_RUN_ONLY"
    blocking_remaining = list(phase.get("blocking_reasons", []))
    if not isinstance(blocking_remaining, list):
        blocking_remaining = []

    recommended_next_action = "CONTINUE_REMEDIATION_SHADOW_ONLY_LOOP"
    if remediation_effective and still_not_ready:
        recommended_next_action = "CONTINUE_REMEDIATION_SHADOW_ONLY_LOOP"
    elif (not remediation_effective) and still_not_ready:
        recommended_next_action = "CONTINUE_REMEDIATION_SHADOW_ONLY_LOOP"

    final_verdict = "PARTIAL"
    if remediation_effective and not still_not_ready:
        final_verdict = "PASS"
    elif str(run_report.get("final_verdict", "")).strip().upper() == "FAIL":
        final_verdict = "FAIL"

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "final_verdict": final_verdict,
        "remediation_effective": bool(remediation_effective),
        "gap_improved": bool(gap_improved),
        "sample_gap_before": sample_gap_before,
        "sample_gap_after": sample_gap_after,
        "gap_delta": gap_delta,
        "new_candidates_collected": max(0, new_candidates),
        "still_not_ready": bool(still_not_ready),
        "recommended_next_action": recommended_next_action,
        "blocking_reasons_remaining": sorted(set(str(x).strip() for x in blocking_remaining if str(x).strip())),
        "allowed_mode": "SHADOW_ONLY",
        "submit_allowed": False,
        "testnet_submit_allowed": False,
        "real_submit_allowed": False,
        "submit_attempted": False,
        "cancel_attempted": False,
        "flatten_attempted": False,
        "context": {
            "blocking_gap_count": _to_int(gaps.get("blocking_gap_count"), 0),
            "remediation_action_count": _to_int(remediation.get("remediation_action_count"), 0),
        },
    }

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "remediation_result.json"
    md_path = out_dir / "summary.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Remediation Result",
        "",
        f"- final_verdict: {report['final_verdict']}",
        f"- remediation_effective: {str(report['remediation_effective']).lower()}",
        f"- still_not_ready: {str(report['still_not_ready']).lower()}",
        f"- sample_gap_before: {report['sample_gap_before']}",
        f"- sample_gap_after: {report['sample_gap_after']}",
        f"- gap_delta: {report['gap_delta']}",
        f"- recommended_next_action: {report['recommended_next_action']}",
        "- allowed_mode: SHADOW_ONLY",
        "- submit_allowed: false",
        "- testnet_submit_allowed: false",
        "- real_submit_allowed: false",
    ]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate effectiveness of one remediation shadow-only loop run")
    parser.add_argument("--remediation-loop-run-report-json", default="reports/remediation_loop_run/remediation_loop_run_report.json")
    parser.add_argument("--readiness-gaps-summary-json", default="reports/testnet_dry_run_readiness_gaps/summary.json")
    parser.add_argument("--remediation-summary-json", default="reports/testnet_dry_run_remediation/summary.json")
    parser.add_argument("--shadow-experiment-progress-gap-summary-json", default="reports/shadow_experiment_progress_gap/summary.json")
    parser.add_argument("--daily-shadow-research-control-json", default="reports/daily_shadow_research_control/daily_shadow_research_control_report.json")
    parser.add_argument("--testnet-dry-run-phase-review-json", default="reports/testnet_dry_run_phase_review/testnet_dry_run_phase_review.json")
    parser.add_argument("--output-dir", default="reports/remediation_result")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = evaluate_remediation_run_result(
        remediation_loop_run_report_json=str(
            args.remediation_loop_run_report_json or "reports/remediation_loop_run/remediation_loop_run_report.json"
        ),
        readiness_gaps_summary_json=str(args.readiness_gaps_summary_json or "reports/testnet_dry_run_readiness_gaps/summary.json"),
        remediation_summary_json=str(args.remediation_summary_json or "reports/testnet_dry_run_remediation/summary.json"),
        shadow_experiment_progress_gap_summary_json=str(
            args.shadow_experiment_progress_gap_summary_json or "reports/shadow_experiment_progress_gap/summary.json"
        ),
        daily_shadow_research_control_json=str(
            args.daily_shadow_research_control_json or "reports/daily_shadow_research_control/daily_shadow_research_control_report.json"
        ),
        testnet_dry_run_phase_review_json=str(
            args.testnet_dry_run_phase_review_json or "reports/testnet_dry_run_phase_review/testnet_dry_run_phase_review.json"
        ),
        output_dir=str(args.output_dir or "reports/remediation_result"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"final_verdict={result.get('final_verdict', '')}")
    print(f"still_not_ready={str(result.get('still_not_ready', True)).lower()}")


if __name__ == "__main__":
    main()
