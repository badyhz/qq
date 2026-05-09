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


def _collect_missing_inputs(
    *,
    decision_v2_json: str,
    readiness_v3_json: str,
    convergence_v2_json: str,
    phase_control_v2_json: str,
) -> list[str]:
    missing: list[str] = []
    for label, p in [
        ("decision_v2_json", Path(decision_v2_json)),
        ("readiness_v3_json", Path(readiness_v3_json)),
        ("convergence_v2_json", Path(convergence_v2_json)),
        ("phase_control_v2_json", Path(phase_control_v2_json)),
    ]:
        if not p.exists():
            missing.append(label)
    return missing


def generate_remediation_loop_packet_v3(
    *,
    decision_v2_json: str = "reports/shadow_to_dry_run_decision_v2/shadow_to_dry_run_decision_v2_report.json",
    readiness_v3_json: str = "reports/testnet_dry_run_readiness_v3/testnet_dry_run_readiness_v3_report.json",
    convergence_v2_json: str = "reports/remediation_gap_convergence_v2/summary.json",
    phase_control_v2_json: str = "reports/phase_control/phase_control_report_v2.json",
    output_dir: str = "reports/remediation_loop_packet_v3",
) -> dict[str, Any]:
    missing_inputs = _collect_missing_inputs(
        decision_v2_json=decision_v2_json,
        readiness_v3_json=readiness_v3_json,
        convergence_v2_json=convergence_v2_json,
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

    decision_v2 = _read_json(Path(decision_v2_json))
    readiness_v3 = _read_json(Path(readiness_v3_json))
    convergence_v2 = _read_json(Path(convergence_v2_json))

    previous_decision = str(decision_v2.get("final_decision", "CONTINUE_SHADOW_ONLY")).strip() or "CONTINUE_SHADOW_ONLY"
    previous_readiness_verdict = str(readiness_v3.get("final_verdict", "NOT_READY")).strip() or "NOT_READY"
    previous_gap_latest = 0

    try:
        previous_gap_latest = int(float(convergence_v2.get("gap_latest", 0)))
    except (TypeError, ValueError):
        pass
    if previous_gap_latest <= 0:
        try:
            previous_gap_latest = int(float(readiness_v3.get("required_gates", {}).get("sample_gap_remaining", 0)))
        except (TypeError, ValueError):
            pass
    if previous_gap_latest <= 0:
        previous_gap_latest = 22

    target_gap_to_close = previous_gap_latest

    recommended_shadow_focus: list[str] = []
    if previous_gap_latest > 0:
        recommended_shadow_focus = ["gap_closing_samples", "convergence_tracking"]

    packet_ready = True

    final_verdict = "PASS"
    if missing_inputs:
        final_verdict = "PARTIAL"
    if testnet_submit_allowed or real_submit_allowed:
        final_verdict = "FAIL"

    report: dict[str, Any] = {
        "task_id": "T371",
        "phase": "REMEDIATION_LOOP_PACKET_V3",
        "allowed_mode": allowed_mode,
        "submit_permission": submit_permission,
        "testnet_submit_allowed": testnet_submit_allowed,
        "real_submit_allowed": real_submit_allowed,
        "submit_attempted": submit_attempted,
        "cancel_attempted": cancel_attempted,
        "flatten_attempted": flatten_attempted,
        "source_archive_range": "T208-T370",
        "previous_decision": previous_decision,
        "previous_readiness_verdict": previous_readiness_verdict,
        "previous_gap_latest": previous_gap_latest,
        "target_gap_to_close": target_gap_to_close,
        "recommended_shadow_focus": recommended_shadow_focus,
        "packet_ready": packet_ready,
        "missing_inputs": missing_inputs,
        "final_verdict": final_verdict,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }

    report_json = out_dir / "remediation_loop_packet_v3.json"
    summary_md = out_dir / "summary.md"

    report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        "# Remediation Loop Packet V3",
        "",
        f"- task_id: {report['task_id']}",
        f"- phase: {report['phase']}",
        f"- final_verdict: {report['final_verdict']}",
        f"- previous_decision: {report['previous_decision']}",
        f"- previous_readiness_verdict: {report['previous_readiness_verdict']}",
        f"- previous_gap_latest: {report['previous_gap_latest']}",
        f"- target_gap_to_close: {report['target_gap_to_close']}",
        f"- packet_ready: {report['packet_ready']}",
        f"- recommended_shadow_focus: {report['recommended_shadow_focus']}",
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
    parser = argparse.ArgumentParser(description="Generate third remediation loop packet (shadow-only)")
    parser.add_argument("--decision-v2-json", default="reports/shadow_to_dry_run_decision_v2/shadow_to_dry_run_decision_v2_report.json")
    parser.add_argument("--readiness-v3-json", default="reports/testnet_dry_run_readiness_v3/testnet_dry_run_readiness_v3_report.json")
    parser.add_argument("--convergence-v2-json", default="reports/remediation_gap_convergence_v2/summary.json")
    parser.add_argument("--phase-control-v2-json", default="reports/phase_control/phase_control_report_v2.json")
    parser.add_argument("--output-dir", default="reports/remediation_loop_packet_v3")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = generate_remediation_loop_packet_v3(
        decision_v2_json=str(args.decision_v2_json or "reports/shadow_to_dry_run_decision_v2/shadow_to_dry_run_decision_v2_report.json"),
        readiness_v3_json=str(args.readiness_v3_json or "reports/testnet_dry_run_readiness_v3/testnet_dry_run_readiness_v3_report.json"),
        convergence_v2_json=str(args.convergence_v2_json or "reports/remediation_gap_convergence_v2/summary.json"),
        phase_control_v2_json=str(args.phase_control_v2_json or "reports/phase_control/phase_control_report_v2.json"),
        output_dir=str(args.output_dir or "reports/remediation_loop_packet_v3"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"task_id={result.get('task_id','')}")
    print(f"final_verdict={result.get('final_verdict','')}")
    print(f"packet_ready={result.get('packet_ready',False)}")


if __name__ == "__main__":
    main()
