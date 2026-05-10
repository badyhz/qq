from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def audit_observation_price_field_candidates(
    source_path: str = "reports/observation_sample_store/observation_samples.csv",
    output_dir: str = "reports/observation_price_field_candidate_audit",
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
    row_count = 0
    column_count = 0
    candidate_price_fields = []
    candidate_price_field_count = 0
    numeric_candidate_counts = {}
    non_null_candidate_counts = {}
    timestamp_field_candidates = []
    symbol_field_candidates = []
    timeframe_field_candidates = []
    setup_field_candidates = []
    source_type_counts = {}
    synthetic_placeholder_counts = {}
    candidate_audit_ready = False
    missing_inputs = []
    audit_warnings = []

    price_field_keywords = [
        "price",
        "close",
        "open",
        "high",
        "low",
        "volume",
        "mark",
        "last",
        "entry",
        "signal",
        "observed",
        "reference",
        "current",
        "trigger",
        "kline",
        "vwap",
        "twap",
    ]

    timestamp_keywords = ["timestamp", "time", "created", "updated", "at"]
    symbol_keywords = ["symbol", "pair", "base", "quote"]
    timeframe_keywords = ["timeframe", "interval", "tf", "bar", "period"]
    setup_keywords = ["setup", "strategy", "key", "name", "type"]

    non_price_fields = [
        "id",
        "uuid",
        "hash",
        "score",
        "rank",
        "count",
        "size",
        "enabled",
        "active",
        "status",
        "origin",
        "source",
        "experiment",
        "test",
        "run",
        "near",
        "miss",
        "verdict",
        "hint",
        "weight",
        "outcome",
        "primary",
        "best",
        "consistency",
        "quality",
        "value",
        "level",
        "protection",
        "distance",
        "orphan",
        "health",
        "recommendation",
        "candidate",
        "sample",
        "observation",
        "shadow",
        "real",
        "dry",
        "row",
        "index",
    ]

    if file_exists:
        with open(source_path_obj, newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            columns = reader.fieldnames or []
            column_count = len(columns)

            # Identify candidate fields
            for col in columns:
                col_lower = col.lower()
                # Check for price field candidates
                is_price_candidate = False
                for keyword in price_field_keywords:
                    if keyword in col_lower:
                        is_price_candidate = True
                        break
                # Exclude non-price fields
                for keyword in non_price_fields:
                    if keyword in col_lower:
                        is_price_candidate = False
                        break
                if is_price_candidate:
                    candidate_price_fields.append(col)
                    numeric_candidate_counts[col] = 0
                    non_null_candidate_counts[col] = 0

                # Check for timestamp field candidates
                for keyword in timestamp_keywords:
                    if keyword in col_lower and col not in timestamp_field_candidates:
                        timestamp_field_candidates.append(col)

                # Check for symbol field candidates
                for keyword in symbol_keywords:
                    if keyword in col_lower and col not in symbol_field_candidates:
                        symbol_field_candidates.append(col)

                # Check for timeframe field candidates
                for keyword in timeframe_keywords:
                    if keyword in col_lower and col not in timeframe_field_candidates:
                        timeframe_field_candidates.append(col)

                # Check for setup field candidates
                for keyword in setup_keywords:
                    if keyword in col_lower and col not in setup_field_candidates:
                        setup_field_candidates.append(col)

            candidate_price_field_count = len(candidate_price_fields)

            # Analyze rows
            for row in reader:
                row_count += 1
                for col in candidate_price_fields:
                    val = row.get(col)
                    if val is not None and val != "":
                        non_null_candidate_counts[col] += 1
                        try:
                            float(val)
                            numeric_candidate_counts[col] += 1
                        except ValueError:
                            pass

                # Check source_type if present
                source_type = row.get("source_type")
                if source_type:
                    source_type_counts[source_type] = source_type_counts.get(source_type, 0) + 1

                # Check synthetic_placeholder if present
                synthetic_placeholder = row.get("synthetic_placeholder")
                if synthetic_placeholder is not None:
                    key = str(synthetic_placeholder).lower()
                    synthetic_placeholder_counts[key] = synthetic_placeholder_counts.get(key, 0) + 1

            candidate_audit_ready = True

    final_verdict = "PASS"
    if not file_exists:
        final_verdict = "PARTIAL"
        missing_inputs.append("observation_samples.csv not found")
    if row_count == 0 and file_exists:
        final_verdict = "PARTIAL"
        audit_warnings.append("No rows found in CSV")
    if candidate_price_field_count == 0:
        final_verdict = "PARTIAL"

    # Safety checks
    if testnet_submit_allowed or real_submit_allowed:
        final_verdict = "FAIL"
    if submit_attempted or cancel_attempted or flatten_attempted:
        final_verdict = "FAIL"

    report = {
        "task_id": "T401",
        "phase": "OBSERVATION_PRICE_FIELD_CANDIDATE_AUDIT",
        "allowed_mode": allowed_mode,
        "collection_mode": collection_mode,
        "submit_permission": submit_permission,
        "testnet_submit_allowed": testnet_submit_allowed,
        "real_submit_allowed": real_submit_allowed,
        "submit_attempted": submit_attempted,
        "cancel_attempted": cancel_attempted,
        "flatten_attempted": flatten_attempted,
        "source_path": source_path,
        "file_exists": file_exists,
        "row_count": row_count,
        "column_count": column_count,
        "candidate_price_fields": candidate_price_fields,
        "candidate_price_field_count": candidate_price_field_count,
        "numeric_candidate_counts": numeric_candidate_counts,
        "non_null_candidate_counts": non_null_candidate_counts,
        "timestamp_field_candidates": timestamp_field_candidates,
        "symbol_field_candidates": symbol_field_candidates,
        "timeframe_field_candidates": timeframe_field_candidates,
        "setup_field_candidates": setup_field_candidates,
        "source_type_counts": source_type_counts,
        "synthetic_placeholder_counts": synthetic_placeholder_counts,
        "candidate_audit_ready": candidate_audit_ready,
        "missing_inputs": missing_inputs,
        "audit_warnings": audit_warnings,
        "final_verdict": final_verdict,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }

    report_json = out_dir / "observation_price_field_candidate_audit.json"
    report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    return report


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit observation price field candidates")
    parser.add_argument("--source-path", default="reports/observation_sample_store/observation_samples.csv")
    parser.add_argument("--output-dir", default="reports/observation_price_field_candidate_audit")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = audit_observation_price_field_candidates(
        source_path=args.source_path,
        output_dir=args.output_dir,
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    print(f"task_id={result.get('task_id','')}")
    print(f"final_verdict={result.get('final_verdict','')}")
    print(f"candidate_price_field_count={result.get('candidate_price_field_count',0)}")


if __name__ == "__main__":
    main()
