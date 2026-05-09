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
    phase_control_v3_json: str,
    sample_quality_audit_json: str,
    convergence_v3_json: str,
) -> list[str]:
    missing: list[str] = []
    for label, p in [
        ("readiness_v4_json", Path(readiness_v4_json)),
        ("phase_control_v3_json", Path(phase_control_v3_json)),
        ("sample_quality_audit_json", Path(sample_quality_audit_json)),
        ("convergence_v3_json", Path(convergence_v3_json)),
    ]:
        if not p.exists():
            missing.append(label)
    return missing


def analyze_readiness_blocker_attribution(
    *,
    readiness_v4_json: str = "reports/testnet_dry_run_readiness_v4/testnet_dry_run_readiness_v4_report.json",
    phase_control_v3_json: str = "reports/phase_control_v3/shadow_phase_control_report_v3.json",
    sample_quality_audit_json: str = "reports/shadow_sample_quality_audit/shadow_sample_quality_audit.json",
    convergence_v3_json: str = "reports/remediation_gap_convergence_v3/summary.json",
    output_dir: str = "reports/readiness_blocker_attribution",
) -> dict[str, Any]:
    missing_inputs = _collect_missing_inputs(
        readiness_v4_json=readiness_v4_json,
        phase_control_v3_json=phase_control_v3_json,
        sample_quality_audit_json=sample_quality_audit_json,
        convergence_v3_json=convergence_v3_json,
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
    phase_ctrl_v3 = _read_json(Path(phase_control_v3_json))
    sample_quality = _read_json(Path(sample_quality_audit_json))
    conv_v3 = _read_json(Path(convergence_v3_json))

    readiness_final_verdict = str(readiness_v4.get("final_verdict", "NOT_READY")).strip().upper() or "NOT_READY"

    blockers: list[dict[str, Any]] = []
    primary_blocker = "UNKNOWN"
    blocker_count = 0
    actionability_score = 0.0
    still_not_ready = True

    # Extract blocked reasons from readiness
    blocked_reasons = readiness_v4.get("blocked_reasons", []) if isinstance(readiness_v4.get("blocked_reasons"), list) else []
    required_gates = readiness_v4.get("required_gates", {}) if isinstance(readiness_v4.get("required_gates"), dict) else {}

    # Analyze sample quality blocker
    sample_quality_ready = _to_bool(sample_quality.get("sample_quality_ready", False))
    if not sample_quality_ready:
        blockers.append({
            "code": "SAMPLE_QUALITY_NOT_READY",
            "severity": "HIGH",
            "actionable": True,
            "recommended_action": "improve_shadow_sample_quality",
        })

    # Analyze remediation effectiveness blocker
    remediation_effective = _to_bool(required_gates.get("remediation_effective", False))
    if not remediation_effective:
        if conv_v3:
            remediation_effective = _to_bool(conv_v3.get("remediation_effective", False))
    if not remediation_effective:
        blockers.append({
            "code": "REMEDIATION_NOT_EFFECTIVE",
            "severity": "HIGH",
            "actionable": True,
            "recommended_action": "run_additional_remediation_loops",
        })

    # Analyze sample gap blocker
    sample_gap_closed = _to_bool(required_gates.get("sample_gap_closed", False))
    gap_latest = 0
    if conv_v3:
        gap_latest = conv_v3.get("gap_latest", 0) or 0
        if gap_latest > 0:
            sample_gap_closed = False
    if not sample_gap_closed:
        blockers.append({
            "code": "SAMPLE_GAP_REMAINING",
            "severity": "MEDIUM",
            "actionable": True,
            "recommended_action": f"collect_{max(1, gap_latest)}_additional_samples",
        })

    # Analyze convergence blocker
    convergence_confirmed = _to_bool(required_gates.get("convergence_confirmed", False))
    if conv_v3:
        convergence_confirmed = _to_bool(conv_v3.get("convergence_confirmed", False))
    if not convergence_confirmed:
        blockers.append({
            "code": "CONVERGENCE_NOT_CONFIRMED",
            "severity": "MEDIUM",
            "actionable": True,
            "recommended_action": "continue_shadow_runs_for_convergence",
        })

    # Add any other blocked reasons from readiness
    for reason in blocked_reasons:
        if "safety" in str(reason).lower():
            blockers.append({
                "code": "SAFETY_FLAG_ISSUE",
                "severity": "CRITICAL",
                "actionable": True,
                "recommended_action": "resolve_safety_issues_first",
            })
        elif "multi_round" in str(reason).lower() and not any(b["code"] == "MULTI_ROUND_CONFIRMATION" for b in blockers):
            blockers.append({
                "code": "MULTI_ROUND_CONFIRMATION",
                "severity": "LOW",
                "actionable": False,
                "recommended_action": "wait_for_multiple_rounds",
            })

    blocker_count = len(blockers)

    # Determine primary blocker
    if blockers:
        primary_blocker = blockers[0]["code"].split("_")[0]
        # Prioritize by severity
        for b in blockers:
            if b["severity"] == "CRITICAL":
                primary_blocker = "SAFETY"
                break
            elif b["severity"] == "HIGH" and primary_blocker != "SAFETY":
                primary_blocker = b["code"].split("_")[0]

    # Calculate actionability score
    actionable_count = sum(1 for b in blockers if b["actionable"])
    if blocker_count > 0:
        actionability_score = (actionable_count / blocker_count) * 100.0
    else:
        actionability_score = 100.0

    # Determine still_not_ready
    if readiness_final_verdict == "NOT_READY":
        still_not_ready = True
    elif readiness_final_verdict == "READY":
        still_not_ready = False
    else:
        still_not_ready = True

    # Determine final verdict
    final_verdict = "PASS"
    if primary_blocker == "SAFETY":
        final_verdict = "FAIL"
    elif missing_inputs or blocker_count > 0:
        final_verdict = "PARTIAL"

    # Safety overrides
    if testnet_submit_allowed or real_submit_allowed:
        final_verdict = "FAIL"
        primary_blocker = "SAFETY"
        still_not_ready = True

    report: dict[str, Any] = {
        "task_id": "T377",
        "phase": "READINESS_BLOCKER_ATTRIBUTION",
        "allowed_mode": allowed_mode,
        "submit_permission": submit_permission,
        "testnet_submit_allowed": testnet_submit_allowed,
        "real_submit_allowed": real_submit_allowed,
        "submit_attempted": submit_attempted,
        "cancel_attempted": cancel_attempted,
        "flatten_attempted": flatten_attempted,
        "readiness_final_verdict": readiness_final_verdict,
        "blocker_count": blocker_count,
        "primary_blocker": primary_blocker,
        "blockers": blockers,
        "actionability_score": round(actionability_score, 1),
        "still_not_ready": still_not_ready,
        "missing_inputs": missing_inputs,
        "final_verdict": final_verdict,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }

    report_json = out_dir / "readiness_blocker_attribution.json"
    summary_md = out_dir / "summary.md"

    report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        "# Readiness Blocker Attribution",
        "",
        f"- task_id: {report['task_id']}",
        f"- phase: {report['phase']}",
        f"- final_verdict: {report['final_verdict']}",
        f"- readiness_final_verdict: {report['readiness_final_verdict']}",
        f"- blocker_count: {report['blocker_count']}",
        f"- primary_blocker: {report['primary_blocker']}",
        f"- blockers: {json.dumps(report['blockers'])}",
        f"- actionability_score: {report['actionability_score']}",
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
    parser = argparse.ArgumentParser(description="Analyze readiness blocker attribution")
    parser.add_argument("--readiness-v4-json", default="reports/testnet_dry_run_readiness_v4/testnet_dry_run_readiness_v4_report.json")
    parser.add_argument("--phase-control-v3-json", default="reports/phase_control_v3/shadow_phase_control_report_v3.json")
    parser.add_argument("--sample-quality-audit-json", default="reports/shadow_sample_quality_audit/shadow_sample_quality_audit.json")
    parser.add_argument("--convergence-v3-json", default="reports/remediation_gap_convergence_v3/summary.json")
    parser.add_argument("--output-dir", default="reports/readiness_blocker_attribution")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = analyze_readiness_blocker_attribution(
        readiness_v4_json=str(args.readiness_v4_json or "reports/testnet_dry_run_readiness_v4/testnet_dry_run_readiness_v4_report.json"),
        phase_control_v3_json=str(args.phase_control_v3_json or "reports/phase_control_v3/shadow_phase_control_report_v3.json"),
        sample_quality_audit_json=str(args.sample_quality_audit_json or "reports/shadow_sample_quality_audit/shadow_sample_quality_audit.json"),
        convergence_v3_json=str(args.convergence_v3_json or "reports/remediation_gap_convergence_v3/summary.json"),
        output_dir=str(args.output_dir or "reports/readiness_blocker_attribution"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"task_id={result.get('task_id','')}")
    print(f"final_verdict={result.get('final_verdict','')}")
    print(f"primary_blocker={result.get('primary_blocker','UNKNOWN')}")


if __name__ == "__main__":
    main()
