from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def generate_price_field_trust_control_report(
    audit_result_t406: dict[str, Any] | None = None,
    policy_result_t407: dict[str, Any] | None = None,
    build_result_t408: dict[str, Any] | None = None,
    validation_result_t409: dict[str, Any] | None = None,
    output_dir: str = "reports/price_field_trust_control_report",
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

    high_trust_field_count = 0
    auxiliary_field_count = 0
    gap_closure_field_count = 0
    trusted_auxiliary_records_built = 0
    gap_closure_records_built = 0
    valid_for_auxiliary_analysis = False
    valid_for_gap_closure = False
    previous_gap = 22
    estimated_gap_after_trust_check = 22
    gap_delta = 0
    price_field_auxiliary_effective = False
    readiness_status = "NOT_READY"
    final_decision = "CONTINUE_SHADOW_COLLECTION"
    allowed_actions = ["SHADOW_ONLY", "SHADOW_COLLECTION", "TESTNET_DRY_RUN_BLOCKED"]
    blocked_reasons = []
    archive_range = "T208-T410"
    next_recommended_task_range = "T411-T415"
    missing_inputs = []

    if audit_result_t406:
        high_trust_field_count = audit_result_t406.get("high_trust_field_count", 0)
        auxiliary_field_count = audit_result_t406.get("auxiliary_field_count", 0)
        gap_closure_field_count = audit_result_t406.get("gap_closure_field_count", 0)
    else:
        missing_inputs.append("audit_result_t406 not provided")

    if build_result_t408:
        trusted_auxiliary_records_built = build_result_t408.get("trusted_auxiliary_records_built", 0)
        gap_closure_records_built = build_result_t408.get("gap_closure_records_built", 0)
    else:
        missing_inputs.append("build_result_t408 not provided")

    if validation_result_t409:
        valid_for_auxiliary_analysis = validation_result_t409.get("valid_for_auxiliary_analysis", False)
        valid_for_gap_closure = validation_result_t409.get("valid_for_gap_closure", False)
    else:
        missing_inputs.append("validation_result_t409 not provided")

    if auxiliary_field_count > 0 and trusted_auxiliary_records_built > 0:
        price_field_auxiliary_effective = True

    if not valid_for_auxiliary_analysis:
        blocked_reasons.append("valid_for_auxiliary_analysis=false")
    if valid_for_gap_closure:
        blocked_reasons.append("valid_for_gap_closure=true - NOT ALLOWED")
    if gap_closure_field_count > 0:
        blocked_reasons.append("gap_closure_field_count>0 - NOT ALLOWED")
    if gap_closure_records_built > 0:
        blocked_reasons.append("gap_closure_records_built>0 - NOT ALLOWED")
    if estimated_gap_after_trust_check > 0:
        blocked_reasons.append("estimated_gap_after_trust_check>0")
        readiness_status = "NOT_READY"

    if readiness_status == "NOT_READY":
        final_decision = "CONTINUE_SHADOW_COLLECTION"

    if "SHADOW_COLLECTION" not in allowed_actions:
        allowed_actions.append("SHADOW_COLLECTION")
    if "TESTNET_DRY_RUN_BLOCKED" not in allowed_actions:
        allowed_actions.append("TESTNET_DRY_RUN_BLOCKED")
    if "TESTNET_DRY_RUN_ONLY" in allowed_actions:
        allowed_actions.remove("TESTNET_DRY_RUN_ONLY")

    final_verdict = "PASS"
    if missing_inputs:
        final_verdict = "PARTIAL"

    if testnet_submit_allowed or real_submit_allowed:
        final_verdict = "FAIL"
    if submit_attempted or cancel_attempted or flatten_attempted:
        final_verdict = "FAIL"
    if valid_for_gap_closure:
        final_verdict = "FAIL"
    if estimated_gap_after_trust_check != previous_gap:
        final_verdict = "FAIL"
    if readiness_status != "NOT_READY":
        final_verdict = "FAIL"
    if "TESTNET_DRY_RUN_ONLY" in allowed_actions:
        final_verdict = "FAIL"

    report = {
        "task_id": "T410",
        "phase": "PRICE_FIELD_TRUST_CONTROL_REPORT",
        "allowed_mode": allowed_mode,
        "collection_mode": collection_mode,
        "submit_permission": submit_permission,
        "testnet_submit_allowed": testnet_submit_allowed,
        "real_submit_allowed": real_submit_allowed,
        "submit_attempted": submit_attempted,
        "cancel_attempted": cancel_attempted,
        "flatten_attempted": flatten_attempted,
        "high_trust_field_count": high_trust_field_count,
        "auxiliary_field_count": auxiliary_field_count,
        "gap_closure_field_count": gap_closure_field_count,
        "trusted_auxiliary_records_built": trusted_auxiliary_records_built,
        "gap_closure_records_built": gap_closure_records_built,
        "valid_for_auxiliary_analysis": valid_for_auxiliary_analysis,
        "valid_for_gap_closure": valid_for_gap_closure,
        "previous_gap": previous_gap,
        "estimated_gap_after_trust_check": estimated_gap_after_trust_check,
        "gap_delta": gap_delta,
        "price_field_auxiliary_effective": price_field_auxiliary_effective,
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

    report_json = out_dir / "price_field_trust_control_report.json"
    report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    return report


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate price field trust control report")
    parser.add_argument("--output-dir", default="reports/price_field_trust_control_report")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = generate_price_field_trust_control_report(
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
