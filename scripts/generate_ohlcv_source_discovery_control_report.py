#!/usr/bin/env python3
import argparse
import json
import os
from datetime import datetime, timezone
from typing import Optional, Dict


def generate_ohlcv_source_discovery_control_report(
    mapping_result: Optional[Dict] = None,
    records_result: Optional[Dict] = None
) -> Dict:
    candidate_source_count = 0
    ohlcv_ready_source_count = 0
    selected_source_count = 0
    mapping_ready = False
    records_built = 0
    valid_ohlcv_source_available = False
    previous_gap = 22
    estimated_gap_after_ohlcv_discovery = 22
    gap_delta = 0
    ohlcv_discovery_effective = False
    readiness_status = "NOT_READY"
    final_decision = "CONTINUE_SHADOW_COLLECTION"
    allowed_actions = ["SHADOW_ONLY", "SHADOW_COLLECTION", "TESTNET_DRY_RUN_BLOCKED"]
    blocked_reasons = []
    final_verdict = "PASS"

    if mapping_result:
        selected_source_count = mapping_result.get("selected_source_count", 0)
        mapping_ready = mapping_result.get("mapping_ready", False)
        ohlcv_ready_source_count = mapping_result.get("selected_source_count", 0)
        candidate_source_count = mapping_result.get("selected_source_count", 0)

    if records_result:
        records_built = records_result.get("records_built", 0)

    if mapping_ready and records_built > 0:
        readiness_status = "READY"
        final_decision = "READY_FOR_OHLCV_GAP_VALIDATION"
        valid_ohlcv_source_available = True

    final_verdict = "PASS"
    if not mapping_ready and records_built == 0:
        final_verdict = "PARTIAL"

    return {
        "task_id": "T415",
        "phase": "OHLCV_SOURCE_DISCOVERY_CONTROL_REPORT",
        "allowed_mode": "SHADOW_ONLY",
        "collection_mode": "SHADOW_COLLECTION",
        "submit_permission": "NO_SUBMIT",
        "testnet_submit_allowed": False,
        "real_submit_allowed": False,
        "submit_attempted": False,
        "cancel_attempted": False,
        "flatten_attempted": False,
        "candidate_source_count": candidate_source_count,
        "ohlcv_ready_source_count": ohlcv_ready_source_count,
        "selected_source_count": selected_source_count,
        "mapping_ready": mapping_ready,
        "records_built": records_built,
        "valid_ohlcv_source_available": valid_ohlcv_source_available,
        "previous_gap": previous_gap,
        "estimated_gap_after_ohlcv_discovery": estimated_gap_after_ohlcv_discovery,
        "gap_delta": gap_delta,
        "ohlcv_discovery_effective": ohlcv_discovery_effective,
        "readiness_status": readiness_status,
        "final_decision": final_decision,
        "allowed_actions": allowed_actions,
        "blocked_reasons": blocked_reasons,
        "archive_range": "T208-T415",
        "next_recommended_task_range": "T416-T420",
        "final_verdict": final_verdict,
        "generated_at_utc": datetime.now(timezone.utc).isoformat()
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--mapping-json", type=str, help="Path to T413 mapping JSON file")
    parser.add_argument("--records-json", type=str, help="Path to T414 records JSON file")
    args = parser.parse_args()

    mapping_result = None
    if args.mapping_json and os.path.exists(args.mapping_json):
        with open(args.mapping_json, "r") as f:
            mapping_result = json.load(f)

    records_result = None
    if args.records_json and os.path.exists(args.records_json):
        with open(args.records_json, "r") as f:
            records_result = json.load(f)

    result = generate_ohlcv_source_discovery_control_report(
        mapping_result=mapping_result,
        records_result=records_result
    )

    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(f"Final decision: {result['final_decision']}")
        print(f"Records built: {result['records_built']}")
        print(f"Mapping ready: {result['mapping_ready']}")


if __name__ == "__main__":
    main()
