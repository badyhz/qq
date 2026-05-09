from __future__ import annotations

import argparse
import json
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


def _collect_missing_inputs(
    *,
    shadow_collection_round_v1_json: str,
    shadow_collection_output_validation_v1_json: str,
) -> list[str]:
    missing: list[str] = []
    if not Path(shadow_collection_round_v1_json).exists():
        missing.append("shadow_collection_round_v1_json")
    if not Path(shadow_collection_output_validation_v1_json).exists():
        missing.append("shadow_collection_output_validation_v1_json")
    return missing


def update_shadow_remediation_history_v1(
    *,
    shadow_collection_round_v1_json: str = "reports/shadow_collection_round_v1/shadow_collection_round_v1.json",
    shadow_collection_output_validation_v1_json: str = "reports/shadow_collection_output_validation_v1/shadow_collection_output_validation_v1.json",
    output_dir: str = "reports/shadow_remediation_history_update_v1",
    history_dir: str = "data/shadow_remediation_history",
) -> dict[str, Any]:
    missing_inputs = _collect_missing_inputs(
        shadow_collection_round_v1_json=shadow_collection_round_v1_json,
        shadow_collection_output_validation_v1_json=shadow_collection_output_validation_v1_json,
    )

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

    collection_round = _read_json(Path(shadow_collection_round_v1_json))
    validation = _read_json(Path(shadow_collection_output_validation_v1_json))

    collection_run_id = collection_round.get("collection_run_id", "")
    valid_records = validation.get("valid_records", 0)
    quality_passed = validation.get("quality_passed", False)
    valid_for_gap_closure = validation.get("valid_for_gap_closure", False)
    gap_closure_eligible_records = validation.get("gap_closure_eligible_records", []) if isinstance(validation.get("gap_closure_eligible_records"), list) else []

    history_file = hist_dir / "history.json"
    existing_history = _read_json(history_file)

    previous_history_runs = len(existing_history.get("runs", [])) if isinstance(existing_history.get("runs"), list) else 0
    existing_run_ids = set(r.get("collection_run_id", "") for r in existing_history.get("runs", []))

    history_updated = False
    history_run_id = collection_run_id
    new_records_considered = len(gap_closure_eligible_records)
    new_records_added = 0
    duplicate_records_skipped = 0
    idempotency_ok = True

    # Only proceed if valid_for_gap_closure and eligible records exist
    if valid_for_gap_closure and len(gap_closure_eligible_records) > 0 and collection_run_id not in existing_run_ids:
        new_history = {
            "collection_run_id": collection_run_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "record_count": valid_records,
        }

        runs = existing_history.get("runs", []) if isinstance(existing_history.get("runs"), list) else []
        runs.append(new_history)
        existing_history["runs"] = runs

        existing_records = existing_history.get("records", []) if isinstance(existing_history.get("records"), list) else []
        existing_record_ids = set(r.get("record_id", "") for r in existing_records)

        for record in gap_closure_eligible_records:
            record_id = record.get("record_id", "")
            if record_id and record_id not in existing_record_ids:
                existing_records.append(record)
                new_records_added += 1
            else:
                duplicate_records_skipped += 1

        existing_history["records"] = existing_records

        history_file.write_text(json.dumps(existing_history, ensure_ascii=False, indent=2), encoding="utf-8")
        history_updated = True

    history_runs_after = len(existing_history.get("runs", [])) if isinstance(existing_history.get("runs"), list) else 0

    final_verdict = "PASS"
    if missing_inputs:
        final_verdict = "PARTIAL"
    if not idempotency_ok:
        final_verdict = "FAIL"

    if testnet_submit_allowed or real_submit_allowed:
        final_verdict = "FAIL"

    report: dict[str, Any] = {
        "task_id": "T388",
        "phase": "SHADOW_REMEDIATION_HISTORY_UPDATE_V1",
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
        "new_records_considered": new_records_considered,
        "new_records_added": new_records_added,
        "duplicate_records_skipped": duplicate_records_skipped,
        "history_runs_after": history_runs_after,
        "idempotency_ok": idempotency_ok,
        "missing_inputs": missing_inputs,
        "final_verdict": final_verdict,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }

    report_json = out_dir / "shadow_remediation_history_update_v1.json"
    summary_md = out_dir / "summary.md"

    report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        "# Shadow Remediation History Update V1",
        "",
        f"- task_id: {report['task_id']}",
        f"- phase: {report['phase']}",
        f"- final_verdict: {report['final_verdict']}",
        f"- history_updated: {report['history_updated']}",
        f"- history_run_id: {report['history_run_id']}",
        f"- previous_history_runs: {report['previous_history_runs']}",
        f"- new_records_considered: {report['new_records_considered']}",
        f"- new_records_added: {report['new_records_added']}",
        f"- duplicate_records_skipped: {report['duplicate_records_skipped']}",
        f"- history_runs_after: {report['history_runs_after']}",
        f"- idempotency_ok: {report['idempotency_ok']}",
        f"- missing_inputs: {report['missing_inputs']}",
        "- allowed_mode: SHADOW_ONLY",
        "- submit_permission: NO_SUBMIT",
        "- testnet_submit_allowed: false",
        "- real_submit_allowed: false",
        "- submit_attempted: false",
        "- cancel_attempted: false",
        "- flatten_attempted: false",
    ]
    summary_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    return report


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Update shadow remediation history v1")
    parser.add_argument("--shadow-collection-round-v1-json", default="reports/shadow_collection_round_v1/shadow_collection_round_v1.json")
    parser.add_argument("--shadow-collection-output-validation-v1-json", default="reports/shadow_collection_output_validation_v1/shadow_collection_output_validation_v1.json")
    parser.add_argument("--output-dir", default="reports/shadow_remediation_history_update_v1")
    parser.add_argument("--history-dir", default="data/shadow_remediation_history")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = update_shadow_remediation_history_v1(
        shadow_collection_round_v1_json=str(args.shadow_collection_round_v1_json or "reports/shadow_collection_round_v1/shadow_collection_round_v1.json"),
        shadow_collection_output_validation_v1_json=str(args.shadow_collection_output_validation_v1_json or "reports/shadow_collection_output_validation_v1/shadow_collection_output_validation_v1.json"),
        output_dir=str(args.output_dir or "reports/shadow_remediation_history_update_v1"),
        history_dir=str(args.history_dir or "data/shadow_remediation_history"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"task_id={result.get('task_id','')}")
    print(f"final_verdict={result.get('final_verdict','')}")
    print(f"history_updated={result.get('history_updated',False)}")


if __name__ == "__main__":
    main()
