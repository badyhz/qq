#!/usr/bin/env python3
import argparse
import csv
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, List, Tuple

from core.execution_guards import assert_dry_run_required, normalize_execution_mode


def audit_single_source(source_path: str) -> Dict:
    row_count = 0
    columns = []
    has_timestamp = False
    has_symbol = False
    has_timeframe = False
    has_open = False
    has_high = False
    has_low = False
    has_close = False
    has_volume = False
    ohlcv_complete_records = 0
    timestamp_parseable_records = 0
    schema_ready = False
    reason = ""
    
    file_type = os.path.splitext(source_path)[1].lower()
    
    if file_type == ".csv":
        try:
            with open(source_path, "r") as f:
                reader = csv.DictReader(f)
                if reader.fieldnames:
                    columns = reader.fieldnames
                    col_set = {c.lower().strip() for c in columns}
                    has_timestamp = any(alias in col_set for alias in ["timestamp", "time", "ts", "open_time"])
                    has_symbol = any(alias in col_set for alias in ["symbol", "pair", "s"])
                    has_timeframe = any(alias in col_set for alias in ["timeframe", "interval", "tf"])
                    has_open = any(alias in col_set for alias in ["open", "o"])
                    has_high = any(alias in col_set for alias in ["high", "h"])
                    has_low = any(alias in col_set for alias in ["low", "l"])
                    has_close = any(alias in col_set for alias in ["close", "c"])
                    has_volume = any(alias in col_set for alias in ["volume", "vol", "v", "quote_volume"])
                    
                    # Find the actual column names to use for checking
                    timestamp_col = None
                    open_col = None
                    high_col = None
                    low_col = None
                    close_col = None
                    volume_col = None
                    
                    for col in columns:
                        lower_col = col.lower().strip()
                        if not timestamp_col and lower_col in ["timestamp", "time", "ts", "open_time"]:
                            timestamp_col = col
                        if not open_col and lower_col in ["open", "o"]:
                            open_col = col
                        if not high_col and lower_col in ["high", "h"]:
                            high_col = col
                        if not low_col and lower_col in ["low", "l"]:
                            low_col = col
                        if not close_col and lower_col in ["close", "c"]:
                            close_col = col
                        if not volume_col and lower_col in ["volume", "vol", "v", "quote_volume"]:
                            volume_col = col
                    
                    # Now check rows (streaming, no full load)
                    for row in reader:
                        row_count += 1
                        try:
                            # Check parseable timestamp
                            if timestamp_col and row[timestamp_col]:
                                try:
                                    float(row[timestamp_col])
                                    timestamp_parseable_records += 1
                                except (ValueError, TypeError):
                                    pass
                            
                            # Check OHLCV complete
                            if (open_col and row[open_col] and 
                                high_col and row[high_col] and 
                                low_col and row[low_col] and 
                                close_col and row[close_col] and 
                                volume_col and row[volume_col]):
                                ohlcv_complete_records += 1
                        except Exception:
                            continue
            
            # Determine schema readiness
            if not (has_timestamp and has_symbol and has_timeframe and has_open and has_high and has_low and has_close and has_volume):
                reason = "Missing required columns: "
                missing = []
                if not has_timestamp: missing.append("timestamp")
                if not has_symbol: missing.append("symbol")
                if not has_timeframe: missing.append("timeframe")
                if not has_open: missing.append("open")
                if not has_high: missing.append("high")
                if not has_low: missing.append("low")
                if not has_close: missing.append("close")
                if not has_volume: missing.append("volume")
                reason += ", ".join(missing)
            elif ohlcv_complete_records == 0:
                reason = "No OHLCV-complete records found"
            elif timestamp_parseable_records == 0:
                reason = "No parseable timestamps found"
            else:
                schema_ready = True
                reason = "Schema audit passed"
                
        except FileNotFoundError:
            reason = f"File not found: {source_path}"
        except Exception as e:
            reason = f"Error reading file: {str(e)}"
    
    return {
        "source_id": str(uuid.uuid4()),
        "path": source_path,
        "row_count": row_count,
        "columns": columns,
        "has_timestamp": has_timestamp,
        "has_symbol": has_symbol,
        "has_timeframe": has_timeframe,
        "has_open": has_open,
        "has_high": has_high,
        "has_low": has_low,
        "has_close": has_close,
        "has_volume": has_volume,
        "ohlcv_complete_records": ohlcv_complete_records,
        "timestamp_parseable_records": timestamp_parseable_records,
        "schema_ready": schema_ready,
        "reason": reason
    }


def audit_real_ohlcv_source_schema(discovery_json_path: Optional[str] = None, candidate_sources: Optional[List[Dict]] = None) -> Dict:
    source_audits: List[Dict] = []
    candidate_source_count = 0
    audited_source_count = 0
    ohlcv_ready_source_count = 0
    schema_audit_ready = False
    missing_inputs = []
    audit_warnings = []
    final_verdict = "PASS"
    
    # Get candidate sources
    if not candidate_sources and not discovery_json_path:
        missing_inputs.append("No candidate sources or discovery JSON provided")
        final_verdict = "PARTIAL"
    elif discovery_json_path and os.path.exists(discovery_json_path):
        try:
            with open(discovery_json_path, "r") as f:
                discovery_data = json.load(f)
                candidate_sources = discovery_data.get("candidate_sources", [])
                candidate_source_count = discovery_data.get("candidate_source_count", 0)
        except Exception as e:
            audit_warnings.append(f"Failed to read discovery JSON: {str(e)}")
            candidate_source_count = 0
    elif candidate_sources:
        candidate_source_count = len(candidate_sources)
    else:
        candidate_source_count = 0
    
    # Perform audits
    for source in candidate_sources or []:
        source_path = source.get("path")
        if source_path and os.path.exists(source_path):
            audit = audit_single_source(source_path)
            # Use source_id from candidate if available
            if "source_id" in source:
                audit["source_id"] = source["source_id"]
            source_audits.append(audit)
            audited_source_count += 1
            if audit["schema_ready"]:
                ohlcv_ready_source_count += 1
    
    # Determine schema audit readiness
    schema_audit_ready = ohlcv_ready_source_count > 0
    
    # Determine final verdict
    if not audit_warnings and candidate_source_count == 0:
        final_verdict = "PARTIAL"
    elif audit_warnings:
        final_verdict = "FAIL"
    elif ohlcv_ready_source_count > 0:
        final_verdict = "PASS"
    else:
        final_verdict = "PARTIAL"
    
    return {
        "task_id": "T412",
        "phase": "REAL_OHLCV_SOURCE_SCHEMA_AUDIT",
        "allowed_mode": "SHADOW_ONLY",
        "collection_mode": "SHADOW_COLLECTION",
        "submit_permission": "NO_SUBMIT",
        "testnet_submit_allowed": False,
        "real_submit_allowed": False,
        "submit_attempted": False,
        "cancel_attempted": False,
        "flatten_attempted": False,
        "candidate_source_count": candidate_source_count,
        "audited_source_count": audited_source_count,
        "ohlcv_ready_source_count": ohlcv_ready_source_count,
        "source_audits": source_audits,
        "schema_audit_ready": schema_audit_ready,
        "missing_inputs": missing_inputs,
        "audit_warnings": audit_warnings,
        "final_verdict": final_verdict,
        "generated_at_utc": datetime.now(timezone.utc).isoformat()
    }


def main():
    mode = normalize_execution_mode(os.environ.get("QQ_RUNTIME_MODE"))
    assert_dry_run_required(mode)

    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--discovery-json", type=str, help="Path to T411 discovery JSON file")
    args = parser.parse_args()
    
    result = audit_real_ohlcv_source_schema(discovery_json_path=args.discovery_json)
    
    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(f"Audited {result['audited_source_count']} sources")
        print(f"OHLCV-ready sources: {result['ohlcv_ready_source_count']}")
        print(f"Schema audit ready: {result['schema_audit_ready']}")
        print(f"Final verdict: {result['final_verdict']}")


if __name__ == "__main__":
    main()
