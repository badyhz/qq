#!/usr/bin/env python3
import argparse
import json
import os
import uuid
import hashlib
from datetime import datetime, timezone
from typing import Optional, Dict, List


def update_ohlcv_gap_validation_ledger_v1(
    dry_check_result: Optional[Dict] = None,
    dry_check_json_path: Optional[str] = None,
    ledger_path: Optional[str] = None
) -> Dict:
    allowed_mode = "SHADOW_ONLY"
    collection_mode = "SHADOW_COLLECTION"
    submit_permission = "NO_SUBMIT"
    testnet_submit_allowed = False
    real_submit_allowed = False
    submit_attempted = False
    cancel_attempted = False
    flatten_attempted = False
    valid_for_testnet_dry_run = False

    ledger_updated = False
    ledger_run_id = ""
    previous_ledger_runs = 0
    validated_sample_count = 0
    new_validated_samples_added = 0
    duplicate_samples_skipped = 0
    ledger_runs_after = 0
    idempotency_ok = True
    missing_inputs: List[str] = []
    final_verdict = "PASS"

    if not dry_check_result and not dry_check_json_path:
        missing_inputs.append("No dry_check_result or dry_check_json_path provided")
        final_verdict = "PARTIAL"
    elif dry_check_json_path and os.path.exists(dry_check_json_path):
        try:
            with open(dry_check_json_path, "r") as f:
                dry_check_result = json.load(f)
        except Exception as e:
            final_verdict = "FAIL"
            missing_inputs.append(f"Failed to load dry_check JSON: {str(e)}")
    elif not dry_check_result:
        final_verdict = "PARTIAL"

    # Default ledger path
    if not ledger_path:
        ledger_path = "data/ohlcv_gap_validation_ledger/ledger.json"

    # Create ledger directory if needed
    ledger_dir = os.path.dirname(ledger_path)
    if ledger_dir and not os.path.exists(ledger_dir):
        os.makedirs(ledger_dir, exist_ok=True)

    # Load existing ledger
    existing_ledger: Dict = {"runs": [], "validated_samples": []}
    if os.path.exists(ledger_path):
        try:
            with open(ledger_path, "r") as f:
                existing_ledger = json.load(f)
        except Exception as e:
            final_verdict = "FAIL"
            missing_inputs.append(f"Failed to load existing ledger: {str(e)}")

    previous_ledger_runs = len(existing_ledger.get("runs", []))

    # Generate stable ledger_run_id based on dry_check_result
    if dry_check_result:
        # Hash the dry_check_result to get a stable id
        try:
            # Remove generated_at_utc for consistent hashing
            hashable_result = {k: v for k, v in dry_check_result.items() if k != "generated_at_utc"}
            result_str = json.dumps(hashable_result, sort_keys=True, ensure_ascii=False)
            ledger_run_id = hashlib.sha256(result_str.encode("utf-8")).hexdigest()[:32]
        except Exception as e:
            final_verdict = "FAIL"
            missing_inputs.append(f"Failed to generate ledger_run_id: {str(e)}")
            idempotency_ok = False

        # Check if this ledger_run_id already exists
        existing_run_ids = [run.get("ledger_run_id", "") for run in existing_ledger.get("runs", [])]
        if ledger_run_id in existing_run_ids:
            # Idempotent, do nothing
            idempotency_ok = True
            ledger_updated = False
            duplicate_samples_skipped = dry_check_result.get("validated_sample_count", 0)
            ledger_runs_after = previous_ledger_runs
        else:
            # Proceed to update
            # Get validated sample info from dry_check_result's plan_items
            # Wait, dry_check_result might not have validation_items; let's assume we get from plan_result
            # Alternatively, for T419, we'll need to pass plan's validation_items
            # But for script's input, let's allow optional validation_items in dry_check_result
            # Or, we can keep track of sample_ids by record_id + validation_id
            validated_samples_list: List[Dict] = []
            existing_sample_ids = set([sample.get("sample_id", "") for sample in existing_ledger.get("validated_samples", [])])
            existing_record_validation_pairs = set([
                (sample.get("record_id", ""), sample.get("validation_id", ""))
                for sample in existing_ledger.get("validated_samples", [])
            ])

            # For test, let's expect validation_items in dry_check_result (we'll pass from test)
            validation_items = dry_check_result.get("validation_items", [])
            current_run_pairs = set()
            for item in validation_items:
                record_id = item.get("record_id", "")
                validation_id = item.get("validation_id", "")
                pair = (record_id, validation_id)
                if pair in existing_record_validation_pairs or pair in current_run_pairs:
                    duplicate_samples_skipped += 1
                else:
                    sample_id = hashlib.sha256(f"{record_id}-{validation_id}".encode("utf-8")).hexdigest()[:32]
                    validated_samples_list.append({
                        "sample_id": sample_id,
                        "record_id": record_id,
                        "validation_id": validation_id,
                        "symbol": item.get("symbol", ""),
                        "timeframe": item.get("timeframe", ""),
                        "timestamp": item.get("timestamp", "")
                    })
                    new_validated_samples_added += 1
                    current_run_pairs.add(pair)

            validated_sample_count = dry_check_result.get("validated_sample_count", 0)

            if new_validated_samples_added > 0 or validated_sample_count > 0:
                # Create new run entry
                new_run = {
                    "ledger_run_id": ledger_run_id,
                    "validated_sample_count": validated_sample_count,
                    "sample_ids": [sample["sample_id"] for sample in validated_samples_list],
                    "created_at_utc": datetime.now(timezone.utc).isoformat()
                }

                existing_ledger["runs"].append(new_run)
                existing_ledger["validated_samples"].extend(validated_samples_list)

                # Save ledger
                try:
                    with open(ledger_path, "w") as f:
                        json.dump(existing_ledger, f, ensure_ascii=False, indent=2)
                    ledger_updated = True
                    ledger_runs_after = previous_ledger_runs + 1
                except Exception as e:
                    final_verdict = "FAIL"
                    missing_inputs.append(f"Failed to save ledger: {str(e)}")
            else:
                ledger_updated = False
                ledger_runs_after = previous_ledger_runs

    return {
        "task_id": "T419",
        "phase": "OHLCV_GAP_VALIDATION_LEDGER_UPDATE_V1",
        "allowed_mode": allowed_mode,
        "collection_mode": collection_mode,
        "submit_permission": submit_permission,
        "testnet_submit_allowed": testnet_submit_allowed,
        "real_submit_allowed": real_submit_allowed,
        "submit_attempted": submit_attempted,
        "cancel_attempted": cancel_attempted,
        "flatten_attempted": flatten_attempted,
        "ledger_updated": ledger_updated,
        "ledger_run_id": ledger_run_id,
        "previous_ledger_runs": previous_ledger_runs,
        "validated_sample_count": validated_sample_count,
        "new_validated_samples_added": new_validated_samples_added,
        "duplicate_samples_skipped": duplicate_samples_skipped,
        "ledger_runs_after": ledger_runs_after,
        "idempotency_ok": idempotency_ok,
        "valid_for_testnet_dry_run": valid_for_testnet_dry_run,
        "missing_inputs": missing_inputs,
        "final_verdict": final_verdict,
        "generated_at_utc": datetime.now(timezone.utc).isoformat()
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--dry-check-json", type=str, help="Path to T418 dry_check JSON file")
    parser.add_argument("--ledger-path", type=str, help="Path to ledger JSON file")
    args = parser.parse_args()

    result = update_ohlcv_gap_validation_ledger_v1(
        dry_check_json_path=args.dry_check_json,
        ledger_path=args.ledger_path
    )

    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(f"ledger_updated: {result['ledger_updated']}")
        print(f"new_validated_samples_added: {result['new_validated_samples_added']}")


if __name__ == "__main__":
    main()
