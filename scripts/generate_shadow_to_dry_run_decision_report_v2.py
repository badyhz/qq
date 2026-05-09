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


def _to_bool(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def _collect_missing_inputs(
    *,
    readiness_v3_report_json: str,
    convergence_v2_summary_json: str,
    allocator_v2_summary_json: str,
    decision_v1_report_json: str,
    phase_control_json: str,
) -> list[str]:
    missing: list[str] = []
    for label, p in [
        ("readiness_v3_report_json", Path(readiness_v3_report_json)),
        ("convergence_v2_summary_json", Path(convergence_v2_summary_json)),
        ("allocator_v2_summary_json", Path(allocator_v2_summary_json)),
        ("decision_v1_report_json", Path(decision_v1_report_json)),
        ("phase_control_json", Path(phase_control_json)),
    ]:
        if not p.exists():
            missing.append(label)
    return missing


def generate_shadow_to_dry_run_decision_report_v2(
    *,
    readiness_v3_report_json: str = "reports/testnet_dry_run_readiness_v3/testnet_dry_run_readiness_v3_report.json",
    convergence_v2_summary_json: str = "reports/remediation_gap_convergence_v2/summary.json",
    allocator_v2_summary_json: str = "reports/shadow_sample_targets_v2/summary.json",
    decision_v1_report_json: str = "reports/shadow_to_dry_run_decision/shadow_to_dry_run_decision_report.json",
    phase_control_json: str = "reports/phase_control/phase_control_report_v2.json",
    output_dir: str = "reports/shadow_to_dry_run_decision_v2",
) -> dict[str, Any]:
    missing_inputs = _collect_missing_inputs(
        readiness_v3_report_json=readiness_v3_report_json,
        convergence_v2_summary_json=convergence_v2_summary_json,
        allocator_v2_summary_json=allocator_v2_summary_json,
        decision_v1_report_json=decision_v1_report_json,
        phase_control_json=phase_control_json,
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

    # Read inputs
    readiness_v3 = _read_json(Path(readiness_v3_report_json))
    conv_v2 = _read_json(Path(convergence_v2_summary_json))
    alloc_v2 = _read_json(Path(allocator_v2_summary_json))
    decision_v1 = _read_json(Path(decision_v1_report_json))
    phase_ctrl = _read_json(Path(phase_control_json))

    # Extract readiness v3 verdict
    readiness_v3_final_verdict = str(
        readiness_v3.get("final_verdict", "NOT_READY")
    ).strip().upper() or "NOT_READY"

    readiness_trend = str(
        readiness_v3.get("readiness_trend", "UNKNOWN")
    ).strip() or "UNKNOWN"

    remediation_effective = _to_bool(readiness_v3.get("required_gates", {}).get("remediation_effective", False))
    if not remediation_effective:
        remediation_effective = _to_bool(conv_v2.get("remediation_effective", False))

    still_not_ready = _to_bool(conv_v2.get("still_not_ready", True))
    if not still_not_ready:
        still_not_ready = readiness_v3_final_verdict in {"NOT_READY", "FAIL"}

    # Build blocked reasons
    blocked_reasons: list[str] = list(
        readiness_v3.get("blocked_reasons", [])
    ) if isinstance(readiness_v3.get("blocked_reasons"), list) else []
    if missing_inputs:
        blocked_reasons.extend(f"missing_input_{m}" for m in missing_inputs)

    # Compute allowed actions
    allowed_actions: list[str] = ["SHADOW_ONLY"]
    if readiness_v3_final_verdict != "READY":
        allowed_actions.append("TESTNET_DRY_RUN_BLOCKED")

    # Final decision
    if readiness_v3_final_verdict == "READY":
        final_decision = "READY_FOR_MANUAL_TESTNET_DRY_RUN_REVIEW"
        allowed_actions = ["SHADOW_ONLY", "TESTNET_DRY_RUN_ONLY"]
    elif readiness_v3_final_verdict == "FAIL":
        final_decision = "FAIL_SAFE_BLOCK"
    else:
        final_decision = "CONTINUE_SHADOW_ONLY"

    # Safety overrides: never allow submit
    if testnet_submit_allowed or real_submit_allowed:
        final_decision = "FAIL_SAFE_BLOCK"

    # Final verdict for this task
    final_verdict = "PASS"
    if final_decision == "FAIL_SAFE_BLOCK":
        final_verdict = "FAIL"
    elif missing_inputs and readiness_v3_final_verdict != "READY":
        final_verdict = "PARTIAL"

    report: dict[str, Any] = {
        "task_id": "T370",
        "phase": "SHADOW_TO_DRY_RUN_DECISION_V2",
        "allowed_mode": allowed_mode,
        "submit_permission": submit_permission,
        "testnet_submit_allowed": testnet_submit_allowed,
        "real_submit_allowed": real_submit_allowed,
        "submit_attempted": submit_attempted,
        "cancel_attempted": cancel_attempted,
        "flatten_attempted": flatten_attempted,
        "readiness_v3_final_verdict": readiness_v3_final_verdict,
        "readiness_trend": readiness_trend,
        "remediation_effective": remediation_effective,
        "still_not_ready": still_not_ready,
        "final_decision": final_decision,
        "allowed_actions": allowed_actions,
        "blocked_reasons": blocked_reasons,
        "next_recommended_task_range": "T371-T375",
        "archive_range": "T208-T370",
        "final_verdict": final_verdict,
        "missing_inputs": missing_inputs,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }

    report_json = out_dir / "shadow_to_dry_run_decision_v2_report.json"
    summary_md = out_dir / "summary.md"

    report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        "# Shadow to Dry-Run Decision Report V2",
        "",
        f"- task_id: {report['task_id']}",
        f"- phase: {report['phase']}",
        f"- final_verdict: {report['final_verdict']}",
        f"- final_decision: {report['final_decision']}",
        f"- readiness_v3_final_verdict: {report['readiness_v3_final_verdict']}",
        f"- readiness_trend: {report['readiness_trend']}",
        f"- remediation_effective: {report['remediation_effective']}",
        f"- still_not_ready: {report['still_not_ready']}",
        f"- allowed_actions: {report['allowed_actions']}",
        f"- blocked_reasons: {report['blocked_reasons']}",
        f"- archive_range: {report['archive_range']}",
        f"- next_recommended_task_range: {report['next_recommended_task_range']}",
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
    parser = argparse.ArgumentParser(description="Generate second shadow-to-dry-run decision report")
    parser.add_argument("--readiness-v3-report-json", default="reports/testnet_dry_run_readiness_v3/testnet_dry_run_readiness_v3_report.json")
    parser.add_argument("--convergence-v2-summary-json", default="reports/remediation_gap_convergence_v2/summary.json")
    parser.add_argument("--allocator-v2-summary-json", default="reports/shadow_sample_targets_v2/summary.json")
    parser.add_argument("--decision-v1-report-json", default="reports/shadow_to_dry_run_decision/shadow_to_dry_run_decision_report.json")
    parser.add_argument("--phase-control-json", default="reports/phase_control/phase_control_report_v2.json")
    parser.add_argument("--output-dir", default="reports/shadow_to_dry_run_decision_v2")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = generate_shadow_to_dry_run_decision_report_v2(
        readiness_v3_report_json=str(args.readiness_v3_report_json or "reports/testnet_dry_run_readiness_v3/testnet_dry_run_readiness_v3_report.json"),
        convergence_v2_summary_json=str(args.convergence_v2_summary_json or "reports/remediation_gap_convergence_v2/summary.json"),
        allocator_v2_summary_json=str(args.allocator_v2_summary_json or "reports/shadow_sample_targets_v2/summary.json"),
        decision_v1_report_json=str(args.decision_v1_report_json or "reports/shadow_to_dry_run_decision/shadow_to_dry_run_decision_report.json"),
        phase_control_json=str(args.phase_control_json or "reports/phase_control/phase_control_report_v2.json"),
        output_dir=str(args.output_dir or "reports/shadow_to_dry_run_decision_v2"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"task_id={result.get('task_id','')}")
    print(f"final_verdict={result.get('final_verdict','')}")
    print(f"final_decision={result.get('final_decision','')}")


if __name__ == "__main__":
    main()
