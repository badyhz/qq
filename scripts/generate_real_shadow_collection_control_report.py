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


def generate_real_shadow_collection_control_report(
    discovery_result: dict[str, Any] | None = None,
    build_result: dict[str, Any] | None = None,
    validation_result: dict[str, Any] | None = None,
    history_result: dict[str, Any] | None = None,
    reports_dir: str = "reports",
    output_dir: str = "reports/real_shadow_collection_control_report",
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

    eligible_source_count = 0
    records_built = 0
    records_analyzed = 0
    valid_records = 0
    valid_for_gap_closure = False
    eligible_records_added = 0
    previous_gap = 22
    estimated_gap_after_real_collection = 22
    gap_delta = 0
    real_collection_effective = False
    readiness_status = "NOT_READY"
    final_decision = "CONTINUE_SHADOW_COLLECTION"
    allowed_actions = ["SHADOW_ONLY", "SHADOW_COLLECTION", "TESTNET_DRY_RUN_BLOCKED"]
    blocked_reasons: list[str] = []
    archive_range = "T208-T395"
    next_recommended_task_range = "T396-T400"
    missing_inputs: list[str] = []

    # Try to load results if not provided
    if discovery_result is None:
        discovery_path = Path(reports_dir) / "real_shadow_data_source_discovery" / "real_shadow_data_source_discovery.json"
        if discovery_path.exists():
            discovery_result = _read_json(discovery_path)
        else:
            missing_inputs.append("discovery_result_not_provided_and_not_found")

    if build_result is None:
        build_path = Path(reports_dir) / "real_shadow_observation_build" / "real_shadow_observation_build.json"
        if build_path.exists():
            build_result = _read_json(build_path)
        else:
            missing_inputs.append("build_result_not_provided_and_not_found")

    if validation_result is None:
        validation_path = Path(reports_dir) / "real_shadow_observation_validation" / "real_shadow_observation_validation.json"
        if validation_path.exists():
            validation_result = _read_json(validation_path)
        else:
            missing_inputs.append("validation_result_not_provided_and_not_found")

    if history_result is None:
        history_path = Path(reports_dir) / "real_shadow_remediation_history_update" / "real_shadow_remediation_history_update.json"
        if history_path.exists():
            history_result = _read_json(history_path)
        else:
            missing_inputs.append("history_result_not_provided_and_not_found")

    # Extract data from results
    if discovery_result:
        eligible_source_count = discovery_result.get("eligible_source_count", 0)

    if build_result:
        records_built = build_result.get("records_built", 0)

    if validation_result:
        records_analyzed = validation_result.get("records_analyzed", 0)
        valid_records = validation_result.get("valid_records", 0)
        valid_for_gap_closure = validation_result.get("valid_for_gap_closure", False)

        if not valid_for_gap_closure:
            blocked_reasons.append("valid_for_gap_closure=false")
        if records_analyzed == 0:
            blocked_reasons.append("no_records_analyzed")

    if history_result:
        eligible_records_added = history_result.get("eligible_records_added", 0)

    # Calculate gap impact
    if valid_for_gap_closure and eligible_records_added > 0:
        estimated_gap_after_real_collection = max(0, previous_gap - eligible_records_added)
        gap_delta = estimated_gap_after_real_collection - previous_gap
        real_collection_effective = True

    if estimated_gap_after_real_collection > 0:
        blocked_reasons.append("estimated_gap_after_real_collection>0")
        readiness_status = "NOT_READY"
    elif valid_for_gap_closure and estimated_gap_after_real_collection <= 0:
        readiness_status = "NOT_READY"  # Still not ready per requirements
        final_decision = "CONTINUE_SHADOW_COLLECTION"

    final_verdict = "PASS"
    if missing_inputs:
        final_verdict = "PARTIAL"

    # Safety checks
    if testnet_submit_allowed or real_submit_allowed:
        final_verdict = "FAIL"
    if submit_attempted or cancel_attempted or flatten_attempted:
        final_verdict = "FAIL"

    # Ensure TESTNET_DRY_RUN_ONLY is not in allowed_actions
    if "TESTNET_DRY_RUN_ONLY" in allowed_actions:
        allowed_actions.remove("TESTNET_DRY_RUN_ONLY")

    # Ensure SHADOW_COLLECTION is in allowed_actions
    if "SHADOW_COLLECTION" not in allowed_actions:
        allowed_actions.append("SHADOW_COLLECTION")

    # Ensure TESTNET_DRY_RUN_BLOCKED is in allowed_actions
    if "TESTNET_DRY_RUN_BLOCKED" not in allowed_actions:
        allowed_actions.append("TESTNET_DRY_RUN_BLOCKED")

    report: dict[str, Any] = {
        "task_id": "T395",
        "phase": "REAL_SHADOW_COLLECTION_CONTROL_REPORT",
        "allowed_mode": allowed_mode,
        "collection_mode": collection_mode,
        "submit_permission": submit_permission,
        "testnet_submit_allowed": testnet_submit_allowed,
        "real_submit_allowed": real_submit_allowed,
        "submit_attempted": submit_attempted,
        "cancel_attempted": cancel_attempted,
        "flatten_attempted": flatten_attempted,
        "eligible_source_count": eligible_source_count,
        "records_built": records_built,
        "records_analyzed": records_analyzed,
        "valid_records": valid_records,
        "valid_for_gap_closure": valid_for_gap_closure,
        "eligible_records_added": eligible_records_added,
        "previous_gap": previous_gap,
        "estimated_gap_after_real_collection": estimated_gap_after_real_collection,
        "gap_delta": gap_delta,
        "real_collection_effective": real_collection_effective,
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

    report_json = out_dir / "real_shadow_collection_control_report.json"
    report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    return report


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate real shadow collection control report")
    parser.add_argument("--reports-dir", default="reports")
    parser.add_argument("--output-dir", default="reports/real_shadow_collection_control_report")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = generate_real_shadow_collection_control_report(
        reports_dir=args.reports_dir,
        output_dir=args.output_dir,
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    print(f"task_id={result.get('task_id','')}")
    print(f"final_verdict={result.get('final_verdict','')}")
    print(f"final_decision={result.get('final_decision','')}")
    print(f"readiness_status={result.get('readiness_status','NOT_READY')}")


if __name__ == "__main__":
    main()
