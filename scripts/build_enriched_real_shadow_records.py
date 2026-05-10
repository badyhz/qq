from __future__ import annotations

import argparse
import csv
import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def build_enriched_real_shadow_records(
    audit_result: dict[str, Any] | None = None,
    mapping_result: dict[str, Any] | None = None,
    source_path: str = "reports/observation_sample_store/observation_samples.csv",
    output_dir: str = "reports/enriched_real_shadow_records",
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
    records_skipped_missing_ohlcv = 0
    records_skipped_invalid_timestamp = 0
    fallback_values_used = False
    missing_inputs = []

    if mapping_result:
        mapping_ready = mapping_result.get("mapping_ready", False)
        field_mappings = mapping_result.get("field_mappings", {})

        if mapping_ready:
            source_path_obj = Path(source_path)
            if source_path_obj.exists():
                with open(source_path_obj, newline="", encoding="utf-8") as csvfile:
                    reader = csv.DictReader(csvfile)

                    for row in reader:
                        source_rows_scanned += 1

                        # Get mapped values
                        timestamp_str = row.get(field_mappings.get("timestamp"))
                        symbol = row.get(field_mappings.get("symbol"))
                        timeframe = row.get(field_mappings.get("timeframe"))
                        setup = row.get(field_mappings.get("setup"))
                        open_val = row.get(field_mappings.get("open"))
                        high_val = row.get(field_mappings.get("high"))
                        low_val = row.get(field_mappings.get("low"))
                        close_val = row.get(field_mappings.get("close"))
                        volume_val = row.get(field_mappings.get("volume"))

                        # Check for missing OHLCV
                        ohlcv_missing = False
                        ohlcv_values = [open_val, high_val, low_val, close_val, volume_val]
                        for val in ohlcv_values:
                            if val is None or val == "":
                                ohlcv_missing = True
                                break

                        if ohlcv_missing:
                            records_skipped_missing_ohlcv += 1
                            continue

                        # Parse timestamp
                        valid_timestamp = False
                        parsed_timestamp = None
                        if timestamp_str:
                            try:
                                parsed_timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                                valid_timestamp = True
                            except ValueError:
                                pass

                        if not valid_timestamp:
                            records_skipped_invalid_timestamp += 1
                            continue

                        # Parse OHLCV
                        try:
                            open_float = float(open_val)
                            high_float = float(high_val)
                            low_float = float(low_val)
                            close_float = float(close_val)
                            volume_float = float(volume_val)
                        except (ValueError, TypeError):
                            records_skipped_missing_ohlcv += 1
                            continue

                        # Compute source row hash
                        row_str = json.dumps(row, sort_keys=True)
                        source_row_hash = hashlib.sha256(row_str.encode("utf-8")).hexdigest()[:16]

                        record_id = f"ENRICHED_REAL_OBS_{uuid.uuid4().hex[:8]}"
                        record = {
                            "record_id": record_id,
                            "source_type": "MARKET_OBSERVATION",
                            "symbol": symbol,
                            "timeframe": timeframe,
                            "setup": setup or "observation",
                            "timestamp": parsed_timestamp.isoformat(),
                            "open": open_float,
                            "high": high_float,
                            "low": low_float,
                            "close": close_float,
                            "volume": volume_float,
                            "observation_only": True,
                            "synthetic_placeholder": False,
                            "source_row_hash": source_row_hash,
                            "status": "COLLECTED",
                            "reason": "Enriched from observation_sample_store",
                        }
                        records.append(record)
                        records_built += 1
            else:
                missing_inputs.append("observation_samples.csv not found")
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
        "task_id": "T398",
        "phase": "ENRICHED_REAL_SHADOW_RECORD_BUILD",
        "allowed_mode": allowed_mode,
        "collection_mode": collection_mode,
        "submit_permission": submit_permission,
        "testnet_submit_allowed": testnet_submit_allowed,
        "real_submit_allowed": real_submit_allowed,
        "submit_attempted": submit_attempted,
        "cancel_attempted": cancel_attempted,
        "flatten_attempted": flatten_attempted,
        "mapping_ready": mapping_ready,
        "source_rows_scanned": source_rows_scanned,
        "records_built": records_built,
        "records": records,
        "records_skipped_missing_ohlcv": records_skipped_missing_ohlcv,
        "records_skipped_invalid_timestamp": records_skipped_invalid_timestamp,
        "fallback_values_used": fallback_values_used,
        "missing_inputs": missing_inputs,
        "final_verdict": final_verdict,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }

    report_json = out_dir / "enriched_real_shadow_records.json"
    report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    return report


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build enriched real shadow records")
    parser.add_argument("--source-path", default="reports/observation_sample_store/observation_samples.csv")
    parser.add_argument("--output-dir", default="reports/enriched_real_shadow_records")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = build_enriched_real_shadow_records(
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
