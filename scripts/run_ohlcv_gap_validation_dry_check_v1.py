#!/usr/bin/env python3
import argparse
import json
import os
from datetime import datetime, timezone
from typing import Optional, Dict, List


def run_ohlcv_gap_validation_dry_check_v1(
    plan_result: Optional[Dict] = None,
    plan_json_path: Optional[str] = None
) -> Dict:
    previous_gap = 22
    planned_validation_count = 0
    validated_sample_count = 0
    invalid_sample_count = 0
    estimated_gap_after_validation = previous_gap
    gap_delta = 0
    gap_validation_effective = False
    still_not_ready = True
    valid_for_testnet_dry_run = False
    dry_check_warnings: List[str] = []
    missing_inputs: List[str] = []
    final_verdict = "PASS"

    if not plan_result and not plan_json_path:
        missing_inputs.append("No plan_result or plan_json_path provided")
        final_verdict = "PARTIAL"
    elif plan_json_path and os.path.exists(plan_json_path):
        try:
            with open(plan_json_path, "r") as f:
                plan_result = json.load(f)
        except Exception as e:
            final_verdict = "FAIL"
            missing_inputs.append(f"Failed to load plan JSON: {str(e)}")
    elif not plan_result:
        final_verdict = "PARTIAL"

    if plan_result:
        planned_validation_count = plan_result.get("planned_validation_count", 0)
        validation_items = plan_result.get("validation_items", [])

        for item in validation_items:
            if item.get("observation_only", False) and not item.get("dry_run_allowed", True):
                validated_sample_count += 1
            else:
                invalid_sample_count += 1

        # Calculate gap
        estimated_gap_after_validation = max(0, previous_gap - validated_sample_count)
        gap_delta = estimated_gap_after_validation - previous_gap
        gap_validation_effective = validated_sample_count > 0
        still_not_ready = estimated_gap_after_validation > 0

    return {
        "task_id": "T418",
        "phase": "OHLCV_GAP_VALIDATION_DRY_CHECK_V1",
        "allowed_mode": "SHADOW_ONLY",
        "collection_mode": "SHADOW_COLLECTION",
        "submit_permission": "NO_SUBMIT",
        "testnet_submit_allowed": False,
        "real_submit_allowed": False,
        "submit_attempted": False,
        "cancel_attempted": False,
        "flatten_attempted": False,
        "previous_gap": previous_gap,
        "planned_validation_count": planned_validation_count,
        "validated_sample_count": validated_sample_count,
        "invalid_sample_count": invalid_sample_count,
        "estimated_gap_after_validation": estimated_gap_after_validation,
        "gap_delta": gap_delta,
        "gap_validation_effective": gap_validation_effective,
        "still_not_ready": still_not_ready,
        "valid_for_testnet_dry_run": valid_for_testnet_dry_run,
        "dry_check_warnings": dry_check_warnings,
        "missing_inputs": missing_inputs,
        "final_verdict": final_verdict,
        "generated_at_utc": datetime.now(timezone.utc).isoformat()
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--plan-json", type=str, help="Path to T417 plan JSON file")
    args = parser.parse_args()

    result = run_ohlcv_gap_validation_dry_check_v1(plan_json_path=args.plan_json)

    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(f"estimated_gap_after_validation: {result['estimated_gap_after_validation']}")
        print(f"gap_delta: {result['gap_delta']}")


if __name__ == "__main__":
    main()
