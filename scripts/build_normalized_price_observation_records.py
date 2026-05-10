from __future__ import annotations

import argparse
import csv
import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def build_normalized_price_observation_records(
    audit_result: dict[str, Any] | None = None,
    mapping_result: dict[str, Any] | None = None,
    source_path: str = "reports/observation_sample_store/observation_samples.csv",
    output_dir: str = "reports/normalized_price_observation_records",
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

    mapping_ready = False
    source_rows_scanned = 0
    records_built = 0
    records = []
    records_skipped_missing_price = 0
    records_skipped_invalid_timestamp = 0
    fallback_values_used = False
    missing_inputs = []

    primary_price_field = None
    backup_price_fields = []

    if mapping_result:
        mapping_ready = mapping_result.get("mapping_ready", False)
        price_field_mappings = mapping_result.get("price_field_mappings", {})
        primary_price_field = price_field_mappings.get("primary")
        backup_price_fields = price_field_mappings.get("backups", [])

        if mapping_ready and primary_price_field:
            source_path_obj = Path(source_path)
            if source_path_obj.exists():
                with open(source_path_obj, newline="", encoding="utf-8") as csvfile:
                    reader = csv.DictReader(csvfile)

                    for row in reader:
                        source_rows_scanned += 1

                        # Get price value, try primary first then backups
                        price_value = None
                        price_source_field = None

                        if primary_price_field and row.get(primary_price_field):
                            val = row.get(primary_price_field)
                            try:
                                price_value = float(val)
                                price_source_field = primary_price_field
                            except (ValueError, TypeError):
                                pass

                        if price_value is None:
                            for backup_field in backup_price_fields:
                                val = row.get(backup_field)
                                if val:
                                    try:
                                        price_value = float(val)
                                        price_source_field = backup_field
                                        break
                                    except (ValueError, TypeError):
                                        pass

                        if price_value is None:
                            records_skipped_missing_price += 1
                            continue

                        # Get timestamp - try all timestamp candidates until one parses
                        valid_timestamp = False
                        parsed_timestamp = None
                        timestamp_candidates = audit_result.get("timestamp_field_candidates", []) if audit_result else []
                        for ts_field in timestamp_candidates:
                            val = row.get(ts_field)
                            if val:
                                try:
                                    parsed_timestamp = datetime.fromisoformat(val.replace("Z", "+00:00"))
                                    valid_timestamp = True
                                    break
                                except ValueError:
                                    pass

                        if not valid_timestamp:
                            records_skipped_invalid_timestamp += 1
                            continue

                        # Get symbol, timeframe, setup
                        symbol = None
                        symbol_candidates = audit_result.get("symbol_field_candidates", []) if audit_result else []
                        for sym_field in symbol_candidates:
                            val = row.get(sym_field)
                            if val:
                                symbol = val
                                break

                        timeframe = None
                        timeframe_candidates = audit_result.get("timeframe_field_candidates", []) if audit_result else []
                        for tf_field in timeframe_candidates:
                            val = row.get(tf_field)
                            if val:
                                timeframe = val
                                break

                        setup = "observation"
                        setup_candidates = audit_result.get("setup_field_candidates", []) if audit_result else []
                        for setup_field in setup_candidates:
                            val = row.get(setup_field)
                            if val:
                                setup = val
                                break

                        # Compute source row hash
                        row_str = json.dumps(row, sort_keys=True)
                        source_row_hash = hashlib.sha256(row_str.encode("utf-8")).hexdigest()[:16]

                        record_id = f"NORM_PRICE_OBS_{uuid.uuid4().hex[:8]}"
                        record = {
                            "record_id": record_id,
                            "source_type": "MARKET_OBSERVATION",
                            "symbol": symbol,
                            "timeframe": timeframe,
                            "setup": setup,
                            "timestamp": parsed_timestamp.isoformat(),
                            "price": price_value,
                            "price_source_field": price_source_field,
                            "observation_only": True,
                            "synthetic_placeholder": False,
                            "source_row_hash": source_row_hash,
                            "status": "COLLECTED",
                            "reason": "Normalized from observation_sample_store",
                        }
                        records.append(record)
                        records_built += 1
            else:
                missing_inputs.append("observation_samples.csv not found")
        elif not mapping_ready:
            missing_inputs.append("mapping_result mapping_ready=false")
        elif not primary_price_field:
            missing_inputs.append("no primary_price_field in mapping_result")
    else:
        missing_inputs.append("mapping_result not provided")

    final_verdict = "PASS"
    if missing_inputs:
        final_verdict = "PARTIAL"
    if not mapping_ready:
        final_verdict = "PARTIAL"
    if records_built == 0 and source_rows_scanned > 0:
        final_verdict = "PARTIAL"

    # Safety checks
    if testnet_submit_allowed or real_submit_allowed:
        final_verdict = "FAIL"
    if submit_attempted or cancel_attempted or flatten_attempted:
        final_verdict = "FAIL"
    if fallback_values_used:
        final_verdict = "FAIL"

    report = {
        "task_id": "T403",
        "phase": "NORMALIZED_PRICE_OBSERVATION_RECORD_BUILD",
        "allowed_mode": allowed_mode,
        "collection_mode": collection_mode,
        "submit_permission": submit_permission,
        "testnet_submit_allowed": testnet_submit_allowed,
        "real_submit_allowed": real_submit_allowed,
        "submit_attempted": submit_attempted,
        "cancel_attempted": cancel_attempted,
        "flatten_attempted": flatten_attempted,
        "mapping_ready": mapping_ready,
        "primary_price_field": primary_price_field,
        "backup_price_fields": backup_price_fields,
        "source_rows_scanned": source_rows_scanned,
        "records_built": records_built,
        "records": records,
        "records_skipped_missing_price": records_skipped_missing_price,
        "records_skipped_invalid_timestamp": records_skipped_invalid_timestamp,
        "fallback_values_used": fallback_values_used,
        "missing_inputs": missing_inputs,
        "final_verdict": final_verdict,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }

    report_json = out_dir / "normalized_price_observation_records.json"
    report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    return report


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build normalized price observation records")
    parser.add_argument("--source-path", default="reports/observation_sample_store/observation_samples.csv")
    parser.add_argument("--output-dir", default="reports/normalized_price_observation_records")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = build_normalized_price_observation_records(
        source_path=args.source_path,
        output_dir=args.output_dir,
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    print(f"task_id={result.get('task_id','')}")
    print(f"final_verdict={result.get('final_verdict','')}")
    print(f"records_built={result.get('records_built',0)}")


if __name__ == "__main__":
    main()
