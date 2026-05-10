from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def generate_price_field_trust_policy_v1(
    audit_result_t406: dict[str, Any] | None = None,
    output_dir: str = "reports/price_field_trust_policy_v1",
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

    policy_version = "v1"
    auxiliary_allowed_fields = []
    gap_closure_allowed_fields = []
    blocked_fields = []
    explicit_policy_allows_price_only = False
    requires_full_ohlcv_for_gap_closure = True
    fallback_values_allowed = False
    policy_ready = False
    policy_warnings = []
    missing_inputs = []

    if audit_result_t406:
        field_trust_assessments = audit_result_t406.get("field_trust_assessments", [])
        for assessment in field_trust_assessments:
            field = assessment.get("field", "")
            can_use_for_auxiliary = assessment.get("can_use_for_auxiliary_analysis", False)
            can_use_for_gap = assessment.get("can_use_for_gap_closure", False)

            if can_use_for_auxiliary:
                auxiliary_allowed_fields.append(field)
            elif can_use_for_gap:
                # This should not happen per rules, but log just in case
                policy_warnings.append(f"Field {field} marked for gap closure, ignoring per policy")
                blocked_fields.append(field)
            else:
                blocked_fields.append(field)

        policy_ready = True
    else:
        missing_inputs.append("audit_result_t406 not provided")

    final_verdict = "PASS"
    if missing_inputs:
        final_verdict = "PARTIAL"
    if not policy_ready:
        final_verdict = "PARTIAL"

    if testnet_submit_allowed or real_submit_allowed:
        final_verdict = "FAIL"
    if submit_attempted or cancel_attempted or flatten_attempted:
        final_verdict = "FAIL"
    if explicit_policy_allows_price_only:
        final_verdict = "FAIL"
    if not requires_full_ohlcv_for_gap_closure:
        final_verdict = "FAIL"
    if fallback_values_allowed:
        final_verdict = "FAIL"
    if gap_closure_allowed_fields:
        final_verdict = "FAIL"

    report = {
        "task_id": "T407",
        "phase": "PRICE_FIELD_TRUST_POLICY_V1",
        "allowed_mode": allowed_mode,
        "collection_mode": collection_mode,
        "submit_permission": submit_permission,
        "testnet_submit_allowed": testnet_submit_allowed,
        "real_submit_allowed": real_submit_allowed,
        "submit_attempted": submit_attempted,
        "cancel_attempted": cancel_attempted,
        "flatten_attempted": flatten_attempted,
        "policy_version": policy_version,
        "auxiliary_allowed_fields": auxiliary_allowed_fields,
        "gap_closure_allowed_fields": gap_closure_allowed_fields,
        "blocked_fields": blocked_fields,
        "explicit_policy_allows_price_only": explicit_policy_allows_price_only,
        "requires_full_ohlcv_for_gap_closure": requires_full_ohlcv_for_gap_closure,
        "fallback_values_allowed": fallback_values_allowed,
        "policy_ready": policy_ready,
        "policy_warnings": policy_warnings,
        "missing_inputs": missing_inputs,
        "final_verdict": final_verdict,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }

    report_json = out_dir / "price_field_trust_policy_v1.json"
    report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    return report


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate price field trust policy v1")
    parser.add_argument("--output-dir", default="reports/price_field_trust_policy_v1")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = generate_price_field_trust_policy_v1(
        output_dir=args.output_dir,
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    print(f"task_id={result.get('task_id','')}")
    print(f"final_verdict={result.get('final_verdict','')}")
    print(f"policy_ready={result.get('policy_ready',False)}")


if __name__ == "__main__":
    main()
