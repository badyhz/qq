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
    readiness_v4_json: str,
    convergence_v3_json: str,
    third_loop_report_json: str,
    phase_control_v2_json: str,
) -> list[str]:
    missing: list[str] = []
    for label, p in [
        ("readiness_v4_json", Path(readiness_v4_json)),
        ("convergence_v3_json", Path(convergence_v3_json)),
        ("third_loop_report_json", Path(third_loop_report_json)),
        ("phase_control_v2_json", Path(phase_control_v2_json)),
    ]:
        if not p.exists():
            missing.append(label)
    return missing


def generate_shadow_phase_control_report_v3(
    *,
    readiness_v4_json: str = "reports/testnet_dry_run_readiness_v4/testnet_dry_run_readiness_v4_report.json",
    convergence_v3_json: str = "reports/remediation_gap_convergence_v3/summary.json",
    third_loop_report_json: str = "reports/third_remediation_loop/third_remediation_loop_report.json",
    phase_control_v2_json: str = "reports/phase_control/phase_control_report_v2.json",
    output_dir: str = "reports/phase_control_v3",
) -> dict[str, Any]:
    missing_inputs = _collect_missing_inputs(
        readiness_v4_json=readiness_v4_json,
        convergence_v3_json=convergence_v3_json,
        third_loop_report_json=third_loop_report_json,
        phase_control_v2_json=phase_control_v2_json,
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

    readiness_v4 = _read_json(Path(readiness_v4_json))
    conv_v3 = _read_json(Path(convergence_v3_json))
    third_loop = _read_json(Path(third_loop_report_json))
    phase_ctrl_v2 = _read_json(Path(phase_control_v2_json))

    readiness_v4_final_verdict = str(
        readiness_v4.get("final_verdict", "NOT_READY")
    ).strip().upper() or "NOT_READY"

    readiness_trend = str(
        readiness_v4.get("readiness_trend", "UNKNOWN")
    ).strip() or "UNKNOWN"

    remediation_effective = _to_bool(readiness_v4.get("required_gates", {}).get("remediation_effective", False))
    if not remediation_effective:
        remediation_effective = _to_bool(conv_v3.get("remediation_effective", False))
    if not remediation_effective:
        remediation_effective = _to_bool(third_loop.get("remediation_effective", False))

    still_not_ready = True
    if readiness_v4_final_verdict == "READY":
        still_not_ready = False
    if _to_bool(conv_v3.get("still_not_ready", True)):
        still_not_ready = True

    blocked_reasons: list[str] = list(
        readiness_v4.get("blocked_reasons", [])
    ) if isinstance(readiness_v4.get("blocked_reasons"), list) else []
    if missing_inputs:
        blocked_reasons.extend(f"missing_input_{m}" for m in missing_inputs)

    if readiness_v4_final_verdict == "READY":
        final_decision = "READY_FOR_MANUAL_TESTNET_DRY_RUN_REVIEW"
    elif readiness_v4_final_verdict == "FAIL":
        final_decision = "FAIL_SAFE_BLOCK"
    else:
        final_decision = "CONTINUE_SHADOW_ONLY"

    allowed_actions: list[str] = ["SHADOW_ONLY"]
    if final_decision == "CONTINUE_SHADOW_ONLY":
        allowed_actions.append("TESTNET_DRY_RUN_BLOCKED")
    elif final_decision == "READY_FOR_MANUAL_TESTNET_DRY_RUN_REVIEW":
        allowed_actions = ["SHADOW_ONLY", "TESTNET_DRY_RUN_ONLY"]

    # Safety overrides
    if testnet_submit_allowed or real_submit_allowed:
        final_decision = "FAIL_SAFE_BLOCK"
        allowed_actions = ["SHADOW_ONLY", "TESTNET_DRY_RUN_BLOCKED"]

    final_verdict = "PASS"
    if final_decision == "FAIL_SAFE_BLOCK":
        final_verdict = "FAIL"
    elif missing_inputs and readiness_v4_final_verdict != "READY":
        final_verdict = "PARTIAL"

    report: dict[str, Any] = {
        "task_id": "T375",
        "phase": "SHADOW_PHASE_CONTROL_V3",
        "allowed_mode": allowed_mode,
        "submit_permission": submit_permission,
        "testnet_submit_allowed": testnet_submit_allowed,
        "real_submit_allowed": real_submit_allowed,
        "submit_attempted": submit_attempted,
        "cancel_attempted": cancel_attempted,
        "flatten_attempted": flatten_attempted,
        "readiness_v4_final_verdict": readiness_v4_final_verdict,
        "readiness_trend": readiness_trend,
        "remediation_effective": remediation_effective,
        "still_not_ready": still_not_ready,
        "final_decision": final_decision,
        "allowed_actions": allowed_actions,
        "blocked_reasons": blocked_reasons,
        "archive_range": "T208-T375",
        "next_recommended_task_range": "T376-T380",
        "final_verdict": final_verdict,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }

    report_json = out_dir / "shadow_phase_control_report_v3.json"
    summary_md = out_dir / "summary.md"

    report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        "# Shadow Phase Control Report V3",
        "",
        f"- task_id: {report['task_id']}",
        f"- phase: {report['phase']}",
        f"- final_verdict: {report['final_verdict']}",
        f"- final_decision: {report['final_decision']}",
        f"- readiness_v4_final_verdict: {report['readiness_v4_final_verdict']}",
        f"- readiness_trend: {report['readiness_trend']}",
        f"- remediation_effective: {report['remediation_effective']}",
        f"- still_not_ready: {report['still_not_ready']}",
        f"- allowed_actions: {report['allowed_actions']}",
        f"- blocked_reasons: {report['blocked_reasons']}",
        f"- archive_range: {report['archive_range']}",
        f"- next_recommended_task_range: {report['next_recommended_task_range']}",
        f"- missing_inputs: {[]}",
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
    parser = argparse.ArgumentParser(description="Generate shadow phase control report v3")
    parser.add_argument("--readiness-v4-json", default="reports/testnet_dry_run_readiness_v4/testnet_dry_run_readiness_v4_report.json")
    parser.add_argument("--convergence-v3-json", default="reports/remediation_gap_convergence_v3/summary.json")
    parser.add_argument("--third-loop-report-json", default="reports/third_remediation_loop/third_remediation_loop_report.json")
    parser.add_argument("--phase-control-v2-json", default="reports/phase_control/phase_control_report_v2.json")
    parser.add_argument("--output-dir", default="reports/phase_control_v3")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = generate_shadow_phase_control_report_v3(
        readiness_v4_json=str(args.readiness_v4_json or "reports/testnet_dry_run_readiness_v4/testnet_dry_run_readiness_v4_report.json"),
        convergence_v3_json=str(args.convergence_v3_json or "reports/remediation_gap_convergence_v3/summary.json"),
        third_loop_report_json=str(args.third_loop_report_json or "reports/third_remediation_loop/third_remediation_loop_report.json"),
        phase_control_v2_json=str(args.phase_control_v2_json or "reports/phase_control/phase_control_report_v2.json"),
        output_dir=str(args.output_dir or "reports/phase_control_v3"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"task_id={result.get('task_id','')}")
    print(f"final_verdict={result.get('final_verdict','')}")
    print(f"final_decision={result.get('final_decision','')}")


if __name__ == "__main__":
    main()
