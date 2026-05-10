#!/usr/bin/env python3
import argparse
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, List


def generate_ohlcv_gap_manual_review_packet_v1(
    control_report: Optional[Dict] = None,
    control_report_json_path: Optional[str] = None
) -> Dict:
    allowed_mode = "SHADOW_ONLY"
    collection_mode = "SHADOW_COLLECTION"
    submit_permission = "NO_SUBMIT"
    testnet_submit_allowed = False
    real_submit_allowed = False
    submit_attempted = False
    cancel_attempted = False
    flatten_attempted = False

    source_readiness_status = "UNKNOWN"
    source_final_decision = "UNKNOWN"
    manual_review_required = True
    manual_review_packet_ready = False
    review_items: List[Dict] = []
    review_checklist = [
        "gap_validation_result_reviewed",
        "ledger_idempotency_reviewed",
        "safety_flags_reviewed",
        "no_testnet_dry_run_permission_confirmed",
        "no_submit_permission_confirmed",
        "manual_operator_approval_required"
    ]
    blocking_findings: List[str] = []
    allowed_actions = ["SHADOW_ONLY", "SHADOW_COLLECTION", "TESTNET_DRY_RUN_BLOCKED"]
    archive_range = "T208-T421"
    next_recommended_task_range = "T422-T425"
    final_verdict = "PASS"

    # Load control report from path if provided
    if not control_report and control_report_json_path and os.path.exists(control_report_json_path):
        try:
            with open(control_report_json_path, "r") as f:
                control_report = json.load(f)
        except Exception as e:
            final_verdict = "FAIL"
            blocking_findings.append(f"Failed to load control report JSON: {str(e)}")

    if control_report:
        source_readiness_status = control_report.get("readiness_status", "UNKNOWN")
        source_final_decision = control_report.get("final_decision", "UNKNOWN")

        # Build review items based on control report
        review_items.append({
            "item_id": str(uuid.uuid4()),
            "category": "READINESS",
            "status": "PASS" if source_readiness_status in ["NOT_READY", "GAP_VALIDATED_PENDING_REVIEW"] else "FAIL",
            "summary": f"Readiness status: {source_readiness_status}",
            "evidence_field": "readiness_status"
        })

        review_items.append({
            "item_id": str(uuid.uuid4()),
            "category": "SAFETY",
            "status": "PASS" if control_report.get("testnet_submit_allowed") is False and control_report.get("real_submit_allowed") is False else "FAIL",
            "summary": "Safety flags confirmed (no testnet/real submit allowed)",
            "evidence_field": "testnet_submit_allowed, real_submit_allowed"
        })

        review_items.append({
            "item_id": str(uuid.uuid4()),
            "category": "LEDGER",
            "status": "PASS" if control_report.get("idempotency_ok") is True else "FAIL",
            "summary": f"Ledger idempotency: {control_report.get('idempotency_ok')}",
            "evidence_field": "idempotency_ok"
        })

        # Determine packet readiness and verdict
        if source_final_decision == "READY_FOR_MANUAL_REVIEW_AFTER_GAP_VALIDATION":
            manual_review_packet_ready = True
            final_verdict = "PASS"
        elif source_final_decision in ["CONTINUE_SHADOW_COLLECTION", "CONTINUE_SHADOW_ONLY"]:
            manual_review_packet_ready = False
            final_verdict = "PARTIAL"
            blocking_findings.append(f"Gap not fully closed: estimated_gap_after_validation={control_report.get('estimated_gap_after_validation')}")
        elif source_final_decision == "FAIL_SAFE_BLOCK":
            manual_review_packet_ready = False
            final_verdict = "FAIL"
            blocking_findings.extend(control_report.get("blocked_reasons", []))

    return {
        "task_id": "T421",
        "phase": "OHLCV_GAP_MANUAL_REVIEW_PACKET_V1",
        "allowed_mode": allowed_mode,
        "collection_mode": collection_mode,
        "submit_permission": submit_permission,
        "testnet_submit_allowed": testnet_submit_allowed,
        "real_submit_allowed": real_submit_allowed,
        "submit_attempted": submit_attempted,
        "cancel_attempted": cancel_attempted,
        "flatten_attempted": flatten_attempted,
        "source_readiness_status": source_readiness_status,
        "source_final_decision": source_final_decision,
        "manual_review_required": manual_review_required,
        "manual_review_packet_ready": manual_review_packet_ready,
        "review_items": review_items,
        "review_checklist": review_checklist,
        "blocking_findings": blocking_findings,
        "allowed_actions": allowed_actions,
        "archive_range": archive_range,
        "next_recommended_task_range": next_recommended_task_range,
        "final_verdict": final_verdict,
        "generated_at_utc": datetime.now(timezone.utc).isoformat()
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--control-report-json", type=str, help="Path to T420 control report JSON file")
    args = parser.parse_args()

    result = generate_ohlcv_gap_manual_review_packet_v1(
        control_report_json_path=args.control_report_json
    )

    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(f"manual_review_packet_ready: {result['manual_review_packet_ready']}")
        print(f"source_final_decision: {result['source_final_decision']}")


if __name__ == "__main__":
    main()
