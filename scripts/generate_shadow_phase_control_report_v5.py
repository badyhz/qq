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
    shadow_collection_preflight_v1_json: str,
    testnet_dry_run_readiness_v4_json: str,
) -> list[str]:
    missing: list[str] = []
    if not Path(shadow_collection_preflight_v1_json).exists():
        missing.append("shadow_collection_preflight_v1_json")
    if not Path(testnet_dry_run_readiness_v4_json).exists():
        missing.append("testnet_dry_run_readiness_v4_json")
    return missing


def generate_shadow_phase_control_report_v5(
    *,
    shadow_collection_preflight_v1_json: str = "reports/shadow_collection_preflight_v1/shadow_collection_preflight_v1.json",
    testnet_dry_run_readiness_v4_json: str = "reports/testnet_dry_run_readiness_v4/testnet_dry_run_readiness_v4_report.json",
    output_dir: str = "reports/shadow_phase_control_v5",
) -> dict[str, Any]:
    missing_inputs = _collect_missing_inputs(
        shadow_collection_preflight_v1_json=shadow_collection_preflight_v1_json,
        testnet_dry_run_readiness_v4_json=testnet_dry_run_readiness_v4_json,
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

    preflight = _read_json(Path(shadow_collection_preflight_v1_json))
    readiness = _read_json(Path(testnet_dry_run_readiness_v4_json))

    shadow_collection_preflight_ready = preflight.get("preflight_ready", False)
    readiness_status = readiness.get("final_verdict", "NOT_READY")
    if readiness_status not in ("READY", "NOT_READY", "FAIL"):
        readiness_status = "NOT_READY"

    blocked_reasons: list[str] = []
    final_decision = "CONTINUE_SHADOW_ONLY"

    if readiness_status == "FAIL":
        final_decision = "FAIL_SAFE_BLOCK"
        blocked_reasons.append("readiness_fail_safe_block")
    elif readiness_status == "READY":
        final_decision = "READY_FOR_MANUAL_TESTNET_DRY_RUN_REVIEW"
    elif shadow_collection_preflight_ready:
        final_decision = "READY_FOR_SHADOW_COLLECTION"
    else:
        final_decision = "CONTINUE_SHADOW_ONLY"
        blocked_reasons.append("preflight_not_ready")

    if readiness_status == "NOT_READY":
        blocked_reasons.append("readiness_not_ready")

    allowed_actions = ["SHADOW_ONLY", "TESTNET_DRY_RUN_BLOCKED"]

    if readiness_status == "READY" and final_decision == "READY_FOR_MANUAL_TESTNET_DRY_RUN_REVIEW":
        allowed_actions = ["SHADOW_ONLY", "TESTNET_DRY_RUN_ONLY"]

    if final_decision == "FAIL_SAFE_BLOCK":
        allowed_actions = ["SHADOW_ONLY", "TESTNET_DRY_RUN_BLOCKED"]

    if readiness_status != "READY":
        if "TESTNET_DRY_RUN_ONLY" in allowed_actions:
            allowed_actions.remove("TESTNET_DRY_RUN_ONLY")
        if "TESTNET_DRY_RUN_BLOCKED" not in allowed_actions:
            allowed_actions.append("TESTNET_DRY_RUN_BLOCKED")
        if final_decision == "READY_FOR_MANUAL_TESTNET_DRY_RUN_REVIEW":
            final_decision = "CONTINUE_SHADOW_ONLY"

    testnet_submit_allowed = False
    real_submit_allowed = False

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
        "task_id": "T385",
        "phase": "SHADOW_PHASE_CONTROL_V5",
        "allowed_mode": allowed_mode,
        "submit_permission": submit_permission,
        "testnet_submit_allowed": testnet_submit_allowed,
        "real_submit_allowed": real_submit_allowed,
        "submit_attempted": submit_attempted,
        "cancel_attempted": cancel_attempted,
        "flatten_attempted": flatten_attempted,
        "shadow_collection_preflight_ready": shadow_collection_preflight_ready,
        "readiness_status": readiness_status,
        "final_decision": final_decision,
        "allowed_actions": allowed_actions,
        "blocked_reasons": blocked_reasons,
        "archive_range": "T208-T385",
        "next_recommended_task_range": "T386-T390",
        "final_verdict": final_verdict,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }

    report_json = out_dir / "shadow_phase_control_report_v5.json"
    summary_md = out_dir / "summary.md"

    report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        "# Shadow Phase Control Report V5",
        "",
        f"- task_id: {report['task_id']}",
        f"- phase: {report['phase']}",
        f"- final_verdict: {report['final_verdict']}",
        f"- shadow_collection_preflight_ready: {report['shadow_collection_preflight_ready']}",
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
    parser = argparse.ArgumentParser(description="Generate shadow phase control report v5")
    parser.add_argument("--shadow-collection-preflight-v1-json", default="reports/shadow_collection_preflight_v1/shadow_collection_preflight_v1.json")
    parser.add_argument("--testnet-dry-run-readiness-v4-json", default="reports/testnet_dry_run_readiness_v4/testnet_dry_run_readiness_v4_report.json")
    parser.add_argument("--output-dir", default="reports/shadow_phase_control_v5")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = generate_shadow_phase_control_report_v5(
        shadow_collection_preflight_v1_json=str(args.shadow_collection_preflight_v1_json or "reports/shadow_collection_preflight_v1/shadow_collection_preflight_v1.json"),
        testnet_dry_run_readiness_v4_json=str(args.testnet_dry_run_readiness_v4_json or "reports/testnet_dry_run_readiness_v4/testnet_dry_run_readiness_v4_report.json"),
        output_dir=str(args.output_dir or "reports/shadow_phase_control_v5"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"task_id={result.get('task_id','')}")
    print(f"final_verdict={result.get('final_verdict','')}")
    print(f"final_decision={result.get('final_decision','')}")


if __name__ == "__main__":
    main()
