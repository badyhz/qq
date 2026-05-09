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
    shadow_collection_queue_v1_json: str,
    shadow_data_quality_rules_v1_json: str,
    readiness_blocker_to_action_map_v1_json: str,
) -> list[str]:
    missing: list[str] = []
    if not Path(shadow_collection_queue_v1_json).exists():
        missing.append("shadow_collection_queue_v1_json")
    if not Path(shadow_data_quality_rules_v1_json).exists():
        missing.append("shadow_data_quality_rules_v1_json")
    if not Path(readiness_blocker_to_action_map_v1_json).exists():
        missing.append("readiness_blocker_to_action_map_v1_json")
    return missing


def generate_shadow_collection_preflight_v1(
    *,
    shadow_collection_queue_v1_json: str = "reports/shadow_collection_queue_v1/shadow_collection_queue_v1.json",
    shadow_data_quality_rules_v1_json: str = "reports/shadow_data_quality_rules_v1/shadow_data_quality_rules_v1.json",
    readiness_blocker_to_action_map_v1_json: str = "reports/readiness_blocker_to_action_map_v1/readiness_blocker_to_action_map_v1.json",
    output_dir: str = "reports/shadow_collection_preflight_v1",
) -> dict[str, Any]:
    missing_inputs = _collect_missing_inputs(
        shadow_collection_queue_v1_json=shadow_collection_queue_v1_json,
        shadow_data_quality_rules_v1_json=shadow_data_quality_rules_v1_json,
        readiness_blocker_to_action_map_v1_json=readiness_blocker_to_action_map_v1_json,
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

    queue = _read_json(Path(shadow_collection_queue_v1_json))
    rules = _read_json(Path(shadow_data_quality_rules_v1_json))
    action_map = _read_json(Path(readiness_blocker_to_action_map_v1_json))

    queue_ready = queue.get("queue_ready", False)
    quality_gate_ready = rules.get("quality_gate_ready", False)
    action_map_ready = len(action_map.get("actions", [])) > 0
    preflight_ready = queue_ready and quality_gate_ready and action_map_ready

    blocking_issues: list[str] = []
    warnings: list[str] = []

    if not queue_ready:
        blocking_issues.append("queue_not_ready")
    if not quality_gate_ready:
        blocking_issues.append("quality_gate_not_ready")
    if not action_map_ready:
        blocking_issues.append("action_map_not_ready")
    if missing_inputs:
        blocking_issues.extend(f"missing_input_{m}" for m in missing_inputs)

    allowed_actions = ["SHADOW_ONLY", "TESTNET_DRY_RUN_BLOCKED"]

    final_verdict = "PASS"
    if blocking_issues:
        final_verdict = "PARTIAL"

    if testnet_submit_allowed or real_submit_allowed:
        final_verdict = "FAIL"

    report: dict[str, Any] = {
        "task_id": "T384",
        "phase": "SHADOW_COLLECTION_PREFLIGHT_V1",
        "allowed_mode": allowed_mode,
        "submit_permission": submit_permission,
        "testnet_submit_allowed": testnet_submit_allowed,
        "real_submit_allowed": real_submit_allowed,
        "submit_attempted": submit_attempted,
        "cancel_attempted": cancel_attempted,
        "flatten_attempted": flatten_attempted,
        "queue_ready": queue_ready,
        "quality_gate_ready": quality_gate_ready,
        "action_map_ready": action_map_ready,
        "preflight_ready": preflight_ready,
        "blocking_issues": blocking_issues,
        "warnings": warnings,
        "allowed_actions": allowed_actions,
        "missing_inputs": missing_inputs,
        "final_verdict": final_verdict,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }

    report_json = out_dir / "shadow_collection_preflight_v1.json"
    summary_md = out_dir / "summary.md"

    report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        "# Shadow Collection Preflight V1",
        "",
        f"- task_id: {report['task_id']}",
        f"- phase: {report['phase']}",
        f"- final_verdict: {report['final_verdict']}",
        f"- queue_ready: {report['queue_ready']}",
        f"- quality_gate_ready: {report['quality_gate_ready']}",
        f"- action_map_ready: {report['action_map_ready']}",
        f"- preflight_ready: {report['preflight_ready']}",
        f"- blocking_issues: {report['blocking_issues']}",
        f"- warnings: {report['warnings']}",
        f"- allowed_actions: {report['allowed_actions']}",
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
    parser = argparse.ArgumentParser(description="Generate shadow collection preflight v1")
    parser.add_argument("--shadow-collection-queue-v1-json", default="reports/shadow_collection_queue_v1/shadow_collection_queue_v1.json")
    parser.add_argument("--shadow-data-quality-rules-v1-json", default="reports/shadow_data_quality_rules_v1/shadow_data_quality_rules_v1.json")
    parser.add_argument("--readiness-blocker-to-action-map-v1-json", default="reports/readiness_blocker_to_action_map_v1/readiness_blocker_to_action_map_v1.json")
    parser.add_argument("--output-dir", default="reports/shadow_collection_preflight_v1")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = generate_shadow_collection_preflight_v1(
        shadow_collection_queue_v1_json=str(args.shadow_collection_queue_v1_json or "reports/shadow_collection_queue_v1/shadow_collection_queue_v1.json"),
        shadow_data_quality_rules_v1_json=str(args.shadow_data_quality_rules_v1_json or "reports/shadow_data_quality_rules_v1/shadow_data_quality_rules_v1.json"),
        readiness_blocker_to_action_map_v1_json=str(args.readiness_blocker_to_action_map_v1_json or "reports/readiness_blocker_to_action_map_v1/readiness_blocker_to_action_map_v1.json"),
        output_dir=str(args.output_dir or "reports/shadow_collection_preflight_v1"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"task_id={result.get('task_id','')}")
    print(f"final_verdict={result.get('final_verdict','')}")
    print(f"preflight_ready={result.get('preflight_ready',False)}")


if __name__ == "__main__":
    main()
