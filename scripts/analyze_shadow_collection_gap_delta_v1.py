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
    shadow_remediation_history_update_v1_json: str,
    readiness_blocker_attribution_json: str,
    shadow_collection_plan_v4_json: str,
    shadow_collection_output_validation_v1_json: str,
) -> list[str]:
    missing: list[str] = []
    if not Path(shadow_remediation_history_update_v1_json).exists():
        missing.append("shadow_remediation_history_update_v1_json")
    if not Path(readiness_blocker_attribution_json).exists():
        missing.append("readiness_blocker_attribution_json")
    if not Path(shadow_collection_plan_v4_json).exists():
        missing.append("shadow_collection_plan_v4_json")
    if not Path(shadow_collection_output_validation_v1_json).exists():
        missing.append("shadow_collection_output_validation_v1_json")
    return missing


def analyze_shadow_collection_gap_delta_v1(
    *,
    shadow_remediation_history_update_v1_json: str = "reports/shadow_remediation_history_update_v1/shadow_remediation_history_update_v1.json",
    readiness_blocker_attribution_json: str = "reports/readiness_blocker_attribution/readiness_blocker_attribution.json",
    shadow_collection_plan_v4_json: str = "reports/shadow_collection_plan_v4/shadow_collection_plan_v4.json",
    shadow_collection_output_validation_v1_json: str = "reports/shadow_collection_output_validation_v1/shadow_collection_output_validation_v1.json",
    output_dir: str = "reports/shadow_collection_gap_delta_v1",
) -> dict[str, Any]:
    missing_inputs = _collect_missing_inputs(
        shadow_remediation_history_update_v1_json=shadow_remediation_history_update_v1_json,
        readiness_blocker_attribution_json=readiness_blocker_attribution_json,
        shadow_collection_plan_v4_json=shadow_collection_plan_v4_json,
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

    history_update = _read_json(Path(shadow_remediation_history_update_v1_json))
    blocker_attr = _read_json(Path(readiness_blocker_attribution_json))
    collection_plan = _read_json(Path(shadow_collection_plan_v4_json))
    validation = _read_json(Path(shadow_collection_output_validation_v1_json))

    previous_gap = 22
    new_records_added = history_update.get("new_records_added", 0)
    quality_passed = validation.get("quality_passed", False)
    valid_for_gap_closure = validation.get("valid_for_gap_closure", False)
    gap_closure_eligible_records = validation.get("gap_closure_eligible_records", []) if isinstance(validation.get("gap_closure_eligible_records"), list) else []

    # Only decrease gap if valid_for_gap_closure and eligible records were added
    if valid_for_gap_closure and new_records_added > 0:
        estimated_gap_after_collection = max(0, previous_gap - new_records_added)
    else:
        estimated_gap_after_collection = previous_gap

    gap_delta = estimated_gap_after_collection - previous_gap

    blockers_before = blocker_attr.get("blockers", []) if isinstance(blocker_attr.get("blockers"), list) else []
    blockers_after: list[dict[str, Any]] = []

    for blocker in blockers_before:
        code = blocker.get("code", "")
        if "SAMPLE_GAP" in code and estimated_gap_after_collection <= 0:
            continue
        blockers_after.append(blocker)

    resolved_count = len(blockers_before) - len(blockers_after)
    remaining_count = len(blockers_after)
    new_count = 0

    blocker_delta_summary = {
        "resolved_count": resolved_count,
        "remaining_count": remaining_count,
        "new_count": new_count,
    }

    # Only collection_effective true if valid_for_gap_closure and new_records_added > 0
    collection_effective = valid_for_gap_closure and new_records_added > 0
    still_not_ready = estimated_gap_after_collection > 0 or remaining_count > 0

    final_verdict = "PASS"
    if missing_inputs:
        final_verdict = "PARTIAL"

    if testnet_submit_allowed or real_submit_allowed:
        final_verdict = "FAIL"

    report: dict[str, Any] = {
        "task_id": "T389",
        "phase": "SHADOW_COLLECTION_GAP_DELTA_V1",
        "allowed_mode": allowed_mode,
        "collection_mode": collection_mode,
        "submit_permission": submit_permission,
        "testnet_submit_allowed": testnet_submit_allowed,
        "real_submit_allowed": real_submit_allowed,
        "submit_attempted": submit_attempted,
        "cancel_attempted": cancel_attempted,
        "flatten_attempted": flatten_attempted,
        "previous_gap": previous_gap,
        "new_records_added": new_records_added,
        "estimated_gap_after_collection": estimated_gap_after_collection,
        "gap_delta": gap_delta,
        "blockers_before": blockers_before,
        "blockers_after": blockers_after,
        "blocker_delta_summary": blocker_delta_summary,
        "collection_effective": collection_effective,
        "still_not_ready": still_not_ready,
        "missing_inputs": missing_inputs,
        "final_verdict": final_verdict,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }

    report_json = out_dir / "shadow_collection_gap_delta_v1.json"
    summary_md = out_dir / "summary.md"

    report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        "# Shadow Collection Gap Delta V1",
        "",
        f"- task_id: {report['task_id']}",
        f"- phase: {report['phase']}",
        f"- final_verdict: {report['final_verdict']}",
        f"- previous_gap: {report['previous_gap']}",
        f"- new_records_added: {report['new_records_added']}",
        f"- estimated_gap_after_collection: {report['estimated_gap_after_collection']}",
        f"- gap_delta: {report['gap_delta']}",
        f"- collection_effective: {report['collection_effective']}",
        f"- still_not_ready: {report['still_not_ready']}",
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
    parser = argparse.ArgumentParser(description="Analyze shadow collection gap delta v1")
    parser.add_argument("--shadow-remediation-history-update-v1-json", default="reports/shadow_remediation_history_update_v1/shadow_remediation_history_update_v1.json")
    parser.add_argument("--readiness-blocker-attribution-json", default="reports/readiness_blocker_attribution/readiness_blocker_attribution.json")
    parser.add_argument("--shadow-collection-plan-v4-json", default="reports/shadow_collection_plan_v4/shadow_collection_plan_v4.json")
    parser.add_argument("--shadow-collection-output-validation-v1-json", default="reports/shadow_collection_output_validation_v1/shadow_collection_output_validation_v1.json")
    parser.add_argument("--output-dir", default="reports/shadow_collection_gap_delta_v1")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = analyze_shadow_collection_gap_delta_v1(
        shadow_remediation_history_update_v1_json=str(args.shadow_remediation_history_update_v1_json or "reports/shadow_remediation_history_update_v1/shadow_remediation_history_update_v1.json"),
        readiness_blocker_attribution_json=str(args.readiness_blocker_attribution_json or "reports/readiness_blocker_attribution/readiness_blocker_attribution.json"),
        shadow_collection_plan_v4_json=str(args.shadow_collection_plan_v4_json or "reports/shadow_collection_plan_v4/shadow_collection_plan_v4.json"),
        shadow_collection_output_validation_v1_json=str(args.shadow_collection_output_validation_v1_json or "reports/shadow_collection_output_validation_v1/shadow_collection_output_validation_v1.json"),
        output_dir=str(args.output_dir or "reports/shadow_collection_gap_delta_v1"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"task_id={result.get('task_id','')}")
    print(f"final_verdict={result.get('final_verdict','')}")
    print(f"still_not_ready={result.get('still_not_ready',True)}")


if __name__ == "__main__":
    main()
