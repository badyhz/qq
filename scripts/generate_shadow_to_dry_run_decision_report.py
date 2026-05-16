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


def generate_shadow_to_dry_run_decision_report(
    *,
    readiness_v2_json: str = "reports/testnet_dry_run_readiness_v2/testnet_dry_run_readiness_v2_report.json",
    convergence_summary_json: str = "reports/remediation_gap_convergence/summary.json",
    sample_targets_summary_json: str = "reports/shadow_sample_targets/summary.json",
    phase_control_v2_json: str = "reports/phase_control/phase_control_report_v2.json",
    output_dir: str = "reports/shadow_to_dry_run_decision",
) -> dict[str, Any]:
    readiness_v2 = _read_json(Path(readiness_v2_json))
    convergence = _read_json(Path(convergence_summary_json))
    sample_targets = _read_json(Path(sample_targets_summary_json))
    phase_v2 = _read_json(Path(phase_control_v2_json))

    # Extract key decision factors
    allow_testnet_dry_run = bool(readiness_v2.get("allow_testnet_dry_run", False))
    readiness_verdict = str(readiness_v2.get("final_verdict", "NOT_READY")).strip().upper() or "NOT_READY"
    convergence_verdict = str(convergence.get("final_verdict", "IN_PROGRESS")).strip().upper() or "IN_PROGRESS"
    convergence_detected = bool(convergence.get("convergence_detected", False))
    current_sample_gap = int(convergence.get("current_sample_gap", 0) or 0)
    gap_trend_slope = float(convergence.get("gap_trend_slope", 0.0) or 0.0)
    allocation_strategy = str(sample_targets.get("allocation_strategy", "STANDARD")).strip() or "STANDARD"

    # Count blocking reasons
    blocking_reasons = readiness_v2.get("blocking_reasons", [])
    blocking_count = len(blocking_reasons)

    # Determine decision
    decision = "SHADOW_ONLY_CONTINUE"
    decision_reason = ""

    # Decision logic with safety gates
    if allow_testnet_dry_run and readiness_verdict == "READY_FOR_TESTNET_DRY_RUN":
        if convergence_verdict in {"CONVERGED", "CONVERGING"} and current_sample_gap < 5:
            decision = "APPROVE_TESTNET_DRY_RUN_ONLY"
            decision_reason = "all_readiness_criteria_met_with_convergence"
        elif convergence_detected and current_sample_gap < 10:
            decision = "APPROVE_TESTNET_DRY_RUN_ONLY"
            decision_reason = "convergence_detected_and_gap_acceptable"
        elif gap_trend_slope < 0 and current_sample_gap < 15:
            decision = "CONSIDER_TESTNET_DRY_RUN_ONLY"
            decision_reason = "gap_declining_nearing_threshold"
        else:
            decision = "CONTINUE_SHADOW_ONLY_UNTIL_CONVERGENCE"
            decision_reason = "readiness_ok_but_convergence_not_confirmed"
    elif readiness_verdict == "READY_FOR_TESTNET_DRY_RUN":
        # Readiness met but convergence not verified - be conservative
        decision = "CONTINUE_SHADOW_ONLY_UNTIL_CONVERGENCE"
        decision_reason = "readiness_met_convergence_pending"
    elif blocking_count <= 1:
        # Near ready - close to promotion
        decision = "CONTINUE_SHADOW_ONLY_NEAR_READY"
        decision_reason = f"single_blocking_reason: {blocking_reasons[0] if blocking_reasons else 'unknown'}"
    elif blocking_count <= 3:
        # Making progress but not ready
        decision = "CONTINUE_SHADOW_ONLY_PROGRESSING"
        decision_reason = f"multiple_blocking_reasons: {blocking_count}"
    elif convergence_verdict == "DIVERGING":
        # Gap is getting worse - need remediation
        decision = "RUN_REMEDIATION_SHADOW_ONLY_LOOP"
        decision_reason = "gap_diverging_requires_remediation"
    elif convergence_verdict == "STAGNANT":
        # Gap not changing - need different approach
        decision = "RUN_REMEDIATION_SHADOW_ONLY_LOOP"
        decision_reason = "gap_stagnant_requires_remediation"
    else:
        # Default to continue shadow
        decision = "SHADOW_ONLY_CONTINUE"
        decision_reason = "not_ready_for_promotion"

    # Safety: never allow real or testnet submit directly
    submit_permission = "NO_SUBMIT"
    testnet_submit_allowed = False
    real_submit_allowed = False
    allowed_mode = "SHADOW_ONLY"

    # Only allow dry-run if explicitly approved
    if decision == "APPROVE_TESTNET_DRY_RUN_ONLY":
        allowed_mode = "TESTNET_DRY_RUN_ONLY"
        submit_permission = "GATE_CONTROLLED_ONLY"

    # Final verdict
    if decision == "APPROVE_TESTNET_DRY_RUN_ONLY":
        final_verdict = "TESTNET_DRY_RUN_ONLY_READY"
    elif decision in {"CONTINUE_SHADOW_ONLY_UNTIL_CONVERGENCE", "CONTINUE_SHADOW_ONLY_NEAR_READY"}:
        final_verdict = "SHADOW_ONLY_CONTINUE"
    else:
        final_verdict = "SHADOW_ONLY_CONTINUE"

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    report_json = out_dir / "shadow_to_dry_run_decision_report.json"
    summary_md = out_dir / "summary.md"

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "final_verdict": final_verdict,
        "decision": decision,
        "decision_reason": decision_reason,
        "readiness_verdict": readiness_verdict,
        "allow_testnet_dry_run": allow_testnet_dry_run,
        "convergence_verdict": convergence_verdict,
        "convergence_detected": convergence_detected,
        "current_sample_gap": current_sample_gap,
        "gap_trend_slope": round(gap_trend_slope, 6),
        "allocation_strategy": allocation_strategy,
        "blocking_reasons_count": blocking_count,
        "blocking_reasons": blocking_reasons,
        "allowed_mode": allowed_mode,
        "submit_permission": submit_permission,
        "testnet_submit_allowed": testnet_submit_allowed,
        "real_submit_allowed": real_submit_allowed,
        "recommended_next_action": decision,
        "submit_attempted": False,
        "cancel_attempted": False,
        "flatten_attempted": False,
    }

    report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    summary_lines = [
        "# Shadow to Dry-Run Decision Report",
        "",
        f"- final_verdict: {report['final_verdict']}",
        f"- decision: {report['decision']}",
        f"- decision_reason: {report['decision_reason']}",
        f"- readiness_verdict: {report['readiness_verdict']}",
        f"- allow_testnet_dry_run: {report['allow_testnet_dry_run']}",
        f"- convergence_verdict: {report['convergence_verdict']}",
        f"- convergence_detected: {report['convergence_detected']}",
        f"- current_sample_gap: {report['current_sample_gap']}",
        f"- gap_trend_slope: {report['gap_trend_slope']}",
        f"- allocation_strategy: {report['allocation_strategy']}",
        f"- blocking_reasons_count: {report['blocking_reasons_count']}",
        f"- allowed_mode: {report['allowed_mode']}",
        f"- submit_permission: {report['submit_permission']}",
        "- testnet_submit_allowed: false",
        "- real_submit_allowed: false",
        "- submit_attempted: false",
        "- cancel_attempted: false",
        "- flatten_attempted: false",
    ]
    summary_md.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    return report


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate decision report: SHADOW_ONLY vs TESTNET_DRY_RUN_ONLY")
    parser.add_argument("--readiness-v2-json", default="reports/testnet_dry_run_readiness_v2/testnet_dry_run_readiness_v2_report.json")
    parser.add_argument("--convergence-summary-json", default="reports/remediation_gap_convergence/summary.json")
    parser.add_argument("--sample-targets-summary-json", default="reports/shadow_sample_targets/summary.json")
    parser.add_argument("--phase-control-v2-json", default="reports/phase_control/phase_control_report_v2.json")
    parser.add_argument("--output-dir", default="reports/shadow_to_dry_run_decision")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = generate_shadow_to_dry_run_decision_report(
        readiness_v2_json=str(args.readiness_v2_json or "reports/testnet_dry_run_readiness_v2/testnet_dry_run_readiness_v2_report.json"),
        convergence_summary_json=str(args.convergence_summary_json or "reports/remediation_gap_convergence/summary.json"),
        sample_targets_summary_json=str(args.sample_targets_summary_json or "reports/shadow_sample_targets/summary.json"),
        phase_control_v2_json=str(args.phase_control_v2_json or "reports/phase_control/phase_control_report_v2.json"),
        output_dir=str(args.output_dir or "reports/shadow_to_dry_run_decision"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"final_verdict={result.get('final_verdict', '')}")
    print(f"decision={result.get('decision', '')}")
    print(f"allowed_mode={result.get('allowed_mode', '')}")


if __name__ == "__main__":
    main()
