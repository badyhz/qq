#!/usr/bin/env python3
import argparse
import json
import os
from datetime import datetime, timezone
from typing import Optional, Dict, List

from core.execution_guards import assert_dry_run_required, normalize_execution_mode


def interpret_ohlcv_gap_manual_review_checklist_v1(
    review_packet: Optional[Dict] = None,
    checklist_result: Optional[Dict] = None,
    review_packet_json_path: Optional[str] = None,
    checklist_json_path: Optional[str] = None
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
    checklist_items_total = 0
    checklist_items_passed = 0
    checklist_items_failed = 0
    manual_operator_approved = False
    manual_review_passed = False
    manual_review_status = "PENDING"
    review_failures: List[str] = []
    allowed_actions = ["SHADOW_ONLY", "SHADOW_COLLECTION", "TESTNET_DRY_RUN_BLOCKED"]
    archive_range = "T208-T422"
    next_recommended_task_range = "T423-T425"
    final_verdict = "PASS"

    # Load review packet from path if provided
    if not review_packet and review_packet_json_path and os.path.exists(review_packet_json_path):
        try:
            with open(review_packet_json_path, "r") as f:
                review_packet = json.load(f)
        except Exception as e:
            final_verdict = "FAIL"
            review_failures.append(f"Failed to load review packet JSON: {str(e)}")

    # Load checklist result from path if provided
    if not checklist_result and checklist_json_path and os.path.exists(checklist_json_path):
        try:
            with open(checklist_json_path, "r") as f:
                checklist_result = json.load(f)
        except Exception as e:
            final_verdict = "FAIL"
            review_failures.append(f"Failed to load checklist JSON: {str(e)}")

    if review_packet:
        manual_review_packet_ready = review_packet.get("manual_review_packet_ready", False)

    if not manual_review_packet_ready:
        manual_review_status = "BLOCKED"
        final_verdict = "PARTIAL"
        review_failures.append("Manual review packet not ready")
    else:
        if checklist_result:
            # Define required checklist items
            required_items = [
                "gap_validation_result_reviewed",
                "ledger_idempotency_reviewed",
                "safety_flags_reviewed",
                "no_testnet_dry_run_permission_confirmed",
                "no_submit_permission_confirmed",
                "manual_operator_approval_required"
            ]
            checklist_items_total = len(required_items)

            # Check each required item
            for item in required_items:
                if checklist_result.get(item) is True:
                    checklist_items_passed += 1
                else:
                    checklist_items_failed += 1
                    review_failures.append(f"Checklist item failed: {item}")

            manual_operator_approved = checklist_result.get("manual_operator_approved", False)

            # Determine status and verdict
            if checklist_items_failed > 0:
                manual_review_status = "FAILED"
                manual_review_passed = False
                final_verdict = "PARTIAL"
            elif not manual_operator_approved:
                manual_review_status = "PENDING"
                manual_review_passed = False
                final_verdict = "PASS"
            else:
                manual_review_status = "PASSED"
                manual_review_passed = True
                final_verdict = "PASS"
        else:
            manual_review_status = "PENDING"
            final_verdict = "PARTIAL"

    return {
        "task_id": "T422",
        "phase": "OHLCV_GAP_MANUAL_REVIEW_CHECKLIST_INTERPRETER_V1",
        "allowed_mode": allowed_mode,
        "collection_mode": collection_mode,
        "submit_permission": submit_permission,
        "testnet_submit_allowed": testnet_submit_allowed,
        "real_submit_allowed": real_submit_allowed,
        "submit_attempted": submit_attempted,
        "cancel_attempted": cancel_attempted,
        "flatten_attempted": flatten_attempted,
        "manual_review_packet_ready": manual_review_packet_ready,
        "checklist_items_total": checklist_items_total,
        "checklist_items_passed": checklist_items_passed,
        "checklist_items_failed": checklist_items_failed,
        "manual_operator_approved": manual_operator_approved,
        "manual_review_passed": manual_review_passed,
        "manual_review_status": manual_review_status,
        "review_failures": review_failures,
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
    parser.add_argument("--review-packet-json", type=str, help="Path to T421 manual review packet JSON file")
    parser.add_argument("--checklist-json", type=str, help="Path to checklist result JSON file")
    args = parser.parse_args()

    result = interpret_ohlcv_gap_manual_review_checklist_v1(
        review_packet_json_path=args.review_packet_json,
        checklist_json_path=args.checklist_json
    )

    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(f"manual_review_status: {result['manual_review_status']}")
        print(f"manual_review_passed: {result['manual_review_passed']}")


if __name__ == "__main__":
    main()
