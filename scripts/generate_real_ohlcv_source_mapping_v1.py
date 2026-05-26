#!/usr/bin/env python3
import argparse
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, List

from core.execution_guards import assert_dry_run_required, normalize_execution_mode


def parse_symbol_and_timeframe_from_path(path: str) -> tuple[Optional[str], Optional[str]]:
    parts = path.split(os.sep)
    try:
        # Look for data/cache/klines/<symbol>/<timeframe>
        for i in range(len(parts)):
            if i + 3 <= len(parts):
                if parts[i] == "data" and parts[i + 1] == "cache" and parts[i + 2] == "klines":
                    symbol = parts[i + 3]
                    timeframe = parts[i + 4]
                    return symbol, timeframe
        return None, None
    except Exception:
        return None, None


def generate_real_ohlcv_source_mapping_v1(
    schema_audit_json_path: Optional[str] = None,
    source_audits: Optional[List[Dict]] = None
) -> Dict:
    mapping_version = "v1"
    schema_audit_ready = False
    selected_source_count = 0
    selected_sources: List[Dict] = []
    fallback_values_used = False
    mapping_ready = False
    unmapped_required_fields: List[str] = []
    mapping_warnings: List[str] = []
    missing_inputs: List[str] = []
    final_verdict = "PASS"

    if not source_audits and not schema_audit_json_path:
        missing_inputs.append("No source audits or schema audit JSON provided")
        final_verdict = "PARTIAL"
    elif schema_audit_json_path and os.path.exists(schema_audit_json_path):
        try:
            with open(schema_audit_json_path, "r") as f:
                schema_audit_result = json.load(f)
                source_audits = schema_audit_result.get("source_audits", [])
                schema_audit_ready = schema_audit_result.get("schema_audit_ready", False)
        except Exception as e:
            mapping_warnings.append(f"Failed to load schema audit JSON: {str(e)}")
            final_verdict = "FAIL"
    elif source_audits:
        # We have source audits provided directly
        pass
    else:
        source_audits = []
        final_verdict = "PARTIAL"

    if source_audits:
        for audit in source_audits:
            path = audit.get("path")
            if not path:
                continue
            has_open = audit.get("has_open", False)
            has_high = audit.get("has_high", False)
            has_low = audit.get("has_low", False)
            has_close = audit.get("has_close", False)
            has_volume = audit.get("has_volume", False)
            columns = audit.get("columns", [])

            # Check if we have all OHLCV columns
            if not (has_open and has_high and has_low and has_close and has_volume):
                continue

            # Try to parse symbol and timeframe from path
            symbol_from_path, timeframe_from_path = parse_symbol_and_timeframe_from_path(path)
            if not symbol_from_path or not timeframe_from_path:
                continue

            # Check if we have a timestamp column
            timestamp_column = None
            for col in columns:
                col_lower = col.lower().strip()
                if col_lower in ["open_time_ms", "open_time", "close_time"]:
                    timestamp_column = col
                    break

            if not timestamp_column:
                continue

            # Okay, we can build mapping!
            selected_source = {
                "source_id": audit.get("source_id", str(uuid.uuid4())),
                "path": path,
                "field_mappings": {
                    "timestamp": timestamp_column,
                    "symbol": "PATH_SYMBOL",
                    "timeframe": "PATH_TIMEFRAME",
                    "open": "open",
                    "high": "high",
                    "low": "low",
                    "close": "close",
                    "volume": "volume"
                },
                "path_derived_fields": {
                    "symbol": symbol_from_path,
                    "timeframe": timeframe_from_path
                },
                "mapping_ready": True,
                "reason": "All required fields available"
            }
            selected_sources.append(selected_source)
            selected_source_count += 1

    if selected_source_count > 0:
        schema_audit_ready = True
        mapping_ready = True
    else:
        final_verdict = "PARTIAL"

    if fallback_values_used:
        final_verdict = "FAIL"

    return {
        "task_id": "T413",
        "phase": "REAL_OHLCV_SOURCE_MAPPING_V1",
        "allowed_mode": "SHADOW_ONLY",
        "collection_mode": "SHADOW_COLLECTION",
        "submit_permission": "NO_SUBMIT",
        "testnet_submit_allowed": False,
        "real_submit_allowed": False,
        "submit_attempted": False,
        "cancel_attempted": False,
        "flatten_attempted": False,
        "mapping_version": mapping_version,
        "schema_audit_ready": schema_audit_ready,
        "selected_source_count": selected_source_count,
        "selected_sources": selected_sources,
        "fallback_values_used": fallback_values_used,
        "mapping_ready": mapping_ready,
        "unmapped_required_fields": unmapped_required_fields,
        "mapping_warnings": mapping_warnings,
        "missing_inputs": missing_inputs,
        "final_verdict": final_verdict,
        "generated_at_utc": datetime.now(timezone.utc).isoformat()
    }


def main():
    mode = normalize_execution_mode(os.environ.get("QQ_RUNTIME_MODE"))
    assert_dry_run_required(mode)

    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--schema-audit-json", type=str, help="Path to T412 schema audit JSON file")
    args = parser.parse_args()

    result = generate_real_ohlcv_source_mapping_v1(
        schema_audit_json_path=args.schema_audit_json
    )

    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(f"Mapping version: {result['mapping_version']}")
        print(f"Selected sources: {result['selected_source_count']}")
        print(f"Mapping ready: {result['mapping_ready']}")
        print(f"Final verdict: {result['final_verdict']}")


if __name__ == "__main__":
    main()
