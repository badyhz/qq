#!/usr/bin/env python3
import argparse
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, List


def generate_ohlcv_gap_validation_plan_v1(
    candidate_result: Optional[Dict] = None,
    candidate_json_path: Optional[str] = None
) -> Dict:
    previous_gap = 22
    gap_validation_candidate_count = 0
    planned_validation_count = 0
    validation_items: List[Dict] = []
    plan_ready = False
    valid_for_gap_validation = False
    valid_for_testnet_dry_run = False
    missing_inputs: List[str] = []
    final_verdict = "PASS"

    if not candidate_result and not candidate_json_path:
        missing_inputs.append("No candidate_result or candidate_json_path provided")
        final_verdict = "PARTIAL"
    elif candidate_json_path and os.path.exists(candidate_json_path):
        try:
            with open(candidate_json_path, "r") as f:
                candidate_result = json.load(f)
        except Exception as e:
            final_verdict = "FAIL"
            missing_inputs.append(f"Failed to load candidate JSON: {str(e)}")
    elif not candidate_result:
        final_verdict = "PARTIAL"

    if candidate_result:
        valid_for_gap_validation = candidate_result.get("valid_for_gap_validation", False)
        candidates = candidate_result.get("gap_validation_candidates", [])
        gap_validation_candidate_count = len(candidates)

        if valid_for_gap_validation and gap_validation_candidate_count > 0:
            # Take up to previous_gap candidates
            max_candidates = min(gap_validation_candidate_count, previous_gap)
            for candidate in candidates[:max_candidates]:
                validation_item = {
                    "validation_id": str(uuid.uuid4()),
                    "record_id": candidate.get("record_id", ""),
                    "symbol": candidate.get("symbol", ""),
                    "timeframe": candidate.get("timeframe", ""),
                    "timestamp": candidate.get("timestamp", ""),
                    "validation_type": "OHLCV_SAMPLE_GAP_VALIDATION",
                    "observation_only": True,
                    "dry_run_allowed": False,
                    "reason": "Valid real OHLCV observation record for gap validation"
                }
                validation_items.append(validation_item)

            planned_validation_count = len(validation_items)

            if planned_validation_count > 0:
                plan_ready = True
            else:
                plan_ready = False
                final_verdict = "PARTIAL"
        else:
            plan_ready = False
            final_verdict = "PARTIAL"

    return {
        "task_id": "T417",
        "phase": "OHLCV_GAP_VALIDATION_PLAN_V1",
        "allowed_mode": "SHADOW_ONLY",
        "collection_mode": "SHADOW_COLLECTION",
        "submit_permission": "NO_SUBMIT",
        "testnet_submit_allowed": False,
        "real_submit_allowed": False,
        "submit_attempted": False,
        "cancel_attempted": False,
        "flatten_attempted": False,
        "previous_gap": previous_gap,
        "gap_validation_candidate_count": gap_validation_candidate_count,
        "planned_validation_count": planned_validation_count,
        "validation_items": validation_items,
        "plan_ready": plan_ready,
        "valid_for_gap_validation": valid_for_gap_validation,
        "valid_for_testnet_dry_run": valid_for_testnet_dry_run,
        "missing_inputs": missing_inputs,
        "final_verdict": final_verdict,
        "generated_at_utc": datetime.now(timezone.utc).isoformat()
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--candidate-json", type=str, help="Path to T416 candidate JSON file")
    args = parser.parse_args()

    result = generate_ohlcv_gap_validation_plan_v1(candidate_json_path=args.candidate_json)

    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(f"plan_ready: {result['plan_ready']}")
        print(f"planned_validation_count: {result['planned_validation_count']}")


if __name__ == "__main__":
    main()
