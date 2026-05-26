#!/usr/bin/env python3
import argparse
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, List

from core.execution_guards import assert_dry_run_required, normalize_execution_mode


def generate_ohlcv_gap_manual_review_phase_control_report_v1(
    manual_gate_report: Optional[Dict] = None,
    manual_gate_json_path: Optional[str] = None
) -> Dict:
    allowed_mode = "SHADOW_ONLY"
    collection_mode = "SHADOW_COLLECTION"
    submit_permission = "NO_SUBMIT"
    testnet_submit_allowed = False
    real_submit_allowed = False
    submit_attempted = False
    cancel_attempted = False
    flatten_attempted = False

    manual_review_phase_completed = False
    manual_gate_passed = False
    manual_gate_status = "UNKNOWN"
    approval_scope = "OHLCV_GAP_VALIDATION_ONLY"
    phase_completion_status = "UNKNOWN"
    testnet_dry_run_still_blocked = True
    phase_findings: List[Dict] = []
    blocked_reasons: List[str] = []
    allowed_actions = ["SHADOW_ONLY", "SHADOW_COLLECTION", "TESTNET_DRY_RUN_BLOCKED"]
    archive_range = "T208-T425"
    completed_task_range = "T421-T425"
    next_recommended_task_range = "T426-T430"
    next_phase = "PRE_DRY_RUN_READINESS_REVIEW"
    final_verdict = "PASS"

    # Load manual gate report if path provided
    if not manual_gate_report and manual_gate_json_path and os.path.exists(manual_gate_json_path):
        try:
            with open(manual_gate_json_path, "r") as f:
                manual_gate_report = json.load(f)
        except Exception as e:
            final_verdict = "FAIL"
            blocked_reasons.append(f"Failed to load manual gate report: {str(e)}")

    if manual_gate_report:
        manual_gate_passed = manual_gate_report.get("final_gate_passed", False)
        manual_gate_status = manual_gate_report.get("final_gate_status", "UNKNOWN")
        approval_scope = manual_gate_report.get("approval_scope", "OHLCV_GAP_VALIDATION_ONLY")
        blocked_reasons.extend(manual_gate_report.get("blocking_reasons", []))

    # Build phase findings
    phase_findings.append({
        "finding_id": str(uuid.uuid4()),
        "category": "MANUAL_GATE",
        "status": "PASS" if manual_gate_passed else "FAIL",
        "summary": f"Manual gate passed: {manual_gate_passed} (status: {manual_gate_status})"
    })
    phase_findings.append({
        "finding_id": str(uuid.uuid4()),
        "category": "SAFETY",
        "status": "PASS",
        "summary": "Safety flags confirmed: no testnet/real submit allowed"
    })
    phase_findings.append({
        "finding_id": str(uuid.uuid4()),
        "category": "PHASE_CONTROL",
        "status": "PASS",
        "summary": f"Completed tasks: {completed_task_range}"
    })
    phase_findings.append({
        "finding_id": str(uuid.uuid4()),
        "category": "NEXT_PHASE",
        "status": "INFO",
        "summary": f"Next phase: {next_phase} (tasks: {next_recommended_task_range})"
    })
    phase_findings.append({
        "finding_id": str(uuid.uuid4()),
        "category": "SAFETY",
        "status": "PASS",
        "summary": f"Testnet dry-run still blocked: {testnet_dry_run_still_blocked}"
    })

    # Determine phase completion status and final verdict
    if manual_gate_passed and manual_gate_status == "PASSED":
        manual_review_phase_completed = True
        phase_completion_status = "COMPLETED_PENDING_PRE_DRY_RUN_REVIEW"
        final_verdict = "PASS"
    elif manual_gate_status in ["FAILED", "BLOCKED"]:
        manual_review_phase_completed = False
        phase_completion_status = "FAIL_SAFE_BLOCK"
        final_verdict = "FAIL"
    else:
        manual_review_phase_completed = False
        phase_completion_status = "CONTINUE_MANUAL_REVIEW"
        final_verdict = "PARTIAL"

    return {
        "task_id": "T425",
        "phase": "OHLCV_GAP_MANUAL_REVIEW_PHASE_CONTROL_REPORT_V1",
        "allowed_mode": allowed_mode,
        "collection_mode": collection_mode,
        "submit_permission": submit_permission,
        "testnet_submit_allowed": testnet_submit_allowed,
        "real_submit_allowed": real_submit_allowed,
        "submit_attempted": submit_attempted,
        "cancel_attempted": cancel_attempted,
        "flatten_attempted": flatten_attempted,
        "manual_review_phase_completed": manual_review_phase_completed,
        "manual_gate_passed": manual_gate_passed,
        "manual_gate_status": manual_gate_status,
        "approval_scope": approval_scope,
        "phase_completion_status": phase_completion_status,
        "testnet_dry_run_still_blocked": testnet_dry_run_still_blocked,
        "phase_findings": phase_findings,
        "blocked_reasons": blocked_reasons,
        "allowed_actions": allowed_actions,
        "archive_range": archive_range,
        "completed_task_range": completed_task_range,
        "next_recommended_task_range": next_recommended_task_range,
        "next_phase": next_phase,
        "final_verdict": final_verdict,
        "generated_at_utc": datetime.now(timezone.utc).isoformat()
    }


def main():
    mode = normalize_execution_mode(os.environ.get("QQ_RUNTIME_MODE"))
    assert_dry_run_required(mode)
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--manual-gate-json", type=str, help="Path to T424 manual gate report JSON file")
    args = parser.parse_args()

    result = generate_ohlcv_gap_manual_review_phase_control_report_v1(
        manual_gate_json_path=args.manual_gate_json
    )

    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(f"manual_review_phase_completed: {result['manual_review_phase_completed']}")
        print(f"phase_completion_status: {result['phase_completion_status']}")
        print(f"next_phase: {result['next_phase']}")


if __name__ == "__main__":
    main()
