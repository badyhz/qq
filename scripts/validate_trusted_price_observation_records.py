from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def validate_trusted_price_observation_records(
    build_result_t408: dict[str, Any] | None = None,
    policy_result_t407: dict[str, Any] | None = None,
    output_dir: str = "reports/trusted_price_observation_validation",
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
    valid_auxiliary_records = 0
    invalid_records = 0
    gap_closure_records = 0
    placeholder_records = 0
    fallback_values_detected = False
    explicit_policy_allows_price_only = False
    requires_full_ohlcv_for_gap_closure = True
    valid_for_auxiliary_analysis = False
    valid_for_gap_closure = False
    gap_closure_eligible_records = []
    validation_warnings = []
    missing_inputs = []

    if policy_result_t407:
        explicit_policy_allows_price_only = policy_result_t407.get("explicit_policy_allows_price_only", False)
        requires_full_ohlcv_for_gap_closure = policy_result_t407.get("requires_full_ohlcv_for_gap_closure", True)
    else:
        missing_inputs.append("policy_result_t407 not provided")

    if build_result_t408:
        input_records = build_result_t408.get("records", [])
        records_analyzed = len(input_records)

        for record in input_records:
            is_valid = True
            record_id = record.get("record_id", "")
            auxiliary_only = record.get("auxiliary_only", False)
            valid_for_gap = record.get("valid_for_gap_closure", False)
            synthetic_placeholder = record.get("synthetic_placeholder", True)
            observation_only = record.get("observation_only", False)

            if not auxiliary_only:
                invalid_records += 1
                is_valid = False

            if valid_for_gap:
                gap_closure_records += 1
                invalid_records += 1
                is_valid = False

            if synthetic_placeholder:
                placeholder_records += 1
                invalid_records += 1
                is_valid = False

            if not observation_only:
                invalid_records += 1
                is_valid = False

            if is_valid:
                valid_auxiliary_records += 1

        if valid_auxiliary_records > 0 and invalid_records == 0:
            valid_for_auxiliary_analysis = True
    else:
        missing_inputs.append("build_result_t408 not provided")

    final_verdict = "PASS"
    if missing_inputs:
        final_verdict = "PARTIAL"
    if records_analyzed == 0:
        final_verdict = "PARTIAL"
    if invalid_records > 0:
        final_verdict = "PARTIAL"

    if testnet_submit_allowed or real_submit_allowed:
        final_verdict = "FAIL"
    if submit_attempted or cancel_attempted or flatten_attempted:
        final_verdict = "FAIL"
    if fallback_values_detected:
        final_verdict = "FAIL"
    if explicit_policy_allows_price_only:
        final_verdict = "FAIL"
    if not requires_full_ohlcv_for_gap_closure:
        final_verdict = "FAIL"
    if valid_for_gap_closure:
        final_verdict = "FAIL"
    if gap_closure_records > 0:
        final_verdict = "FAIL"

    report = {
        "task_id": "T409",
        "phase": "TRUSTED_PRICE_OBSERVATION_VALIDATION",
        "allowed_mode": allowed_mode,
        "collection_mode": collection_mode,
        "submit_permission": submit_permission,
        "testnet_submit_allowed": testnet_submit_allowed,
        "real_submit_allowed": real_submit_allowed,
        "submit_attempted": submit_attempted,
        "cancel_attempted": cancel_attempted,
        "flatten_attempted": flatten_attempted,
        "records_analyzed": records_analyzed,
        "valid_auxiliary_records": valid_auxiliary_records,
        "invalid_records": invalid_records,
        "gap_closure_records": gap_closure_records,
        "placeholder_records": placeholder_records,
        "fallback_values_detected": fallback_values_detected,
        "explicit_policy_allows_price_only": explicit_policy_allows_price_only,
        "requires_full_ohlcv_for_gap_closure": requires_full_ohlcv_for_gap_closure,
        "valid_for_auxiliary_analysis": valid_for_auxiliary_analysis,
        "valid_for_gap_closure": valid_for_gap_closure,
        "gap_closure_eligible_records": gap_closure_eligible_records,
        "validation_warnings": validation_warnings,
        "missing_inputs": missing_inputs,
        "final_verdict": final_verdict,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }

    report_json = out_dir / "trusted_price_observation_validation.json"
    report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    return report


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate trusted price observation records")
    parser.add_argument("--output-dir", default="reports/trusted_price_observation_validation")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = validate_trusted_price_observation_records(
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
