from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def validate_normalized_price_observation_records(
    build_result: dict[str, Any] | None = None,
    output_dir: str = "reports/normalized_price_observation_validation",
) -> dict[str, Any]:
    allowed_mode = "SHADOW_ONLY"
    collection_mode = "SHADOW_COLLECTION"
    submit_permission = "NO_SUBMIT"
    testnet_submit_allowed = False
    real_submit_allowed = False
    submit_attempted = False
    cancel_attempted = False
    flatten_attempted = False

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    records_analyzed = 0
    valid_records = 0
    invalid_records = 0
    duplicate_records = 0
    placeholder_records = 0
    missing_required_fields_count = 0
    timestamp_anomaly_count = 0
    price_valid_records = 0
    authentic_source_records = 0
    fallback_values_detected = False
    data_authenticity_passed = False
    quality_passed = False
    valid_for_gap_closure = False
    gap_closure_eligible_records = []
    validation_warnings = []
    missing_inputs = []

    authentic_source_types = {"SHADOW_LOG", "MARKET_OBSERVATION", "OUTCOME_RECORD"}
    seen_row_hashes = set()
    seen_record_ids = set()

    if build_result:
        input_records = build_result.get("records", [])
        records_analyzed = len(input_records)

        for record in input_records:
            is_valid = True
            record_id = record.get("record_id")
            source_row_hash = record.get("source_row_hash")
            synthetic_placeholder = record.get("synthetic_placeholder", True)
            source_type = record.get("source_type")
            observation_only = record.get("observation_only", False)

            # Check duplicate row hash
            if source_row_hash and source_row_hash in seen_row_hashes:
                duplicate_records += 1
                is_valid = False
            elif source_row_hash:
                seen_row_hashes.add(source_row_hash)

            # Check duplicate record id
            if record_id and record_id in seen_record_ids:
                duplicate_records += 1
                is_valid = False
            elif record_id:
                seen_record_ids.add(record_id)

            # Check placeholder status
            if synthetic_placeholder:
                placeholder_records += 1
                is_valid = False

            # Check authentic source
            if source_type in authentic_source_types and not synthetic_placeholder:
                authentic_source_records += 1

            # Check observation only
            if not observation_only:
                invalid_records += 1
                is_valid = False

            # Check required fields including price
            required_fields = ["record_id", "source_type", "symbol", "timeframe", "setup", "timestamp", "price", "price_source_field"]
            has_all_fields = True
            for field in required_fields:
                if field not in record or record.get(field) is None:
                    has_all_fields = False
                    missing_required_fields_count += 1
                    is_valid = False
                    break

            # Check price valid and numeric
            price_valid = has_all_fields
            if has_all_fields:
                try:
                    price_val = float(record["price"])
                    if price_val <= 0:
                        price_valid = False
                        missing_required_fields_count += 1
                        is_valid = False
                except (ValueError, TypeError):
                    price_valid = False
                    missing_required_fields_count += 1
                    is_valid = False

            if price_valid:
                price_valid_records += 1

            # Check timestamp
            timestamp_str = record.get("timestamp")
            valid_timestamp = True
            if timestamp_str:
                try:
                    dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                    if dt > datetime.now(timezone.utc):
                        valid_timestamp = False
                except ValueError:
                    valid_timestamp = False
            else:
                valid_timestamp = False

            if not valid_timestamp:
                timestamp_anomaly_count += 1
                is_valid = False

            if is_valid:
                valid_records += 1
                gap_closure_eligible_records.append(record)
            else:
                invalid_records += 1

    # Determine data_authenticity_passed
    data_authenticity_passed = (
        records_analyzed > 0 and
        valid_records > 0 and
        placeholder_records == 0 and
        authentic_source_records == valid_records and
        not fallback_values_detected
    )

    # Determine quality_passed
    quality_passed = (
        records_analyzed > 0 and
        valid_records > 0 and
        invalid_records == 0 and
        duplicate_records == 0 and
        missing_required_fields_count == 0 and
        timestamp_anomaly_count == 0 and
        price_valid_records == valid_records
    )

    # Determine valid_for_gap_closure
    valid_for_gap_closure = (
        records_analyzed > 0 and
        valid_records > 0 and
        invalid_records == 0 and
        duplicate_records == 0 and
        placeholder_records == 0 and
        missing_required_fields_count == 0 and
        timestamp_anomaly_count == 0 and
        not fallback_values_detected and
        data_authenticity_passed and
        quality_passed
    )

    if duplicate_records > 0:
        validation_warnings.append(f"Found {duplicate_records} duplicate records")
    if placeholder_records > 0:
        validation_warnings.append(f"Found {placeholder_records} placeholder records")
    if missing_required_fields_count > 0:
        validation_warnings.append(f"Found {missing_required_fields_count} records with missing required fields")

    final_verdict = "PASS"
    if missing_inputs:
        final_verdict = "PARTIAL"
    if records_analyzed == 0:
        final_verdict = "PARTIAL"
    if not valid_for_gap_closure and records_analyzed > 0:
        final_verdict = "PARTIAL"

    # Safety checks
    if testnet_submit_allowed or real_submit_allowed:
        final_verdict = "FAIL"
    if submit_attempted or cancel_attempted or flatten_attempted:
        final_verdict = "FAIL"

    report = {
        "task_id": "T404",
        "phase": "NORMALIZED_PRICE_OBSERVATION_RECORD_VALIDATION",
        "allowed_mode": allowed_mode,
        "collection_mode": collection_mode,
        "submit_permission": submit_permission,
        "testnet_submit_allowed": testnet_submit_allowed,
        "real_submit_allowed": real_submit_allowed,
        "submit_attempted": submit_attempted,
        "cancel_attempted": cancel_attempted,
        "flatten_attempted": flatten_attempted,
        "records_analyzed": records_analyzed,
        "valid_records": valid_records,
        "invalid_records": invalid_records,
        "duplicate_records": duplicate_records,
        "placeholder_records": placeholder_records,
        "missing_required_fields_count": missing_required_fields_count,
        "timestamp_anomaly_count": timestamp_anomaly_count,
        "price_valid_records": price_valid_records,
        "authentic_source_records": authentic_source_records,
        "fallback_values_detected": fallback_values_detected,
        "data_authenticity_passed": data_authenticity_passed,
        "quality_passed": quality_passed,
        "valid_for_gap_closure": valid_for_gap_closure,
        "gap_closure_eligible_records": gap_closure_eligible_records,
        "validation_warnings": validation_warnings,
        "missing_inputs": missing_inputs,
        "final_verdict": final_verdict,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }

    report_json = out_dir / "normalized_price_observation_validation.json"
    report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    return report


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate normalized price observation records")
    parser.add_argument("--output-dir", default="reports/normalized_price_observation_validation")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = validate_normalized_price_observation_records(
        output_dir=args.output_dir,
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    print(f"task_id={result.get('task_id','')}")
    print(f"final_verdict={result.get('final_verdict','')}")
    print(f"valid_for_gap_closure={result.get('valid_for_gap_closure',False)}")


if __name__ == "__main__":
    main()
