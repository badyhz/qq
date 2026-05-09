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


def _to_bool(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def _collect_missing_inputs(
    *,
    sample_quality_audit_json: str,
    blocker_attribution_json: str,
    shadow_collection_plan_v4_json: str,
    backlog_prioritization_json: str,
) -> list[str]:
    missing: list[str] = []
    for label, p in [
        ("sample_quality_audit_json", Path(sample_quality_audit_json)),
        ("blocker_attribution_json", Path(blocker_attribution_json)),
        ("shadow_collection_plan_v4_json", Path(shadow_collection_plan_v4_json)),
        ("backlog_prioritization_json", Path(backlog_prioritization_json)),
    ]:
        if not p.exists():
            missing.append(label)
    return missing


def generate_shadow_phase_control_report_v4(
    *,
    sample_quality_audit_json: str = "reports/shadow_sample_quality_audit/shadow_sample_quality_audit.json",
    blocker_attribution_json: str = "reports/readiness_blocker_attribution/readiness_blocker_attribution.json",
    shadow_collection_plan_v4_json: str = "reports/shadow_collection_plan_v4/shadow_collection_plan_v4.json",
    backlog_prioritization_json: str = "reports/shadow_only_backlog_prioritization/shadow_only_backlog_prioritization.json",
    output_dir: str = "reports/shadow_phase_control_v4",
) -> dict[str, Any]:
    missing_inputs = _collect_missing_inputs(
        sample_quality_audit_json=sample_quality_audit_json,
        blocker_attribution_json=blocker_attribution_json,
        shadow_collection_plan_v4_json=shadow_collection_plan_v4_json,
        backlog_prioritization_json=backlog_prioritization_json,
    )

    allowed_mode = "SHADOW_ONLY"
    submit_permission = "NO_SUBMIT"
    testnet_submit_allowed = False
    real_submit_allowed = False
    submit_attempted = False
    cancel_attempted = False
    flatten_attempted = False

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    sample_quality = _read_json(Path(sample_quality_audit_json))
    blocker_attr = _read_json(Path(blocker_attribution_json))
    collection_plan = _read_json(Path(shadow_collection_plan_v4_json))
    backlog_prio = _read_json(Path(backlog_prioritization_json))

    sample_quality_ready = _to_bool(sample_quality.get("sample_quality_ready", False))
    primary_blocker = str(blocker_attr.get("primary_blocker", "UNKNOWN")).strip().upper()
    readiness_final_verdict = str(blocker_attr.get("readiness_final_verdict", "NOT_READY")).strip().upper()
    total_target_samples = collection_plan.get("total_target_samples", 0) or 0
    backlog_count = backlog_prio.get("backlog_count", 0) or 0

    readiness_status = readiness_final_verdict
    if readiness_status not in {"READY", "NOT_READY", "FAIL"}:
        readiness_status = "NOT_READY"

    # Determine final decision
    final_decision = "CONTINUE_SHADOW_ONLY"
    if readiness_status == "FAIL":
        final_decision = "FAIL_SAFE_BLOCK"
    elif readiness_status == "READY":
        final_decision = "READY_FOR_MANUAL_TESTNET_DRY_RUN_REVIEW"

    # Build allowed actions
    allowed_actions: list[str] = ["SHADOW_ONLY"]
    blocked_reasons: list[str] = []

    if final_decision == "CONTINUE_SHADOW_ONLY":
        allowed_actions.append("TESTNET_DRY_RUN_BLOCKED")
        blocked_reasons.append("readiness_not_ready")
    elif final_decision == "READY_FOR_MANUAL_TESTNET_DRY_RUN_REVIEW":
        allowed_actions.append("TESTNET_DRY_RUN_ONLY")

    # Add blocked reasons from inputs
    if not sample_quality_ready:
        blocked_reasons.append("sample_quality_not_ready")
    if primary_blocker != "UNKNOWN":
        blocked_reasons.append(f"primary_blocker_{primary_blocker.lower()}")

    archive_range = "T208-T380"
    next_recommended_task_range = "T381-T385"

    # Determine final verdict
    final_verdict = "PASS"
    if final_decision == "FAIL_SAFE_BLOCK":
        final_verdict = "FAIL"
    elif missing_inputs:
        final_verdict = "PARTIAL"

    # Safety overrides - NEVER allow TESTNET_DRY_RUN_ONLY unless explicitly READY
    if readiness_status != "READY":
        if "TESTNET_DRY_RUN_ONLY" in allowed_actions:
            allowed_actions.remove("TESTNET_DRY_RUN_ONLY")
        if "TESTNET_DRY_RUN_BLOCKED" not in allowed_actions:
            allowed_actions.append("TESTNET_DRY_RUN_BLOCKED")
        final_decision = "CONTINUE_SHADOW_ONLY"

    # Absolute safety - ensure no submit allowed
    if testnet_submit_allowed or real_submit_allowed:
        final_verdict = "FAIL"
        final_decision = "FAIL_SAFE_BLOCK"
        allowed_actions = ["SHADOW_ONLY", "TESTNET_DRY_RUN_BLOCKED"]
        testnet_submit_allowed = False
        real_submit_allowed = False

    report: dict[str, Any] = {
        "task_id": "T380",
        "phase": "SHADOW_PHASE_CONTROL_V4",
        "allowed_mode": allowed_mode,
        "submit_permission": submit_permission,
        "testnet_submit_allowed": testnet_submit_allowed,
        "real_submit_allowed": real_submit_allowed,
        "submit_attempted": submit_attempted,
        "cancel_attempted": cancel_attempted,
        "flatten_attempted": flatten_attempted,
        "sample_quality_ready": sample_quality_ready,
        "primary_blocker": primary_blocker,
        "total_target_samples": total_target_samples,
        "backlog_count": backlog_count,
        "readiness_status": readiness_status,
        "final_decision": final_decision,
        "allowed_actions": allowed_actions,
        "blocked_reasons": blocked_reasons,
        "archive_range": archive_range,
        "next_recommended_task_range": next_recommended_task_range,
        "final_verdict": final_verdict,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }

    report_json = out_dir / "shadow_phase_control_report_v4.json"
    summary_md = out_dir / "summary.md"

    report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        "# Shadow Phase Control Report V4",
        "",
        f"- task_id: {report['task_id']}",
        f"- phase: {report['phase']}",
        f"- final_verdict: {report['final_verdict']}",
        f"- sample_quality_ready: {report['sample_quality_ready']}",
        f"- primary_blocker: {report['primary_blocker']}",
        f"- total_target_samples: {report['total_target_samples']}",
        f"- backlog_count: {report['backlog_count']}",
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
    parser = argparse.ArgumentParser(description="Generate shadow phase control report v4")
    parser.add_argument("--sample-quality-audit-json", default="reports/shadow_sample_quality_audit/shadow_sample_quality_audit.json")
    parser.add_argument("--blocker-attribution-json", default="reports/readiness_blocker_attribution/readiness_blocker_attribution.json")
    parser.add_argument("--shadow-collection-plan-v4-json", default="reports/shadow_collection_plan_v4/shadow_collection_plan_v4.json")
    parser.add_argument("--backlog-prioritization-json", default="reports/shadow_only_backlog_prioritization/shadow_only_backlog_prioritization.json")
    parser.add_argument("--output-dir", default="reports/shadow_phase_control_v4")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = generate_shadow_phase_control_report_v4(
        sample_quality_audit_json=str(args.sample_quality_audit_json or "reports/shadow_sample_quality_audit/shadow_sample_quality_audit.json"),
        blocker_attribution_json=str(args.blocker_attribution_json or "reports/readiness_blocker_attribution/readiness_blocker_attribution.json"),
        shadow_collection_plan_v4_json=str(args.shadow_collection_plan_v4_json or "reports/shadow_collection_plan_v4/shadow_collection_plan_v4.json"),
        backlog_prioritization_json=str(args.backlog_prioritization_json or "reports/shadow_only_backlog_prioritization/shadow_only_backlog_prioritization.json"),
        output_dir=str(args.output_dir or "reports/shadow_phase_control_v4"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"task_id={result.get('task_id','')}")
    print(f"final_verdict={result.get('final_verdict','')}")
    print(f"final_decision={result.get('final_decision','')}")


if __name__ == "__main__":
    main()
