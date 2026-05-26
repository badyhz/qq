#!/usr/bin/env python3
import argparse
import json
import os
from datetime import datetime, timezone
from typing import Optional, Dict, List

from core.execution_guards import assert_dry_run_required, normalize_execution_mode


def validate_real_ohlcv_gap_candidates(
    records_result: Optional[Dict] = None,
    records_json_path: Optional[str] = None
) -> Dict:
    records_analyzed = 0
    valid_ohlcv_records = 0
    invalid_records = 0
    duplicate_records = 0
    placeholder_records = 0
    fallback_values_detected = False
    timestamp_anomaly_count = 0
    gap_validation_candidate_count = 0
    valid_for_gap_validation = False
    valid_for_testnet_dry_run = False
    gap_validation_candidates: List[Dict] = []
    validation_warnings: List[str] = []
    missing_inputs: List[str] = []
    final_verdict = "PASS"
    seen_source_row_hashes = set()
    seen_record_ids = set()

    if not records_result and not records_json_path:
        missing_inputs.append("No records_result or records_json_path provided")
        final_verdict = "PARTIAL"
    elif records_json_path and os.path.exists(records_json_path):
        try:
            with open(records_json_path, "r") as f:
                records_result = json.load(f)
        except Exception as e:
            final_verdict = "FAIL"
            missing_inputs.append(f"Failed to load records JSON: {str(e)}")
    elif not records_result:
        final_verdict = "PARTIAL"

    if records_result and "records" in records_result:
        records = records_result.get("records", [])
        records_analyzed = len(records)

        for record in records:
            record_valid = True
            record_id = record.get("record_id", "")
            source_row_hash = record.get("source_row_hash", "")
            observation_only = record.get("observation_only", False)
            synthetic_placeholder = record.get("synthetic_placeholder", False)

            # Check placeholder
            if synthetic_placeholder or not observation_only:
                placeholder_records += 1
                record_valid = False

            # Check duplicate
            if source_row_hash in seen_source_row_hashes or record_id in seen_record_ids:
                duplicate_records += 1
                record_valid = False
            else:
                seen_source_row_hashes.add(source_row_hash)
                seen_record_ids.add(record_id)

            # Check OHLCV completeness
            required_fields = ["open", "high", "low", "close", "volume"]
            missing_ohlcv = False
            for f in required_fields:
                if record.get(f) is None or record.get(f) != record.get(f):
                    missing_ohlcv = True
                    break
            if missing_ohlcv:
                invalid_records += 1
                record_valid = False

            # Check timestamp
            try:
                timestamp = record.get("timestamp", 0)
                if timestamp <= 0:
                    timestamp_anomaly_count += 1
                    record_valid = False
            except (TypeError, ValueError):
                timestamp_anomaly_count += 1
                record_valid = False

            if record_valid:
                valid_ohlcv_records += 1
                gap_validation_candidates.append(record)
            else:
                invalid_records += 1

        # Calculate valid_for_gap_validation
        if (
            records_analyzed > 0
            and valid_ohlcv_records > 0
            and invalid_records == 0
            and duplicate_records == 0
            and placeholder_records == 0
            and not fallback_values_detected
            and timestamp_anomaly_count == 0
        ):
            valid_for_gap_validation = True
            gap_validation_candidate_count = valid_ohlcv_records
        else:
            valid_for_gap_validation = False
            gap_validation_candidate_count = 0

        if not valid_for_gap_validation and records_analyzed > 0:
            final_verdict = "PARTIAL"

    return {
        "task_id": "T416",
        "phase": "REAL_OHLCV_GAP_CANDIDATE_VALIDATION",
        "allowed_mode": "SHADOW_ONLY",
        "collection_mode": "SHADOW_COLLECTION",
        "submit_permission": "NO_SUBMIT",
        "testnet_submit_allowed": False,
        "real_submit_allowed": False,
        "submit_attempted": False,
        "cancel_attempted": False,
        "flatten_attempted": False,
        "records_analyzed": records_analyzed,
        "valid_ohlcv_records": valid_ohlcv_records,
        "invalid_records": invalid_records,
        "duplicate_records": duplicate_records,
        "placeholder_records": placeholder_records,
        "fallback_values_detected": fallback_values_detected,
        "timestamp_anomaly_count": timestamp_anomaly_count,
        "gap_validation_candidate_count": gap_validation_candidate_count,
        "valid_for_gap_validation": valid_for_gap_validation,
        "valid_for_testnet_dry_run": valid_for_testnet_dry_run,
        "gap_validation_candidates": gap_validation_candidates,
        "validation_warnings": validation_warnings,
        "missing_inputs": missing_inputs,
        "final_verdict": final_verdict,
        "generated_at_utc": datetime.now(timezone.utc).isoformat()
    }


def main():
    mode = normalize_execution_mode(os.environ.get("QQ_RUNTIME_MODE"))
    assert_dry_run_required(mode)

    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--records-json", type=str, help="Path to T414 records JSON file")
    args = parser.parse_args()

    result = validate_real_ohlcv_gap_candidates(records_json_path=args.records_json)

    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(f"valid_for_gap_validation: {result['valid_for_gap_validation']}")
        print(f"gap_validation_candidate_count: {result['gap_validation_candidate_count']}")


if __name__ == "__main__":
    main()
