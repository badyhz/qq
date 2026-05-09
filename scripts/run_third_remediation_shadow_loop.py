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
        return default


def _collect_missing_inputs(
    *,
    remediation_loop_packet_v3_json: str,
    second_loop_report_json: str,
    shadow_outcomes_summary_json: str,
    shadow_research_control_json: str,
) -> list[str]:
    missing: list[str] = []
    for label, p in [
        ("remediation_loop_packet_v3_json", Path(remediation_loop_packet_v3_json)),
        ("second_loop_report_json", Path(second_loop_report_json)),
        ("shadow_outcomes_summary_json", Path(shadow_outcomes_summary_json)),
        ("shadow_research_control_json", Path(shadow_research_control_json)),
    ]:
        if not p.exists():
            missing.append(label)
    return missing


def run_third_remediation_shadow_loop(
    *,
    remediation_loop_packet_v3_json: str = "reports/remediation_loop_packet_v3/remediation_loop_packet_v3.json",
    second_loop_report_json: str = "reports/second_remediation_loop/second_remediation_loop_report.json",
    shadow_outcomes_summary_json: str = "reports/shadow_candidate_outcomes/summary.json",
    shadow_research_control_json: str = "reports/daily_shadow_research_control/daily_shadow_research_control_report.json",
    output_dir: str = "reports/third_remediation_loop",
) -> dict[str, Any]:
    missing_inputs = _collect_missing_inputs(
        remediation_loop_packet_v3_json=remediation_loop_packet_v3_json,
        second_loop_report_json=second_loop_report_json,
        shadow_outcomes_summary_json=shadow_outcomes_summary_json,
        shadow_research_control_json=shadow_research_control_json,
    )

    allowed_mode = "SHADOW_ONLY"
    submit_permission = "NO_SUBMIT"
    testnet_submit_allowed = False
    real_submit_allowed = False
    submit_attempted = False
    cancel_attempted = False
    flatten_attempted = False

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    third_loop_run_id = f"THIRD_REMEDIATION_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"

    packet_v3 = _read_json(Path(remediation_loop_packet_v3_json))
    second_loop = _read_json(Path(second_loop_report_json))
    shadow_outcomes = _read_json(Path(shadow_outcomes_summary_json))
    research_control = _read_json(Path(shadow_research_control_json))

    target_gap = _to_int(packet_v3.get("target_gap_to_close", 22))
    previous_gap = _to_int(packet_v3.get("previous_gap_latest", 22))
    if previous_gap <= 0:
        previous_gap = _to_int(second_loop.get("sample_gap_after", 22))

    sample_gap_before = previous_gap if previous_gap > 0 else 22

    source_history_runs = _to_int(second_loop.get("source_history_runs", 0))

    new_shadow_samples = _to_int(shadow_outcomes.get("shadow_sample_count", 0))
    new_experiment_candidates = _to_int(research_control.get("total_experiments", 0))

    sample_gap_after = sample_gap_before
    if target_gap > 0 and new_shadow_samples > 0:
        sample_gap_after = max(0, sample_gap_before - new_shadow_samples)
    if sample_gap_after == 0 and sample_gap_before > 0:
        sample_gap_after = sample_gap_before

    gap_delta = sample_gap_after - sample_gap_before

    remediation_effective = sample_gap_after < sample_gap_before
    still_not_ready = sample_gap_after > 0

    final_verdict = "PASS"
    if missing_inputs:
        final_verdict = "PARTIAL"
    if testnet_submit_allowed or real_submit_allowed:
        final_verdict = "FAIL"

    report: dict[str, Any] = {
        "task_id": "T372",
        "phase": "SHADOW_ONLY_REMEDIATION_ROUND_3",
        "allowed_mode": allowed_mode,
        "submit_permission": submit_permission,
        "testnet_submit_allowed": testnet_submit_allowed,
        "real_submit_allowed": real_submit_allowed,
        "submit_attempted": submit_attempted,
        "cancel_attempted": cancel_attempted,
        "flatten_attempted": flatten_attempted,
        "third_loop_run_id": third_loop_run_id,
        "source_history_runs": source_history_runs,
        "new_shadow_samples_detected": max(0, new_shadow_samples),
        "new_experiment_candidates": max(0, new_experiment_candidates),
        "sample_gap_before": sample_gap_before,
        "sample_gap_after": sample_gap_after,
        "gap_delta": gap_delta,
        "remediation_effective": remediation_effective,
        "still_not_ready": still_not_ready,
        "missing_inputs": missing_inputs,
        "final_verdict": final_verdict,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }

    report_json = out_dir / "third_remediation_loop_report.json"
    summary_md = out_dir / "summary.md"

    report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        "# Third Remediation Shadow-Only Loop",
        "",
        f"- task_id: {report['task_id']}",
        f"- phase: {report['phase']}",
        f"- final_verdict: {report['final_verdict']}",
        f"- third_loop_run_id: {report['third_loop_run_id']}",
        f"- source_history_runs: {report['source_history_runs']}",
        f"- new_shadow_samples_detected: {report['new_shadow_samples_detected']}",
        f"- new_experiment_candidates: {report['new_experiment_candidates']}",
        f"- sample_gap_before: {report['sample_gap_before']}",
        f"- sample_gap_after: {report['sample_gap_after']}",
        f"- gap_delta: {report['gap_delta']}",
        f"- remediation_effective: {report['remediation_effective']}",
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
    parser = argparse.ArgumentParser(description="Run third remediation shadow-only loop")
    parser.add_argument("--remediation-loop-packet-v3-json", default="reports/remediation_loop_packet_v3/remediation_loop_packet_v3.json")
    parser.add_argument("--second-loop-report-json", default="reports/second_remediation_loop/second_remediation_loop_report.json")
    parser.add_argument("--shadow-outcomes-summary-json", default="reports/shadow_candidate_outcomes/summary.json")
    parser.add_argument("--shadow-research-control-json", default="reports/daily_shadow_research_control/daily_shadow_research_control_report.json")
    parser.add_argument("--output-dir", default="reports/third_remediation_loop")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = run_third_remediation_shadow_loop(
        remediation_loop_packet_v3_json=str(args.remediation_loop_packet_v3_json or "reports/remediation_loop_packet_v3/remediation_loop_packet_v3.json"),
        second_loop_report_json=str(args.second_loop_report_json or "reports/second_remediation_loop/second_remediation_loop_report.json"),
        shadow_outcomes_summary_json=str(args.shadow_outcomes_summary_json or "reports/shadow_candidate_outcomes/summary.json"),
        shadow_research_control_json=str(args.shadow_research_control_json or "reports/daily_shadow_research_control/daily_shadow_research_control_report.json"),
        output_dir=str(args.output_dir or "reports/third_remediation_loop"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"task_id={result.get('task_id','')}")
    print(f"final_verdict={result.get('final_verdict','')}")
    print(f"remediation_effective={result.get('remediation_effective',False)}")
    print(f"still_not_ready={result.get('still_not_ready',True)}")


if __name__ == "__main__":
    main()
