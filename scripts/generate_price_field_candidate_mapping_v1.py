from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def generate_price_field_candidate_mapping_v1(
    audit_result: dict[str, Any] | None = None,
    output_dir: str = "reports/price_field_candidate_mapping_v1",
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

    candidate_price_fields = []
    numeric_candidate_counts = {}
    non_null_candidate_counts = {}
    mapping_ready = False
    fallback_values_used = False
    price_field_mappings = {}
    primary_price_field = None
    backup_price_fields = []
    mapping_warnings = []
    missing_inputs = []

    if audit_result:
        candidate_price_fields = audit_result.get("candidate_price_fields", [])
        numeric_candidate_counts = audit_result.get("numeric_candidate_counts", {})
        non_null_candidate_counts = audit_result.get("non_null_candidate_counts", {})
        candidate_audit_ready = audit_result.get("candidate_audit_ready", False)

        if candidate_audit_ready and candidate_price_fields:
            # Score each candidate by numeric count and non-null count
            scored_candidates = []
            for field in candidate_price_fields:
                numeric_count = numeric_candidate_counts.get(field, 0)
                non_null_count = non_null_candidate_counts.get(field, 0)
                # Prefer fields with 100% numeric values
                score = numeric_count * 2
                if non_null_count > 0:
                    score += (numeric_count / non_null_count) * 100
                scored_candidates.append((score, field))

            # Sort by score descending
            scored_candidates.sort(reverse=True, key=lambda x: x[0])

            if scored_candidates:
                primary_price_field = scored_candidates[0][1]
                backup_price_fields = [field for (score, field) in scored_candidates[1:]]

                price_field_mappings = {
                    "primary": primary_price_field,
                    "backups": backup_price_fields,
                }
                mapping_ready = True
            else:
                mapping_warnings.append("No valid price field candidates found")
        else:
            mapping_warnings.append("Candidate audit not ready or no candidates")
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
    if fallback_values_used:
        final_verdict = "FAIL"

    report = {
        "task_id": "T402",
        "phase": "PRICE_FIELD_CANDIDATE_MAPPING_V1",
        "allowed_mode": allowed_mode,
        "collection_mode": collection_mode,
        "submit_permission": submit_permission,
        "testnet_submit_allowed": testnet_submit_allowed,
        "real_submit_allowed": real_submit_allowed,
        "submit_attempted": submit_attempted,
        "cancel_attempted": cancel_attempted,
        "flatten_attempted": flatten_attempted,
        "candidate_price_fields": candidate_price_fields,
        "numeric_candidate_counts": numeric_candidate_counts,
        "non_null_candidate_counts": non_null_candidate_counts,
        "primary_price_field": primary_price_field,
        "backup_price_fields": backup_price_fields,
        "price_field_mappings": price_field_mappings,
        "mapping_ready": mapping_ready,
        "fallback_values_used": fallback_values_used,
        "mapping_warnings": mapping_warnings,
        "missing_inputs": missing_inputs,
        "final_verdict": final_verdict,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }

    report_json = out_dir / "price_field_candidate_mapping_v1.json"
    report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    return report


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate price field candidate mapping v1")
    parser.add_argument("--output-dir", default="reports/price_field_candidate_mapping_v1")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = generate_price_field_candidate_mapping_v1(
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
