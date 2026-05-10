from __future__ import annotations

import argparse
import csv
import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def build_trusted_price_observation_records(
    audit_result_t401: dict[str, Any] | None = None,
    audit_result_t406: dict[str, Any] | None = None,
    mapping_result_t402: dict[str, Any] | None = None,
    policy_result_t407: dict[str, Any] | None = None,
    build_result_t403: dict[str, Any] | None = None,
    source_path: str = "reports/observation_sample_store/observation_samples.csv",
    output_dir: str = "reports/trusted_price_observation_records",
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

    policy_ready = False
    auxiliary_allowed_fields = []
    trust_assessments_by_field = {}
    source_records_analyzed = 0
    trusted_auxiliary_records_built = 0
    gap_closure_records_built = 0
    records = []
    records_skipped_by_policy = 0
    fallback_values_used = False
    missing_inputs = []

    if policy_result_t407:
        policy_ready = policy_result_t407.get("policy_ready", False)
        auxiliary_allowed_fields = policy_result_t407.get("auxiliary_allowed_fields", [])
    else:
        missing_inputs.append("policy_result_t407 not provided")

    if audit_result_t406:
        field_trust_assessments = audit_result_t406.get("field_trust_assessments", [])
        for assessment in field_trust_assessments:
            field = assessment.get("field")
            if field:
                trust_assessments_by_field[field] = assessment
    else:
        missing_inputs.append("audit_result_t406 not provided")

    if policy_ready and source_path:
        source_path_obj = Path(source_path)
        if source_path_obj.exists():
            with open(source_path_obj, newline="", encoding="utf-8") as csvfile:
                reader = csv.DictReader(csvfile)

                for row in reader:
                    source_records_analyzed += 1

                    # Try to get price from allowed auxiliary fields
                    price_value = None
                    price_field = None
                    trust_level = "LOW"

                    for field in auxiliary_allowed_fields:
                        val = row.get(field)
                        if val:
                            try:
                                price_value = float(val)
                                price_field = field
                                assessment = trust_assessments_by_field.get(field, {})
                                trust_level = assessment.get("trust_level", "LOW")
                                break
                            except (ValueError, TypeError):
                                pass

                    if price_value is None:
                        records_skipped_by_policy += 1
                        continue

                    # Get timestamp - try all timestamp candidates
                    valid_timestamp = False
                    parsed_timestamp = None
                    timestamp_candidates = audit_result_t401.get("timestamp_field_candidates", []) if audit_result_t401 else []
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
                        records_skipped_by_policy += 1
                        continue

                    # Get symbol, timeframe, setup
                    symbol = None
                    symbol_candidates = audit_result_t401.get("symbol_field_candidates", []) if audit_result_t401 else []
                    for sym_field in symbol_candidates:
                        val = row.get(sym_field)
                        if val:
                            symbol = val
                            break

                    timeframe = None
                    timeframe_candidates = audit_result_t401.get("timeframe_field_candidates", []) if audit_result_t401 else []
                    for tf_field in timeframe_candidates:
                        val = row.get(tf_field)
                        if val:
                            timeframe = val
                            break

                    setup = "observation"
                    setup_candidates = audit_result_t401.get("setup_field_candidates", []) if audit_result_t401 else []
                    for setup_field in setup_candidates:
                        val = row.get(setup_field)
                        if val:
                            setup = val
                            break

                    # Compute source row hash
                    row_str = json.dumps(row, sort_keys=True)
                    source_row_hash = hashlib.sha256(row_str.encode("utf-8")).hexdigest()[:16]

                    record_id = f"TRUSTED_PRICE_OBS_{uuid.uuid4().hex[:8]}"
                    record = {
                        "record_id": record_id,
                        "source_type": "MARKET_OBSERVATION",
                        "symbol": symbol,
                        "timeframe": timeframe,
                        "setup": setup,
                        "timestamp": parsed_timestamp.isoformat(),
                        "normalized_price": price_value,
                        "price_field": price_field,
                        "trust_level": trust_level,
                        "auxiliary_only": True,
                        "valid_for_gap_closure": False,
                        "observation_only": True,
                        "synthetic_placeholder": False,
                        "status": "AUXILIARY_ONLY",
                        "reason": "Allowed by trust policy for auxiliary analysis only",
                    }
                    records.append(record)
                    trusted_auxiliary_records_built += 1
        else:
            missing_inputs.append("observation_samples.csv not found")

    final_verdict = "PASS"
    if missing_inputs:
        final_verdict = "PARTIAL"
    if not policy_ready:
        final_verdict = "PARTIAL"
    if trusted_auxiliary_records_built == 0 and source_records_analyzed > 0:
        final_verdict = "PARTIAL"

    if testnet_submit_allowed or real_submit_allowed:
        final_verdict = "FAIL"
    if submit_attempted or cancel_attempted or flatten_attempted:
        final_verdict = "FAIL"
    if fallback_values_used:
        final_verdict = "FAIL"
    if gap_closure_records_built > 0:
        final_verdict = "FAIL"

    report = {
        "task_id": "T408",
        "phase": "TRUSTED_PRICE_OBSERVATION_RECORD_BUILD",
        "allowed_mode": allowed_mode,
        "collection_mode": collection_mode,
        "submit_permission": submit_permission,
        "testnet_submit_allowed": testnet_submit_allowed,
        "real_submit_allowed": real_submit_allowed,
        "submit_attempted": submit_attempted,
        "cancel_attempted": cancel_attempted,
        "flatten_attempted": flatten_attempted,
        "policy_ready": policy_ready,
        "source_records_analyzed": source_records_analyzed,
        "trusted_auxiliary_records_built": trusted_auxiliary_records_built,
        "gap_closure_records_built": gap_closure_records_built,
        "records": records,
        "records_skipped_by_policy": records_skipped_by_policy,
        "fallback_values_used": fallback_values_used,
        "missing_inputs": missing_inputs,
        "final_verdict": final_verdict,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }

    report_json = out_dir / "trusted_price_observation_records.json"
    report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    return report


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build trusted price observation records")
    parser.add_argument("--source-path", default="reports/observation_sample_store/observation_samples.csv")
    parser.add_argument("--output-dir", default="reports/trusted_price_observation_records")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = build_trusted_price_observation_records(
        source_path=args.source_path,
        output_dir=args.output_dir,
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    print(f"task_id={result.get('task_id','')}")
    print(f"final_verdict={result.get('final_verdict','')}")
    print(f"trusted_auxiliary_records_built={result.get('trusted_auxiliary_records_built',0)}")


if __name__ == "__main__":
    main()
