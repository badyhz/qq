from __future__ import annotations

import argparse
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def update_real_shadow_remediation_history(
    validation_result: dict[str, Any] | None = None,
    reports_dir: str = "reports",
    output_dir: str = "reports/real_shadow_remediation_history_update",
    history_dir: str = "data/real_shadow_remediation_history",
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

    hist_dir = Path(history_dir)
    hist_dir.mkdir(parents=True, exist_ok=True)

    history_updated = False
    history_run_id = f"REAL_SHADOW_RUN_{uuid.uuid4().hex[:8]}"
    previous_history_runs = 0
    eligible_records_considered = 0
    eligible_records_added = 0
    duplicate_records_skipped = 0
    history_runs_after = 0
    idempotency_ok = True
    valid_for_gap_closure = False
    missing_inputs: list[str] = []

    if validation_result is None:
        validation_path = Path(reports_dir) / "real_shadow_observation_validation" / "real_shadow_observation_validation.json"
        if validation_path.exists():
            validation_result = _read_json(validation_path)
        else:
            missing_inputs.append("validation_result_not_provided_and_not_found")

    if validation_result:
        valid_for_gap_closure = validation_result.get("valid_for_gap_closure", False)
        gap_closure_eligible_records = validation_result.get("gap_closure_eligible_records", [])
        eligible_records_considered = len(gap_closure_eligible_records)

    # Load existing history
    history_file = hist_dir / "history.json"
    existing_history = _read_json(history_file)

    previous_history_runs = len(existing_history.get("runs", [])) if isinstance(existing_history.get("runs"), list) else 0
    existing_run_ids = set(r.get("history_run_id", "") for r in existing_history.get("runs", []))

    # Only proceed if valid_for_gap_closure and eligible records exist
    if valid_for_gap_closure and eligible_records_considered > 0:
        # First, check if any records would actually be added
        existing_records = existing_history.get("records", []) if isinstance(existing_history.get("records"), list) else []
        existing_record_ids = set(r.get("record_id", "") for r in existing_records)

        temp_records_added = 0
        for record in gap_closure_eligible_records:
            record_id = record.get("record_id", "")
            if record_id and record_id not in existing_record_ids:
                temp_records_added += 1

        # Only add a new run if we would actually add records
        if temp_records_added > 0 and history_run_id not in existing_run_ids:
            new_history_run = {
                "history_run_id": history_run_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "eligible_record_count": eligible_records_considered,
            }

            runs = existing_history.get("runs", []) if isinstance(existing_history.get("runs"), list) else []
            runs.append(new_history_run)
            existing_history["runs"] = runs

            for record in gap_closure_eligible_records:
                record_id = record.get("record_id", "")
                if record_id and record_id not in existing_record_ids:
                    existing_records.append(record)
                    eligible_records_added += 1
                    existing_record_ids.add(record_id)
                else:
                    duplicate_records_skipped += 1

            existing_history["records"] = existing_records

            history_file.write_text(json.dumps(existing_history, ensure_ascii=False, indent=2), encoding="utf-8")
            history_updated = True
        else:
            # No new records to add, skip adding a run
            history_updated = False

    history_runs_after = len(existing_history.get("runs", [])) if isinstance(existing_history.get("runs"), list) else 0

    final_verdict = "PASS"
    if missing_inputs:
        final_verdict = "PARTIAL"
    if not idempotency_ok:
        final_verdict = "FAIL"

    # Safety checks
    if testnet_submit_allowed or real_submit_allowed:
        final_verdict = "FAIL"
    if submit_attempted or cancel_attempted or flatten_attempted:
        final_verdict = "FAIL"

    report: dict[str, Any] = {
        "task_id": "T394",
        "phase": "REAL_SHADOW_REMEDIATION_HISTORY_UPDATE",
        "allowed_mode": allowed_mode,
        "collection_mode": collection_mode,
        "submit_permission": submit_permission,
        "testnet_submit_allowed": testnet_submit_allowed,
        "real_submit_allowed": real_submit_allowed,
        "submit_attempted": submit_attempted,
        "cancel_attempted": cancel_attempted,
        "flatten_attempted": flatten_attempted,
        "history_updated": history_updated,
        "history_run_id": history_run_id,
        "previous_history_runs": previous_history_runs,
        "eligible_records_considered": eligible_records_considered,
        "eligible_records_added": eligible_records_added,
        "duplicate_records_skipped": duplicate_records_skipped,
        "history_runs_after": history_runs_after,
        "idempotency_ok": idempotency_ok,
        "valid_for_gap_closure": valid_for_gap_closure,
        "missing_inputs": missing_inputs,
        "final_verdict": final_verdict,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }

    report_json = out_dir / "real_shadow_remediation_history_update.json"
    report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    return report


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Update real shadow remediation history")
    parser.add_argument("--reports-dir", default="reports")
    parser.add_argument("--output-dir", default="reports/real_shadow_remediation_history_update")
    parser.add_argument("--history-dir", default="data/real_shadow_remediation_history")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = update_real_shadow_remediation_history(
        reports_dir=args.reports_dir,
        output_dir=args.output_dir,
        history_dir=args.history_dir,
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    print(f"task_id={result.get('task_id','')}")
    print(f"final_verdict={result.get('final_verdict','')}")
    print(f"history_updated={result.get('history_updated',False)}")
    print(f"eligible_records_added={result.get('eligible_records_added',0)}")


if __name__ == "__main__":
    main()
