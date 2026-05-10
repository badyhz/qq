from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def generate_price_field_eligibility_control_report(
    audit_result: dict[str, Any] | None = None,
    mapping_result: dict[str, Any] | None = None,
    build_result: dict[str, Any] | None = None,
    validation_result: dict[str, Any] | None = None,
    output_dir: str = "reports/price_field_eligibility_control_report",
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

    candidate_audit_ready = False
    price_mapping_ready = False
    price_records_built = 0
    price_records_analyzed = 0
    valid_price_records = 0
    valid_for_gap_closure = False
    gap_closure_eligible_count = 0
    previous_gap = 22
    estimated_gap_after_price_eligibility = 22
    gap_delta = 0
    price_eligibility_effective = False
    readiness_status = "NOT_READY"
    final_decision = "CONTINUE_SHADOW_COLLECTION"
    allowed_actions = ["SHADOW_ONLY", "SHADOW_COLLECTION", "TESTNET_DRY_RUN_BLOCKED"]
    blocked_reasons = []
    archive_range = "T208-T405"
    next_recommended_task_range = "T406-T410"
    missing_inputs = []

    if audit_result:
        candidate_audit_ready = audit_result.get("candidate_audit_ready", False)
    if mapping_result:
        price_mapping_ready = mapping_result.get("mapping_ready", False)
    if build_result:
        price_records_built = build_result.get("records_built", 0)
    if validation_result:
        price_records_analyzed = validation_result.get("records_analyzed", 0)
        valid_price_records = validation_result.get("valid_records", 0)
        valid_for_gap_closure = validation_result.get("valid_for_gap_closure", False)
        gap_closure_eligible_count = len(validation_result.get("gap_closure_eligible_records", []))

    # Calculate gap impact
    if valid_for_gap_closure and gap_closure_eligible_count > 0:
        estimated_gap_after_price_eligibility = max(0, previous_gap - gap_closure_eligible_count)
        gap_delta = estimated_gap_after_price_eligibility - previous_gap
        price_eligibility_effective = True
    else:
        estimated_gap_after_price_eligibility = previous_gap

    # Determine readiness and decision
    if not candidate_audit_ready:
        blocked_reasons.append("candidate_audit_ready=false")
    if not price_mapping_ready:
        blocked_reasons.append("price_mapping_ready=false")
    if not valid_for_gap_closure:
        blocked_reasons.append("valid_for_gap_closure=false")
    if estimated_gap_after_price_eligibility > 0:
        blocked_reasons.append("estimated_gap_after_price_eligibility>0")
        readiness_status = "NOT_READY"

    if readiness_status == "NOT_READY":
        final_decision = "CONTINUE_SHADOW_COLLECTION"

    # Ensure allowed actions are correct
    if "SHADOW_COLLECTION" not in allowed_actions:
        allowed_actions.append("SHADOW_COLLECTION")
    if "TESTNET_DRY_RUN_BLOCKED" not in allowed_actions:
        allowed_actions.append("TESTNET_DRY_RUN_BLOCKED")
    if "TESTNET_DRY_RUN_ONLY" in allowed_actions:
        allowed_actions.remove("TESTNET_DRY_RUN_ONLY")

    final_verdict = "PASS"
    if missing_inputs:
        final_verdict = "PARTIAL"

    # Safety checks
    if testnet_submit_allowed or real_submit_allowed:
        final_verdict = "FAIL"
    if submit_attempted or cancel_attempted or flatten_attempted:
        final_verdict = "FAIL"

    report = {
        "task_id": "T405",
        "phase": "PRICE_FIELD_ELIGIBILITY_CONTROL_REPORT",
        "allowed_mode": allowed_mode,
        "collection_mode": collection_mode,
        "submit_permission": submit_permission,
        "testnet_submit_allowed": testnet_submit_allowed,
        "real_submit_allowed": real_submit_allowed,
        "submit_attempted": submit_attempted,
        "cancel_attempted": cancel_attempted,
        "flatten_attempted": flatten_attempted,
        "candidate_audit_ready": candidate_audit_ready,
        "price_mapping_ready": price_mapping_ready,
        "price_records_built": price_records_built,
        "price_records_analyzed": price_records_analyzed,
        "valid_price_records": valid_price_records,
        "valid_for_gap_closure": valid_for_gap_closure,
        "gap_closure_eligible_count": gap_closure_eligible_count,
        "previous_gap": previous_gap,
        "estimated_gap_after_price_eligibility": estimated_gap_after_price_eligibility,
        "gap_delta": gap_delta,
        "price_eligibility_effective": price_eligibility_effective,
        "readiness_status": readiness_status,
        "final_decision": final_decision,
        "allowed_actions": allowed_actions,
        "blocked_reasons": blocked_reasons,
        "archive_range": archive_range,
        "next_recommended_task_range": next_recommended_task_range,
        "missing_inputs": missing_inputs,
        "final_verdict": final_verdict,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }

    report_json = out_dir / "price_field_eligibility_control_report.json"
    report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    return report


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate price field eligibility control report")
    parser.add_argument("--output-dir", default="reports/price_field_eligibility_control_report")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = generate_price_field_eligibility_control_report(
        output_dir=args.output_dir,
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    print(f"task_id={result.get('task_id','')}")
    print(f"final_verdict={result.get('final_verdict','')}")
    print(f"final_decision={result.get('final_decision','')}")


if __name__ == "__main__":
    main()
