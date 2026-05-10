from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def audit_price_field_source_trust(
    source_path: str = "reports/observation_sample_store/observation_samples.csv",
    audit_result_t401: dict[str, Any] | None = None,
    output_dir: str = "reports/price_field_source_trust_audit",
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

    source_path_obj = Path(source_path)
    file_exists = source_path_obj.exists()

    candidate_price_fields = []
    if audit_result_t401:
        candidate_price_fields = audit_result_t401.get("candidate_price_fields", [])

    field_trust_assessments = []
    high_trust_field_count = 0
    gap_closure_field_count = 0
    auxiliary_field_count = 0
    trust_audit_ready = False
    missing_inputs = []
    audit_warnings = []

    if not file_exists:
        missing_inputs.append("observation_samples.csv not found")

    if not candidate_price_fields and audit_result_t401:
        audit_warnings.append("No candidate price fields from T401")

    if file_exists and candidate_price_fields:
        numeric_counts = {}
        non_null_counts = {}
        for field in candidate_price_fields:
            numeric_counts[field] = 0
            non_null_counts[field] = 0

        with open(source_path_obj, newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                for field in candidate_price_fields:
                    val = row.get(field)
                    if val is not None and val != "":
                        non_null_counts[field] += 1
                        try:
                            float(val)
                            numeric_counts[field] += 1
                        except ValueError:
                            pass

        for field in candidate_price_fields:
            numeric_parse_count = numeric_counts.get(field, 0)
            non_null_count = non_null_counts.get(field, 0)

            detected_source_hint = "UNKNOWN"
            if "close" in field.lower() or "last" in field.lower() or "mark" in field.lower():
                detected_source_hint = "MARKET_OBSERVATION"
            elif "entry" in field.lower():
                detected_source_hint = "ORDER_DERIVED"

            trust_level = "LOW"
            can_use_for_auxiliary_analysis = False
            can_use_for_gap_closure = False
            reason = ""

            if detected_source_hint == "MARKET_OBSERVATION":
                if numeric_parse_count > 0 and non_null_count > 0:
                    trust_level = "MEDIUM"
                    can_use_for_auxiliary_analysis = True
                    reason = "Market observation price, good for auxiliary analysis only"
                else:
                    reason = "Market observation price but no valid numeric data"
            elif detected_source_hint == "ORDER_DERIVED":
                trust_level = "LOW"
                can_use_for_auxiliary_analysis = False
                reason = "Entry price is order-derived, not recommended for auxiliary analysis"
            else:
                reason = "Unknown price field source"

            assessment = {
                "field": field,
                "detected_source_hint": detected_source_hint,
                "numeric_parse_count": numeric_parse_count,
                "non_null_count": non_null_count,
                "trust_level": trust_level,
                "can_use_for_auxiliary_analysis": can_use_for_auxiliary_analysis,
                "can_use_for_gap_closure": can_use_for_gap_closure,
                "reason": reason,
            }
            field_trust_assessments.append(assessment)

            if trust_level == "HIGH":
                high_trust_field_count += 1
            if can_use_for_gap_closure:
                gap_closure_field_count += 1
            if can_use_for_auxiliary_analysis:
                auxiliary_field_count += 1

        trust_audit_ready = True

    final_verdict = "PASS"
    if missing_inputs:
        final_verdict = "PARTIAL"
    if not trust_audit_ready and file_exists:
        final_verdict = "PARTIAL"

    if testnet_submit_allowed or real_submit_allowed:
        final_verdict = "FAIL"
    if submit_attempted or cancel_attempted or flatten_attempted:
        final_verdict = "FAIL"

    report = {
        "task_id": "T406",
        "phase": "PRICE_FIELD_SOURCE_TRUST_AUDIT",
        "allowed_mode": allowed_mode,
        "collection_mode": collection_mode,
        "submit_permission": submit_permission,
        "testnet_submit_allowed": testnet_submit_allowed,
        "real_submit_allowed": real_submit_allowed,
        "submit_attempted": submit_attempted,
        "cancel_attempted": cancel_attempted,
        "flatten_attempted": flatten_attempted,
        "candidate_price_fields": candidate_price_fields,
        "field_trust_assessments": field_trust_assessments,
        "high_trust_field_count": high_trust_field_count,
        "gap_closure_field_count": gap_closure_field_count,
        "auxiliary_field_count": auxiliary_field_count,
        "trust_audit_ready": trust_audit_ready,
        "missing_inputs": missing_inputs,
        "audit_warnings": audit_warnings,
        "final_verdict": final_verdict,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }

    report_json = out_dir / "price_field_source_trust_audit.json"
    report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    return report


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit price field source trust")
    parser.add_argument("--source-path", default="reports/observation_sample_store/observation_samples.csv")
    parser.add_argument("--output-dir", default="reports/price_field_source_trust_audit")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = audit_price_field_source_trust(
        source_path=args.source_path,
        output_dir=args.output_dir,
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    print(f"task_id={result.get('task_id','')}")
    print(f"final_verdict={result.get('final_verdict','')}")
    print(f"auxiliary_field_count={result.get('auxiliary_field_count',0)}")
    print(f"gap_closure_field_count={result.get('gap_closure_field_count',0)}")


if __name__ == "__main__":
    main()
