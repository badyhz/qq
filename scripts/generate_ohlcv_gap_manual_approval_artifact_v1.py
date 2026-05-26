#!/usr/bin/env python3
import argparse
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, List

from core.execution_guards import assert_dry_run_required, normalize_execution_mode


def generate_ohlcv_gap_manual_approval_artifact_v1(
    checklist_interpretation: Optional[Dict] = None,
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

    manual_review_status = "UNKNOWN"
    manual_review_passed = False
    manual_operator_approved = False
    approval_artifact_ready = False
    approval_artifact_id = str(uuid.uuid4())
    approval_scope = "OHLCV_GAP_VALIDATION_ONLY"
    approval_does_not_allow_testnet_dry_run = True
    approval_does_not_allow_submit = True
    approval_items: List[Dict] = []
    blocking_reasons: List[str] = []
    allowed_actions = ["SHADOW_ONLY", "SHADOW_COLLECTION", "TESTNET_DRY_RUN_BLOCKED"]
    archive_range = "T208-T423"
    next_recommended_task_range = "T424-T425"
    final_verdict = "PASS"

    # Load checklist interpretation from path if provided
    if not checklist_interpretation and checklist_json_path and os.path.exists(checklist_json_path):
        try:
            with open(checklist_json_path, "r") as f:
                checklist_interpretation = json.load(f)
        except Exception as e:
            final_verdict = "FAIL"
            blocking_reasons.append(f"Failed to load checklist interpretation JSON: {str(e)}")

    if checklist_interpretation:
        manual_review_status = checklist_interpretation.get("manual_review_status", "UNKNOWN")
        manual_review_passed = checklist_interpretation.get("manual_review_passed", False)
        manual_operator_approved = checklist_interpretation.get("manual_operator_approved", False)

        # Build approval items
        approval_items.append({
            "item_id": str(uuid.uuid4()),
            "category": "MANUAL_REVIEW",
            "status": "PASS" if manual_review_passed else "FAIL",
            "summary": f"Manual review status: {manual_review_status}"
        })
        approval_items.append({
            "item_id": str(uuid.uuid4()),
            "category": "SAFETY",
            "status": "PASS",
            "summary": "Safety flags confirmed: no testnet/real submit allowed"
        })
        approval_items.append({
            "item_id": str(uuid.uuid4()),
            "category": "SCOPE",
            "status": "PASS",
            "summary": f"Approval scope: {approval_scope}"
        })
        approval_items.append({
            "item_id": str(uuid.uuid4()),
            "category": "APPROVAL_LIMIT",
            "status": "PASS",
            "summary": "Approval does NOT allow testnet dry-run or submit"
        })

        # Determine readiness and verdict
        if manual_review_passed and manual_operator_approved:
            approval_artifact_ready = True
            final_verdict = "PASS"
        elif manual_review_status in ["FAILED", "BLOCKED"]:
            approval_artifact_ready = False
            final_verdict = "FAIL"
            blocking_reasons.extend(checklist_interpretation.get("review_failures", []))
            if not blocking_reasons:
                blocking_reasons.append(f"Manual review status: {manual_review_status}")
        else:
            approval_artifact_ready = False
            final_verdict = "PARTIAL"
            blocking_reasons.append(f"Manual review status: {manual_review_status}")
    else:
        approval_artifact_ready = False
        final_verdict = "PARTIAL"
        blocking_reasons.append("No checklist interpretation provided")

    return {
        "task_id": "T423",
        "phase": "OHLCV_GAP_MANUAL_APPROVAL_ARTIFACT_V1",
        "allowed_mode": allowed_mode,
        "collection_mode": collection_mode,
        "submit_permission": submit_permission,
        "testnet_submit_allowed": testnet_submit_allowed,
        "real_submit_allowed": real_submit_allowed,
        "submit_attempted": submit_attempted,
        "cancel_attempted": cancel_attempted,
        "flatten_attempted": flatten_attempted,
        "manual_review_status": manual_review_status,
        "manual_review_passed": manual_review_passed,
        "manual_operator_approved": manual_operator_approved,
        "approval_artifact_ready": approval_artifact_ready,
        "approval_artifact_id": approval_artifact_id,
        "approval_scope": approval_scope,
        "approval_does_not_allow_testnet_dry_run": approval_does_not_allow_testnet_dry_run,
        "approval_does_not_allow_submit": approval_does_not_allow_submit,
        "approval_items": approval_items,
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
    parser.add_argument("--checklist-json", type=str, help="Path to T422 checklist interpretation JSON file")
    args = parser.parse_args()

    result = generate_ohlcv_gap_manual_approval_artifact_v1(
        checklist_json_path=args.checklist_json
    )

    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(f"approval_artifact_ready: {result['approval_artifact_ready']}")
        print(f"approval_does_not_allow_testnet_dry_run: {result['approval_does_not_allow_testnet_dry_run']}")


if __name__ == "__main__":
    main()
