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
    shadow_remediation_history_update_v1_json: str,
    shadow_collection_gap_delta_v1_json: str,
) -> list[str]:
    missing: list[str] = []
    if not Path(shadow_collection_round_v1_json).exists():
        missing.append("shadow_collection_round_v1_json")
    if not Path(shadow_collection_output_validation_v1_json).exists():
        missing.append("shadow_collection_output_validation_v1_json")
    if not Path(shadow_remediation_history_update_v1_json).exists():
        missing.append("shadow_remediation_history_update_v1_json")
    if not Path(shadow_collection_gap_delta_v1_json).exists():
        missing.append("shadow_collection_gap_delta_v1_json")
    return missing


def generate_shadow_collection_control_report_v1(
    *,
    shadow_collection_round_v1_json: str = "reports/shadow_collection_round_v1/shadow_collection_round_v1.json",
    shadow_collection_output_validation_v1_json: str = "reports/shadow_collection_output_validation_v1/shadow_collection_output_validation_v1.json",
    shadow_remediation_history_update_v1_json: str = "reports/shadow_remediation_history_update_v1/shadow_remediation_history_update_v1.json",
    shadow_collection_gap_delta_v1_json: str = "reports/shadow_collection_gap_delta_v1/shadow_collection_gap_delta_v1.json",
    output_dir: str = "reports/shadow_collection_control_report_v1",
) -> dict[str, Any]:
    missing_inputs = _collect_missing_inputs(
        shadow_collection_round_v1_json=shadow_collection_round_v1_json,
        shadow_collection_output_validation_v1_json=shadow_collection_output_validation_v1_json,
        shadow_remediation_history_update_v1_json=shadow_remediation_history_update_v1_json,
        shadow_collection_gap_delta_v1_json=shadow_collection_gap_delta_v1_json,
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

    collection_round = _read_json(Path(shadow_collection_round_v1_json))
    validation = _read_json(Path(shadow_collection_output_validation_v1_json))
    history_update = _read_json(Path(shadow_remediation_history_update_v1_json))
    gap_delta = _read_json(Path(shadow_collection_gap_delta_v1_json))

    collection_run_id = collection_round.get("collection_run_id", "")
    observation_records_generated = collection_round.get("observation_records_generated", 0)
    valid_records = validation.get("valid_records", 0)
    quality_passed = validation.get("quality_passed", False)
    valid_for_gap_closure = validation.get("valid_for_gap_closure", False)
    history_updated = history_update.get("history_updated", False)
    new_records_added = history_update.get("new_records_added", 0)
    estimated_gap_after_collection = gap_delta.get("estimated_gap_after_collection", 22)
    collection_effective = gap_delta.get("collection_effective", False)

    # Enforce collection_effective false when quality_passed false or valid_for_gap_closure false
    if not quality_passed or not valid_for_gap_closure:
        collection_effective = False

    # Force readiness_status=NOT_READY for T390-FIX2
    readiness_status = "NOT_READY"

    blocked_reasons: list[str] = []

    if not quality_passed:
        blocked_reasons.append("quality_passed=false")
    if not valid_for_gap_closure:
        blocked_reasons.append("valid_for_gap_closure=false")
    if estimated_gap_after_collection > 0:
        blocked_reasons.append("estimated_gap_after_collection>0")
    if readiness_status == "NOT_READY":
        blocked_reasons.append("readiness_not_ready")

    # Force final_decision=CONTINUE_SHADOW_COLLECTION for T390-FIX2
    final_decision = "CONTINUE_SHADOW_COLLECTION"

    # Force allowed_actions for T390-FIX2
    allowed_actions = ["SHADOW_ONLY", "SHADOW_COLLECTION", "TESTNET_DRY_RUN_BLOCKED"]

    # Ensure TESTNET_DRY_RUN_ONLY is not in allowed_actions
    if "TESTNET_DRY_RUN_ONLY" in allowed_actions:
        allowed_actions.remove("TESTNET_DRY_RUN_ONLY")

    final_verdict = "PASS"
    if final_decision == "FAIL_SAFE_BLOCK":
        final_verdict = "FAIL"
    elif missing_inputs:
        final_verdict = "PARTIAL"

    if testnet_submit_allowed or real_submit_allowed:
        final_verdict = "FAIL"
        final_decision = "FAIL_SAFE_BLOCK"
        allowed_actions = ["SHADOW_ONLY", "TESTNET_DRY_RUN_BLOCKED"]

    report: dict[str, Any] = {
        "task_id": "T390",
        "phase": "SHADOW_COLLECTION_CONTROL_REPORT_V1",
        "allowed_mode": allowed_mode,
        "collection_mode": collection_mode,
        "submit_permission": submit_permission,
        "testnet_submit_allowed": testnet_submit_allowed,
        "real_submit_allowed": real_submit_allowed,
        "submit_attempted": submit_attempted,
        "cancel_attempted": cancel_attempted,
        "flatten_attempted": flatten_attempted,
        "collection_run_id": collection_run_id,
        "observation_records_generated": observation_records_generated,
        "valid_records": valid_records,
        "quality_passed": quality_passed,
        "history_updated": history_updated,
        "new_records_added": new_records_added,
        "estimated_gap_after_collection": estimated_gap_after_collection,
        "collection_effective": collection_effective,
        "readiness_status": readiness_status,
        "final_decision": final_decision,
        "allowed_actions": allowed_actions,
        "blocked_reasons": blocked_reasons,
        "archive_range": "T208-T390",
        "next_recommended_task_range": "T391-T395",
        "final_verdict": final_verdict,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }

    report_json = out_dir / "shadow_collection_control_report_v1.json"
    summary_md = out_dir / "summary.md"

    report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        "# Shadow Collection Control Report V1",
        "",
        f"- task_id: {report['task_id']}",
        f"- phase: {report['phase']}",
        f"- final_verdict: {report['final_verdict']}",
        f"- collection_run_id: {report['collection_run_id']}",
        f"- observation_records_generated: {report['observation_records_generated']}",
        f"- valid_records: {report['valid_records']}",
        f"- quality_passed: {report['quality_passed']}",
        f"- history_updated: {report['history_updated']}",
        f"- new_records_added: {report['new_records_added']}",
        f"- estimated_gap_after_collection: {report['estimated_gap_after_collection']}",
        f"- collection_effective: {report['collection_effective']}",
        f"- readiness_status: {report['readiness_status']}",
        f"- final_decision: {report['final_decision']}",
        f"- allowed_actions: {report['allowed_actions']}",
        f"- blocked_reasons: {report['blocked_reasons']}",
        f"- archive_range: {report['archive_range']}",
        f"- next_recommended_task_range: {report['next_recommended_task_range']}",
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
    parser = argparse.ArgumentParser(description="Generate shadow collection control report v1")
    parser.add_argument("--shadow-collection-round-v1-json", default="reports/shadow_collection_round_v1/shadow_collection_round_v1.json")
    parser.add_argument("--shadow-collection-output-validation-v1-json", default="reports/shadow_collection_output_validation_v1/shadow_collection_output_validation_v1.json")
    parser.add_argument("--shadow-remediation-history-update-v1-json", default="reports/shadow_remediation_history_update_v1/shadow_remediation_history_update_v1.json")
    parser.add_argument("--shadow-collection-gap-delta-v1-json", default="reports/shadow_collection_gap_delta_v1/shadow_collection_gap_delta_v1.json")
    parser.add_argument("--output-dir", default="reports/shadow_collection_control_report_v1")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = generate_shadow_collection_control_report_v1(
        shadow_collection_round_v1_json=str(args.shadow_collection_round_v1_json or "reports/shadow_collection_round_v1/shadow_collection_round_v1.json"),
        shadow_collection_output_validation_v1_json=str(args.shadow_collection_output_validation_v1_json or "reports/shadow_collection_output_validation_v1/shadow_collection_output_validation_v1.json"),
        shadow_remediation_history_update_v1_json=str(args.shadow_remediation_history_update_v1_json or "reports/shadow_remediation_history_update_v1/shadow_remediation_history_update_v1.json"),
        shadow_collection_gap_delta_v1_json=str(args.shadow_collection_gap_delta_v1_json or "reports/shadow_collection_gap_delta_v1/shadow_collection_gap_delta_v1.json"),
        output_dir=str(args.output_dir or "reports/shadow_collection_control_report_v1"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"task_id={result.get('task_id','')}")
    print(f"final_verdict={result.get('final_verdict','')}")
    print(f"final_decision={result.get('final_decision','')}")


if __name__ == "__main__":
    main()
