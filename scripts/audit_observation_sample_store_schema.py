from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def audit_observation_sample_store_schema(
    source_path: str = "reports/observation_sample_store/observation_samples.csv",
    output_dir: str = "reports/observation_sample_store_audit",
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

    file_exists = False
    file_size_bytes = 0
    row_count = 0
    columns = []
    required_base_fields = ["symbol", "timeframe", "timestamp"]
    ohlcv_fields = ["open", "high", "low", "close", "volume"]
    required_base_fields_present = False
    ohlcv_fields_present = False
    ohlcv_complete_records = 0
    timestamp_parseable_records = 0
    symbol_coverage = set()
    timeframe_coverage = set()
    setup_coverage = set()
    source_type_counts = {}
    synthetic_placeholder_counts = {}
    schema_ready_for_mapping = False
    missing_fields = []
    audit_warnings = []
    missing_inputs = []

    source_path_obj = Path(source_path)
    if source_path_obj.exists():
        file_exists = True
        file_size_bytes = source_path_obj.stat().st_size

        with open(source_path_obj, newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            columns = reader.fieldnames or []

            for i, row in enumerate(reader):
                row_count += 1
                symbol = row.get("symbol")
                timeframe = row.get("timeframe")
                setup = row.get("setup") or row.get("strategy_key")
                timestamp_str = row.get("timestamp") or row.get("created_at")

                if symbol:
                    symbol_coverage.add(symbol)
                if timeframe:
                    timeframe_coverage.add(timeframe)
                if setup:
                    setup_coverage.add(setup)

                # Check OHLCV completeness
                has_ohlcv = True
                for field in ohlcv_fields:
                    if not row.get(field):
                        has_ohlcv = False
                        break
                if has_ohlcv:
                    ohlcv_complete_records += 1

                # Check timestamp parseable
                if timestamp_str:
                    try:
                        datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                        timestamp_parseable_records += 1
                    except ValueError:
                        pass

                # Check source_type and synthetic_placeholder if present
                source_type = row.get("source_type")
                synthetic_placeholder = row.get("synthetic_placeholder")

                if source_type:
                    source_type_counts[source_type] = source_type_counts.get(source_type, 0) + 1
                if synthetic_placeholder is not None:
                    key = str(synthetic_placeholder).lower()
                    synthetic_placeholder_counts[key] = synthetic_placeholder_counts.get(key, 0) + 1

    # Check required fields
    missing_base_fields = []
    for field in required_base_fields:
        # Look for field or common alternatives
        found = False
        for col in columns:
            if col.lower() == field.lower():
                found = True
                break
        if not found:
            missing_base_fields.append(field)
    required_base_fields_present = len(missing_base_fields) == 0

    # Check OHLCV fields
    missing_ohlcv = []
    for field in ohlcv_fields:
        # Look for field or common alternatives
        found = False
        for col in columns:
            if col.lower() == field.lower():
                found = True
                break
        if not found:
            missing_ohlcv.append(field)
    ohlcv_fields_present = len(missing_ohlcv) == 0

    missing_fields = missing_base_fields + missing_ohlcv
    schema_ready_for_mapping = required_base_fields_present and ohlcv_fields_present

    if not required_base_fields_present:
        audit_warnings.append(f"Missing base fields: {missing_base_fields}")
    if not ohlcv_fields_present:
        audit_warnings.append(f"Missing OHLCV fields: {missing_ohlcv}")

    final_verdict = "PASS"
    if not file_exists:
        final_verdict = "PARTIAL"
        missing_inputs.append("observation_samples.csv not found")
    elif row_count == 0:
        final_verdict = "PARTIAL"
        audit_warnings.append("No rows found in CSV")
    elif not schema_ready_for_mapping:
        final_verdict = "PARTIAL"

    # Safety checks
    safety_ok = True
    if testnet_submit_allowed or real_submit_allowed:
        final_verdict = "FAIL"
        safety_ok = False
    if submit_attempted or cancel_attempted or flatten_attempted:
        final_verdict = "FAIL"
        safety_ok = False

    report = {
        "task_id": "T396",
        "phase": "OBSERVATION_SAMPLE_STORE_SCHEMA_AUDIT",
        "allowed_mode": allowed_mode,
        "collection_mode": collection_mode,
        "submit_permission": submit_permission,
        "testnet_submit_allowed": testnet_submit_allowed,
        "real_submit_allowed": real_submit_allowed,
        "submit_attempted": submit_attempted,
        "cancel_attempted": cancel_attempted,
        "flatten_attempted": flatten_attempted,
        "source_path": source_path,
        "file_exists": file_exists,
        "file_size_bytes": file_size_bytes,
        "row_count": row_count,
        "columns": columns,
        "required_base_fields_present": required_base_fields_present,
        "ohlcv_fields_present": ohlcv_fields_present,
        "ohlcv_complete_records": ohlcv_complete_records,
        "timestamp_parseable_records": timestamp_parseable_records,
        "symbol_coverage_count": len(symbol_coverage),
        "timeframe_coverage_count": len(timeframe_coverage),
        "setup_coverage_count": len(setup_coverage),
        "source_type_counts": source_type_counts,
        "synthetic_placeholder_counts": synthetic_placeholder_counts,
        "schema_ready_for_mapping": schema_ready_for_mapping,
        "missing_fields": missing_fields,
        "audit_warnings": audit_warnings,
        "missing_inputs": missing_inputs,
        "final_verdict": final_verdict,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }

    report_json = out_dir / "observation_sample_store_schema_audit.json"
    report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    return report


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit observation sample store schema")
    parser.add_argument("--source-path", default="reports/observation_sample_store/observation_samples.csv")
    parser.add_argument("--output-dir", default="reports/observation_sample_store_audit")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = audit_observation_sample_store_schema(
        source_path=args.source_path,
        output_dir=args.output_dir,
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    print(f"task_id={result.get('task_id','')}")
    print(f"final_verdict={result.get('final_verdict','')}")
    print(f"schema_ready_for_mapping={result.get('schema_ready_for_mapping',False)}")


if __name__ == "__main__":
    main()
