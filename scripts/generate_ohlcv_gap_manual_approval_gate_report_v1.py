#!/usr/bin/env python3
import argparse
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, List

from core.execution_guards import assert_dry_run_required, normalize_execution_mode


def generate_ohlcv_gap_manual_approval_gate_report_v1(
    review_packet: Optional[Dict] = None,
    checklist_interpretation: Optional[Dict] = None,
    approval_artifact: Optional[Dict] = None
) -> Dict:
    allowed_mode = "SHADOW_ONLY"
    collection_mode = "SHADOW_COLLECTION"
    submit_permission = "NO_SUBMIT"
    testnet_submit_allowed = False
    real_submit_allowed = False
    submit_attempted = False
    cancel_attempted = False
    flatten_attempted = False

    manual_review_packet_ready = False
    manual_review_passed = False
    manual_operator_approved = False
    approval_artifact_ready = False
    approval_scope = "OHLCV_GAP_VALIDATION_ONLY"
    final_gate_passed = False
    final_gate_status = "BLOCKED"
    gate_findings: List[Dict] = []
    blocking_reasons: List[str] = []
    allowed_actions = ["SHADOW_ONLY", "SHADOW_COLLECTION", "TESTNET_DRY_RUN_BLOCKED"]
    archive_range = "T208-T424"
    next_recommended_task_range = "T425"
    final_verdict = "PASS"

    # Extract fields from inputs
    if review_packet:
        manual_review_packet_ready = review_packet.get("manual_review_packet_ready", False)
    if checklist_interpretation:
        manual_review_passed = checklist_interpretation.get("manual_review_passed", False)
        manual_operator_approved = checklist_interpretation.get("manual_operator_approved", False)
    if approval_artifact:
        approval_artifact_ready = approval_artifact.get("approval_artifact_ready", False)
        approval_scope = approval_artifact.get("approval_scope", "OHLCV_GAP_VALIDATION_ONLY")

    # Build gate findings
    gate_findings.append({
        "finding_id": str(uuid.uuid4()),
        "category": "MANUAL_REVIEW",
        "status": "PASS" if manual_review_packet_ready else "FAIL",
        "summary": f"Manual review packet ready: {manual_review_packet_ready}"
    })
    gate_findings.append({
        "finding_id": str(uuid.uuid4()),
        "category": "CHECKLIST",
        "status": "PASS" if manual_review_passed else "FAIL",
        "summary": f"Manual review passed: {manual_review_passed}"
    })
    gate_findings.append({
        "finding_id": str(uuid.uuid4()),
        "category": "CHECKLIST",
        "status": "PASS" if manual_operator_approved else "FAIL",
        "summary": f"Manual operator approved: {manual_operator_approved}"
    })
    gate_findings.append({
        "finding_id": str(uuid.uuid4()),
        "category": "APPROVAL_ARTIFACT",
        "status": "PASS" if approval_artifact_ready else "FAIL",
        "summary": f"Approval artifact ready: {approval_artifact_ready}"
    })
    gate_findings.append({
        "finding_id": str(uuid.uuid4()),
        "category": "SCOPE",
        "status": "PASS" if approval_scope == "OHLCV_GAP_VALIDATION_ONLY" else "FAIL",
        "summary": f"Approval scope: {approval_scope}"
    })
    gate_findings.append({
        "finding_id": str(uuid.uuid4()),
        "category": "SAFETY",
        "status": "PASS",
        "summary": "Safety flags confirmed: no testnet/real submit allowed"
    })

    # Determine gate status and verdict
    if (manual_review_packet_ready and manual_review_passed and manual_operator_approved and 
        approval_artifact_ready and approval_scope == "OHLCV_GAP_VALIDATION_ONLY"):
        final_gate_passed = True
        final_gate_status = "PASSED"
        final_verdict = "PASS"
    else:
        final_gate_passed = False
        if not manual_review_packet_ready:
            blocking_reasons.append("Manual review packet not ready")
        if not manual_review_passed:
            blocking_reasons.append("Manual review not passed")
        if not manual_operator_approved:
            blocking_reasons.append("Manual operator not approved")
        if not approval_artifact_ready:
            blocking_reasons.append("Approval artifact not ready")
        if approval_scope != "OHLCV_GAP_VALIDATION_ONLY":
            blocking_reasons.append(f"Wrong approval scope: {approval_scope}")
        
        if "Manual operator not approved" in blocking_reasons and len(blocking_reasons) == 1:
            final_gate_status = "PENDING"
        elif any(s in blocking_reasons for s in ["Manual review not passed", "Wrong approval scope"]):
            final_gate_status = "FAILED"
        else:
            final_gate_status = "BLOCKED"
        
        final_verdict = "PARTIAL" if final_gate_status == "PENDING" else "FAIL"

    return {
        "task_id": "T424",
        "phase": "OHLCV_GAP_MANUAL_APPROVAL_GATE_REPORT_V1",
        "allowed_mode": allowed_mode,
        "collection_mode": collection_mode,
        "submit_permission": submit_permission,
        "testnet_submit_allowed": testnet_submit_allowed,
        "real_submit_allowed": real_submit_allowed,
        "submit_attempted": submit_attempted,
        "cancel_attempted": cancel_attempted,
        "flatten_attempted": flatten_attempted,
        "manual_review_packet_ready": manual_review_packet_ready,
        "manual_review_passed": manual_review_passed,
        "manual_operator_approved": manual_operator_approved,
        "approval_artifact_ready": approval_artifact_ready,
        "approval_scope": approval_scope,
        "final_gate_passed": final_gate_passed,
        "final_gate_status": final_gate_status,
        "gate_findings": gate_findings,
        "blocking_reasons": blocking_reasons,
        "allowed_actions": allowed_actions,
        "archive_range": archive_range,
        "next_recommended_task_range": next_recommended_task_range,
        "final_verdict": final_verdict,
        "generated_at_utc": datetime.now(timezone.utc).isoformat()
    }


def main():
    mode = normalize_execution_mode(os.environ.get("QQ_RUNTIME_MODE"))
    assert_dry_run_required(mode)
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = generate_ohlcv_gap_manual_approval_gate_report_v1()

    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(f"final_gate_passed: {result['final_gate_passed']}")
        print(f"final_gate_status: {result['final_gate_status']}")


if __name__ == "__main__":
    main()
