from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def generate_observation_field_mapping_v1(
    audit_result: dict[str, Any] | None = None,
    output_dir: str = "reports/observation_field_mapping_v1",
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

    mapping_version = "v1"
    source_schema_ready = False
    field_mappings = {
        "timestamp": None,
        "symbol": None,
        "timeframe": None,
        "setup": None,
        "open": None,
        "high": None,
        "low": None,
        "close": None,
        "volume": None,
    }
    mapped_required_field_count = 0
    mapped_ohlcv_field_count = 0
    fallback_values_used = False
    mapping_ready = False
    unmapped_required_fields = []
    mapping_warnings = []
    missing_inputs = []

    if audit_result:
        source_schema_ready = audit_result.get("schema_ready_for_mapping", False)
        columns = audit_result.get("columns", [])

        # Map fields (case-insensitive)
        field_aliases = {
            "timestamp": ["timestamp", "created_at", "time"],
            "symbol": ["symbol", "pair"],
            "timeframe": ["timeframe", "interval", "tf"],
            "setup": ["setup", "strategy_key", "strategy"],
            "open": ["open", "o"],
            "high": ["high", "h"],
            "low": ["low", "l"],
            "close": ["close", "c"],
            "volume": ["volume", "vol", "v"],
        }

        for target_field, aliases in field_aliases.items():
            for alias in aliases:
                for col in columns:
                    if col.lower() == alias.lower():
                        field_mappings[target_field] = col
                        break
                if field_mappings[target_field]:
                    break

        # Count mapped fields
        required_base_fields = ["timestamp", "symbol", "timeframe", "setup"]
        ohlcv_fields = ["open", "high", "low", "close", "volume"]

        mapped_required_field_count = sum(1 for f in required_base_fields if field_mappings[f])
        mapped_ohlcv_field_count = sum(1 for f in ohlcv_fields if field_mappings[f])

        # Check unmapped required fields
        unmapped_required_fields = []
        for f in required_base_fields + ohlcv_fields:
            if not field_mappings[f]:
                unmapped_required_fields.append(f)

        mapping_ready = (
            source_schema_ready and
            mapped_required_field_count == len(required_base_fields) and
            mapped_ohlcv_field_count == len(ohlcv_fields) and
            not fallback_values_used
        )

        if not source_schema_ready:
            mapping_warnings.append("Source schema not ready for mapping")
        if unmapped_required_fields:
            mapping_warnings.append(f"Unmapped required fields: {unmapped_required_fields}")
    else:
        missing_inputs.append("audit_result not provided")

    final_verdict = "PASS"
    if missing_inputs:
        final_verdict = "PARTIAL"
    if not mapping_ready:
        final_verdict = "PARTIAL"

    # Safety checks
    if testnet_submit_allowed or real_submit_allowed:
        final_verdict = "FAIL"
    if submit_attempted or cancel_attempted or flatten_attempted:
        final_verdict = "FAIL"

    report = {
        "task_id": "T397",
        "phase": "OBSERVATION_FIELD_MAPPING_V1",
        "allowed_mode": allowed_mode,
        "collection_mode": collection_mode,
        "submit_permission": submit_permission,
        "testnet_submit_allowed": testnet_submit_allowed,
        "real_submit_allowed": real_submit_allowed,
        "submit_attempted": submit_attempted,
        "cancel_attempted": cancel_attempted,
        "flatten_attempted": flatten_attempted,
        "mapping_version": mapping_version,
        "source_schema_ready": source_schema_ready,
        "field_mappings": field_mappings,
        "mapped_required_field_count": mapped_required_field_count,
        "mapped_ohlcv_field_count": mapped_ohlcv_field_count,
        "fallback_values_used": fallback_values_used,
        "mapping_ready": mapping_ready,
        "unmapped_required_fields": unmapped_required_fields,
        "mapping_warnings": mapping_warnings,
        "missing_inputs": missing_inputs,
        "final_verdict": final_verdict,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }

    report_json = out_dir / "observation_field_mapping_v1.json"
    report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    return report


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate observation field mapping v1")
    parser.add_argument("--output-dir", default="reports/observation_field_mapping_v1")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = generate_observation_field_mapping_v1(
        output_dir=args.output_dir,
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    print(f"task_id={result.get('task_id','')}")
    print(f"final_verdict={result.get('final_verdict','')}")
    print(f"mapping_ready={result.get('mapping_ready',False)}")


if __name__ == "__main__":
    main()
