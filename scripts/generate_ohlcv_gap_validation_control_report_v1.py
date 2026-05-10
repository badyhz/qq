#!/usr/bin/env python3
import argparse
import json
import os
from datetime import datetime, timezone
from typing import Optional, Dict, List


def generate_ohlcv_gap_validation_control_report_v1(
    dry_check_result: Optional[Dict] = None,
    ledger_result: Optional[Dict] = None,
    dry_check_json_path: Optional[str] = None,
    ledger_json_path: Optional[str] = None
) -> Dict:
    allowed_mode = "SHADOW_ONLY"
    collection_mode = "SHADOW_COLLECTION"
    submit_permission = "NO_SUBMIT"
    testnet_submit_allowed = False
    real_submit_allowed = False
    submit_attempted = False
    cancel_attempted = False
    flatten_attempted = False

    previous_gap = 22
    validated_sample_count = 0
    estimated_gap_after_validation = 22
    gap_delta = 0
    gap_validation_effective = False
    ledger_updated = False
    idempotency_ok = True
    readiness_status = "NOT_READY"
    final_decision = "CONTINUE_SHADOW_COLLECTION"
    allowed_actions = ["SHADOW_ONLY", "SHADOW_COLLECTION", "TESTNET_DRY_RUN_BLOCKED"]
    blocked_reasons: List[str] = []
    archive_range = "T208-T420"
    next_recommended_task_range = "T421-T425"
    final_verdict = "PASS"

    # Load dry_check_result from path if provided
    if not dry_check_result and dry_check_json_path and os.path.exists(dry_check_json_path):
        try:
            with open(dry_check_json_path, "r") as f:
                dry_check_result = json.load(f)
        except Exception as e:
            final_verdict = "FAIL"
            blocked_reasons.append(f"Failed to load dry_check JSON: {str(e)}")

    # Load ledger_result from path if provided
    if not ledger_result and ledger_json_path and os.path.exists(ledger_json_path):
        try:
            with open(ledger_json_path, "r") as f:
                ledger_result = json.load(f)
        except Exception as e:
            final_verdict = "FAIL"
            blocked_reasons.append(f"Failed to load ledger JSON: {str(e)}")

    # Extract fields from dry_check and ledger results
    if dry_check_result:
        previous_gap = dry_check_result.get("previous_gap", 22)
        validated_sample_count = dry_check_result.get("validated_sample_count", 0)
        estimated_gap_after_validation = dry_check_result.get("estimated_gap_after_validation", previous_gap)
        gap_delta = dry_check_result.get("gap_delta", 0)
        gap_validation_effective = dry_check_result.get("gap_validation_effective", False)

    if ledger_result:
        ledger_updated = ledger_result.get("ledger_updated", False)
        idempotency_ok = ledger_result.get("idempotency_ok", True)

    # Determine readiness and decision
    if not idempotency_ok:
        readiness_status = "FAIL"
        final_decision = "FAIL_SAFE_BLOCK"
        final_verdict = "FAIL"
        blocked_reasons.append("Ledger idempotency check failed")
    elif estimated_gap_after_validation == 0 and idempotency_ok:
        readiness_status = "GAP_VALIDATED_PENDING_REVIEW"
        final_decision = "READY_FOR_MANUAL_REVIEW_AFTER_GAP_VALIDATION"
    elif estimated_gap_after_validation > 0:
        readiness_status = "NOT_READY"
        final_decision = "CONTINUE_SHADOW_COLLECTION"
    else:
        readiness_status = "UNKNOWN"
        final_decision = "CONTINUE_SHADOW_ONLY"

    return {
        "task_id": "T420",
        "phase": "OHLCV_GAP_VALIDATION_CONTROL_REPORT_V1",
        "allowed_mode": allowed_mode,
        "collection_mode": collection_mode,
        "submit_permission": submit_permission,
        "testnet_submit_allowed": testnet_submit_allowed,
        "real_submit_allowed": real_submit_allowed,
        "submit_attempted": submit_attempted,
        "cancel_attempted": cancel_attempted,
        "flatten_attempted": flatten_attempted,
        "previous_gap": previous_gap,
        "validated_sample_count": validated_sample_count,
        "estimated_gap_after_validation": estimated_gap_after_validation,
        "gap_delta": gap_delta,
        "gap_validation_effective": gap_validation_effective,
        "ledger_updated": ledger_updated,
        "idempotency_ok": idempotency_ok,
        "readiness_status": readiness_status,
        "final_decision": final_decision,
        "allowed_actions": allowed_actions,
        "blocked_reasons": blocked_reasons,
        "archive_range": archive_range,
        "next_recommended_task_range": next_recommended_task_range,
        "final_verdict": final_verdict,
        "generated_at_utc": datetime.now(timezone.utc).isoformat()
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--dry-check-json", type=str, help="Path to T418 dry_check JSON file")
    parser.add_argument("--ledger-json", type=str, help="Path to ledger JSON file")
    args = parser.parse_args()

    result = generate_ohlcv_gap_validation_control_report_v1(
        dry_check_json_path=args.dry_check_json,
        ledger_json_path=args.ledger_json
    )

    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(f"readiness_status: {result['readiness_status']}")
        print(f"final_decision: {result['final_decision']}")


if __name__ == "__main__":
    main()
