#!/usr/bin/env python3
import argparse
import csv
import json
import os
import uuid
import hashlib
from datetime import datetime, timezone
from typing import Optional, Dict, List


def parse_symbol_and_timeframe_from_path(path: str) -> tuple[Optional[str], Optional[str]]:
    parts = path.split(os.sep)
    try:
        for i in range(len(parts)):
            if i + 3 <= len(parts):
                if parts[i] == "data" and parts[i + 1] == "cache" and parts[i + 2] == "klines":
                    symbol = parts[i + 3]
                    timeframe = parts[i + 4]
                    return symbol, timeframe
        return None, None
    except Exception:
        return None, None


def build_real_ohlcv_observation_records(
    mapping_json_path: Optional[str] = None,
    selected_sources: Optional[List[Dict]] = None
) -> Dict:
    mapping_ready = False
    source_rows_scanned = 0
    records_built = 0
    records: List[Dict] = []
    records_skipped_missing_ohlcv = 0
    records_skipped_invalid_timestamp = 0
    fallback_values_used = False
    missing_inputs: List[str] = []
    final_verdict = "PASS"

    if not selected_sources and not mapping_json_path:
        missing_inputs.append("No selected sources or mapping JSON provided")
        final_verdict = "PARTIAL"
    elif mapping_json_path and os.path.exists(mapping_json_path):
        try:
            with open(mapping_json_path, "r") as f:
                mapping_result = json.load(f)
                selected_sources = mapping_result.get("selected_sources", [])
                mapping_ready = mapping_result.get("mapping_ready", False)
        except Exception as e:
            final_verdict = "FAIL"
            missing_inputs.append(f"Failed to load mapping JSON: {str(e)}")
    elif selected_sources:
        mapping_ready = len(selected_sources) > 0
    else:
        mapping_ready = False
        final_verdict = "PARTIAL"

    if mapping_ready:
        for source in selected_sources:
            path = source.get("path")
            if not path or not os.path.exists(path):
                continue

            source_id = source.get("source_id")
            field_mappings = source.get("field_mappings", {})
            path_derived_fields = source.get("path_derived_fields", {})
            symbol = path_derived_fields.get("symbol")
            timeframe = path_derived_fields.get("timeframe")

            if not symbol or not timeframe:
                continue

            timestamp_field = field_mappings.get("timestamp")
            open_field = field_mappings.get("open")
            high_field = field_mappings.get("high")
            low_field = field_mappings.get("low")
            close_field = field_mappings.get("close")
            volume_field = field_mappings.get("volume")

            try:
                with open(path, "r", newline="") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        source_rows_scanned += 1
                        row_str = str(sorted(row.items())).encode("utf-8")
                        row_hash = hashlib.md5(row_str).hexdigest()

                        # Try to parse OHLCV
                        try:
                            o = float(row.get(open_field, "nan"))
                            h = float(row.get(high_field, "nan"))
                            l = float(row.get(low_field, "nan"))
                            c = float(row.get(close_field, "nan"))
                            v = float(row.get(volume_field, "nan"))
                        except (ValueError, TypeError):
                            records_skipped_missing_ohlcv += 1
                            continue

                        if any(x != x for x in [o, h, l, c, v]):  # nan check
                            records_skipped_missing_ohlcv += 1
                            continue

                        # Try to parse timestamp
                        ts_str = row.get(timestamp_field)
                        ts_parsed = None
                        try:
                            ts_parsed = float(ts_str)
                            # If it's in seconds, convert to millis, else assume millis
                            if ts_parsed < 1e12:
                                ts_parsed = ts_parsed * 1000
                        except (ValueError, TypeError):
                            records_skipped_invalid_timestamp += 1
                            continue

                        if not ts_parsed:
                            records_skipped_invalid_timestamp += 1
                            continue

                        # Now build the record
                        record = {
                            "record_id": str(uuid.uuid4()),
                            "source_id": source_id,
                            "source_type": "KLINE_CACHE",
                            "symbol": symbol,
                            "timeframe": timeframe,
                            "timestamp": int(ts_parsed),
                            "open": o,
                            "high": h,
                            "low": l,
                            "close": c,
                            "volume": v,
                            "observation_only": True,
                            "synthetic_placeholder": False,
                            "source_row_hash": row_hash,
                            "status": "COLLECTED",
                            "reason": "Successfully built from kline cache"
                        }
                        records.append(record)
                        records_built += 1
            except Exception:
                continue

    if fallback_values_used:
        final_verdict = "FAIL"
    elif not mapping_ready or records_built == 0:
        final_verdict = "PARTIAL"

    return {
        "task_id": "T414",
        "phase": "REAL_OHLCV_OBSERVATION_RECORD_BUILD",
        "allowed_mode": "SHADOW_ONLY",
        "collection_mode": "SHADOW_COLLECTION",
        "submit_permission": "NO_SUBMIT",
        "testnet_submit_allowed": False,
        "real_submit_allowed": False,
        "submit_attempted": False,
        "cancel_attempted": False,
        "flatten_attempted": False,
        "mapping_ready": mapping_ready,
        "source_rows_scanned": source_rows_scanned,
        "records_built": records_built,
        "records": records,
        "records_skipped_missing_ohlcv": records_skipped_missing_ohlcv,
        "records_skipped_invalid_timestamp": records_skipped_invalid_timestamp,
        "fallback_values_used": fallback_values_used,
        "missing_inputs": missing_inputs,
        "final_verdict": final_verdict,
        "generated_at_utc": datetime.now(timezone.utc).isoformat()
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--mapping-json", type=str, help="Path to T413 mapping JSON file")
    args = parser.parse_args()

    result = build_real_ohlcv_observation_records(
        mapping_json_path=args.mapping_json
    )

    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(f"Mapping ready: {result['mapping_ready']}")
        print(f"Source rows scanned: {result['source_rows_scanned']}")
        print(f"Records built: {result['records_built']}")
        print(f"Final verdict: {result['final_verdict']}")


if __name__ == "__main__":
    main()
