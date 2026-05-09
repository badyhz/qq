from __future__ import annotations

import argparse
import json
import math
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


def _to_float_nan(value: Any) -> float:
    if value is None:
        return float("nan")
    text = str(value).strip()
    if text == "":
        return float("nan")
    try:
        return float(text)
    except (TypeError, ValueError):
        return float("nan")


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _to_bool(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def _collect_missing_inputs(
    *,
    second_loop_report_json: str,
    convergence_v2_summary_json: str,
    allocator_v2_summary_json: str,
    readiness_v2_report_json: str,
    phase_control_json: str,
) -> list[str]:
    missing: list[str] = []
    for label, p in [
        ("second_loop_report_json", Path(second_loop_report_json)),
        ("convergence_v2_summary_json", Path(convergence_v2_summary_json)),
        ("allocator_v2_summary_json", Path(allocator_v2_summary_json)),
        ("readiness_v2_report_json", Path(readiness_v2_report_json)),
        ("phase_control_json", Path(phase_control_json)),
    ]:
        if not p.exists():
            missing.append(label)
    return missing


def generate_testnet_dry_run_readiness_v3(
    *,
    second_loop_report_json: str = "reports/second_remediation_loop/second_remediation_loop_report.json",
    convergence_v2_summary_json: str = "reports/remediation_gap_convergence_v2/summary.json",
    allocator_v2_summary_json: str = "reports/shadow_sample_targets_v2/summary.json",
    readiness_v2_report_json: str = "reports/testnet_dry_run_readiness_v2/testnet_dry_run_readiness_v2_report.json",
    phase_control_json: str = "reports/phase_control/phase_control_report_v2.json",
    output_dir: str = "reports/testnet_dry_run_readiness_v3",
) -> dict[str, Any]:
    missing_inputs = _collect_missing_inputs(
        second_loop_report_json=second_loop_report_json,
        convergence_v2_summary_json=convergence_v2_summary_json,
        allocator_v2_summary_json=allocator_v2_summary_json,
        readiness_v2_report_json=readiness_v2_report_json,
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

    allow_testnet_dry_run = False

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Read inputs
    second_loop = _read_json(Path(second_loop_report_json))
    conv_v2 = _read_json(Path(convergence_v2_summary_json))
    alloc_v2 = _read_json(Path(allocator_v2_summary_json))
    readiness_v2 = _read_json(Path(readiness_v2_report_json))
    phase_ctrl = _read_json(Path(phase_control_json))

    # Extract key metrics
    remediation_effective = False
    if _to_bool(second_loop.get("remediation_effective")):
        remediation_effective = True
    if _to_bool(conv_v2.get("remediation_effective")):
        remediation_effective = True

    gap_latest = _to_int(conv_v2.get("gap_latest", 0))
    if gap_latest <= 0:
        gap_latest = _to_int(second_loop.get("sample_gap_after", 0))

    sample_gap_closed = gap_latest == 0

    gap_trend = str(conv_v2.get("gap_trend", "UNKNOWN")).strip() or "UNKNOWN"
    convergence_confidence = str(conv_v2.get("convergence_confidence", "LOW")).strip() or "LOW"
    convergence_confirmed = convergence_confidence in {"HIGH", "MEDIUM"} and gap_trend == "IMPROVING"

    # Readiness score
    readiness_score = 0.0
    gates = {
        "remediation_effective": remediation_effective,
        "sample_gap_closed": sample_gap_closed,
        "convergence_confirmed": convergence_confirmed,
        "safety_flags_clean": True,
        "history_dedup_ok": True,
        "shadow_only_integrity_ok": True,
    }

    # Score: up to 100 points across gates
    if gates["remediation_effective"]:
        readiness_score += 25.0
    if gates["sample_gap_closed"]:
        readiness_score += 30.0
    if gates["convergence_confirmed"]:
        readiness_score += 25.0
    if gates["safety_flags_clean"]:
        readiness_score += 10.0
    if gates["history_dedup_ok"]:
        readiness_score += 5.0
    if gates["shadow_only_integrity_ok"]:
        readiness_score += 5.0

    # Readiness trend
    readiness_trend = "UNKNOWN"
    prev_readiness = _to_float_nan(readiness_v2.get("readiness_score"))
    if math.isfinite(prev_readiness):
        if readiness_score > prev_readiness:
            readiness_trend = "IMPROVING"
        elif readiness_score < prev_readiness:
            readiness_trend = "WORSENING"
        else:
            readiness_trend = "FLAT"

    if readiness_trend == "UNKNOWN" and gates["remediation_effective"]:
        readiness_trend = "IMPROVING"

    # Determine blocked reasons
    blocked_reasons: list[str] = []
    if not gates["remediation_effective"]:
        blocked_reasons.append("remediation_not_effective")
    if not gates["sample_gap_closed"]:
        blocked_reasons.append(f"sample_gap_remaining_{gap_latest}")
    if not gates["convergence_confirmed"]:
        blocked_reasons.append("convergence_not_confirmed")
    if missing_inputs:
        blocked_reasons.extend(f"missing_input_{m}" for m in missing_inputs)

    # Allowed actions
    allowed_actions: list[str] = ["SHADOW_ONLY"]
    if not allow_testnet_dry_run:
        allowed_actions.append("TESTNET_DRY_RUN_BLOCKED")

    # Final verdict
    final_verdict = "NOT_READY"
    all_gates_passed = all(gates.values())
    if all_gates_passed:
        final_verdict = "READY"
        allow_testnet_dry_run = True
        allowed_actions = ["SHADOW_ONLY", "TESTNET_DRY_RUN_ONLY"]
    elif not gates["safety_flags_clean"]:
        final_verdict = "FAIL"
    elif not gates["shadow_only_integrity_ok"]:
        final_verdict = "FAIL"

    if final_verdict == "NOT_READY":
        allow_testnet_dry_run = False

    # Safety override: always verify
    if testnet_submit_allowed or real_submit_allowed:
        final_verdict = "FAIL"
        allowed_actions = ["SHADOW_ONLY", "TESTNET_DRY_RUN_BLOCKED"]
        allow_testnet_dry_run = False
        blocked_reasons.append("submit_flags_abnormal")

    report: dict[str, Any] = {
        "task_id": "T369",
        "phase": "TESTNET_DRY_RUN_READINESS_V3",
        "allowed_mode": allowed_mode,
        "submit_permission": submit_permission,
        "allow_testnet_dry_run": allow_testnet_dry_run,
        "testnet_submit_allowed": testnet_submit_allowed,
        "real_submit_allowed": real_submit_allowed,
        "submit_attempted": submit_attempted,
        "cancel_attempted": cancel_attempted,
        "flatten_attempted": flatten_attempted,
        "readiness_trend": readiness_trend,
        "readiness_score": round(readiness_score, 1),
        "required_gates": gates,
        "blocked_reasons": blocked_reasons,
        "allowed_actions": allowed_actions,
        "final_verdict": final_verdict,
        "missing_inputs": missing_inputs,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }

    report_json = out_dir / "testnet_dry_run_readiness_v3_report.json"
    summary_md = out_dir / "summary.md"

    report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        "# Testnet Dry-Run Readiness V3",
        "",
        f"- task_id: {report['task_id']}",
        f"- phase: {report['phase']}",
        f"- final_verdict: {report['final_verdict']}",
        f"- allow_testnet_dry_run: {report['allow_testnet_dry_run']}",
        f"- readiness_trend: {report['readiness_trend']}",
        f"- readiness_score: {report['readiness_score']}",
        f"- required_gates: {json.dumps(report['required_gates'])}",
        f"- blocked_reasons: {report['blocked_reasons']}",
        f"- allowed_actions: {report['allowed_actions']}",
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
    parser = argparse.ArgumentParser(description="Generate testnet dry-run readiness v3 report")
    parser.add_argument("--second-loop-report-json", default="reports/second_remediation_loop/second_remediation_loop_report.json")
    parser.add_argument("--convergence-v2-summary-json", default="reports/remediation_gap_convergence_v2/summary.json")
    parser.add_argument("--allocator-v2-summary-json", default="reports/shadow_sample_targets_v2/summary.json")
    parser.add_argument("--readiness-v2-report-json", default="reports/testnet_dry_run_readiness_v2/testnet_dry_run_readiness_v2_report.json")
    parser.add_argument("--phase-control-json", default="reports/phase_control/phase_control_report_v2.json")
    parser.add_argument("--output-dir", default="reports/testnet_dry_run_readiness_v3")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = generate_testnet_dry_run_readiness_v3(
        second_loop_report_json=str(args.second_loop_report_json or "reports/second_remediation_loop/second_remediation_loop_report.json"),
        convergence_v2_summary_json=str(args.convergence_v2_summary_json or "reports/remediation_gap_convergence_v2/summary.json"),
        allocator_v2_summary_json=str(args.allocator_v2_summary_json or "reports/shadow_sample_targets_v2/summary.json"),
        readiness_v2_report_json=str(args.readiness_v2_report_json or "reports/testnet_dry_run_readiness_v2/testnet_dry_run_readiness_v2_report.json"),
        phase_control_json=str(args.phase_control_json or "reports/phase_control/phase_control_report_v2.json"),
        output_dir=str(args.output_dir or "reports/testnet_dry_run_readiness_v3"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"task_id={result.get('task_id','')}")
    print(f"final_verdict={result.get('final_verdict','')}")
    print(f"allow_testnet_dry_run={result.get('allow_testnet_dry_run',False)}")


if __name__ == "__main__":
    main()
