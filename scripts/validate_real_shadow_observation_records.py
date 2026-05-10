from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def validate_real_shadow_observation_records(
    build_result: dict[str, Any] | None = None,
    reports_dir: str = "reports",
    output_dir: str = "reports/real_shadow_observation_validation",
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
    authentic_source_records = 0
    data_authenticity_passed = False
    quality_passed = False
    valid_for_gap_closure = False
    gap_closure_eligible_records: list[dict[str, Any]] = []
    validation_warnings: list[str] = []
    missing_inputs: list[str] = []

    authentic_source_types = {"SHADOW_LOG", "MARKET_OBSERVATION", "OUTCOME_RECORD"}
    seen_record_ids: set[str] = set()

    if build_result is None:
        build_path = Path(reports_dir) / "real_shadow_observation_build" / "real_shadow_observation_build.json"
        if build_path.exists():
            build_result = _read_json(build_path)
        else:
            missing_inputs.append("build_result_not_provided_and_not_found")

    if build_result:
        input_records = build_result.get("records", [])
        records_analyzed = len(input_records)

        for record in input_records:
            record_id = record.get("record_id", "")
            synthetic = record.get("synthetic_placeholder", True)
            source_type = record.get("source_type", "")
            observation_only = record.get("observation_only", False)

            is_valid = True

            # Check for duplicates
            if record_id in seen_record_ids:
                duplicate_records += 1
                is_valid = False
            else:
                seen_record_ids.add(record_id)

            # Check required fields (including OHLCV for gap closure eligibility)
            required_fields = ["record_id", "source_id", "source_type", "symbol", "timeframe", "setup", "timestamp", "open", "high", "low", "close", "volume"]
            for field in required_fields:
                if field not in record or record.get(field) is None:
                    missing_required_fields_count += 1
                    is_valid = False
                    break

            # Check timestamp
            timestamp = record.get("timestamp", "")
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    if dt > datetime.now(timezone.utc):
                        timestamp_anomaly_count += 1
                        is_valid = False
                except ValueError:
                    timestamp_anomaly_count += 1
                    is_valid = False

            # Check placeholder status
            if synthetic:
                placeholder_records += 1
                is_valid = False

            # Check authentic source
            if source_type in authentic_source_types and not synthetic:
                authentic_source_records += 1

            # Check observation only
            if not observation_only:
                invalid_records += 1
                is_valid = False

            if is_valid:
                valid_records += 1
                gap_closure_eligible_records.append(record)
            else:
                invalid_records += 1

    # Determine data_authenticity_passed
    data_authenticity_passed = (
        records_analyzed > 0
        and valid_records > 0
        and placeholder_records == 0
        and authentic_source_records == valid_records
    )

    # Determine quality_passed
    quality_passed = (
        records_analyzed > 0
        and valid_records > 0
        and invalid_records == 0
        and duplicate_records == 0
    )

    # Determine valid_for_gap_closure
    valid_for_gap_closure = (
        records_analyzed > 0
        and valid_records > 0
        and invalid_records == 0
        and duplicate_records == 0
        and placeholder_records == 0
        and data_authenticity_passed
        and quality_passed
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

    report: dict[str, Any] = {
        "task_id": "T393",
        "phase": "REAL_SHADOW_OBSERVATION_VALIDATION",
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
        "authentic_source_records": authentic_source_records,
        "data_authenticity_passed": data_authenticity_passed,
        "quality_passed": quality_passed,
        "valid_for_gap_closure": valid_for_gap_closure,
        "gap_closure_eligible_records": gap_closure_eligible_records,
        "validation_warnings": validation_warnings,
        "missing_inputs": missing_inputs,
        "final_verdict": final_verdict,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }

    report_json = out_dir / "real_shadow_observation_validation.json"
    report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    return report


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate real shadow observation records")
    parser.add_argument("--reports-dir", default="reports")
    parser.add_argument("--output-dir", default="reports/real_shadow_observation_validation")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = validate_real_shadow_observation_records(
        reports_dir=args.reports_dir,
        output_dir=args.output_dir,
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    print(f"task_id={result.get('task_id','')}")
    print(f"final_verdict={result.get('final_verdict','')}")
    print(f"valid_for_gap_closure={result.get('valid_for_gap_closure',False)}")
    print(f"valid_records={result.get('valid_records',0)}")


if __name__ == "__main__":
    main()
