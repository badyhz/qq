#!/usr/bin/env python3
import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional


PHASE = "ONE_SHOT_SUBMIT_LIFECYCLE_FINAL_ARCHIVE"


def load_json(path: str) -> Optional[Dict[str, Any]]:
    if not path or not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def write_json(path: str, data: Dict[str, Any]) -> bool:
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, sort_keys=True, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def _has_unsafe_marker(data: Any) -> bool:
    if isinstance(data, str):
        lower = data.lower()
        return (
            "mainnet" in lower
            or "live" in lower
            or "api.binance.com" in lower
            or "fapi.binance.com" in lower
        )
    if isinstance(data, dict):
        return any(_has_unsafe_marker(v) for v in data.values())
    if isinstance(data, list):
        return any(_has_unsafe_marker(v) for v in data)
    return False


def generate_final_archive_phase_control_report(
    replay_index: Optional[Dict[str, Any]],
    regression_guard: Optional[Dict[str, Any]],
    safety_dashboard: Optional[Dict[str, Any]],
    closeout_snapshot: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    blockers: List[str] = []
    warnings: List[str] = []

    payloads = [replay_index, regression_guard, safety_dashboard, closeout_snapshot]
    labels = ["REPLAY_INDEX", "REGRESSION_GUARD", "SAFETY_DASHBOARD", "CLOSEOUT_SNAPSHOT"]
    for label, payload in zip(labels, payloads):
        if not isinstance(payload, dict):
            blockers.append(f"{label}_MISSING")

    if blockers:
        return {
            "ok": False,
            "verdict": "FAIL",
            "phase": PHASE,
            "decision": "STOP",
            "can_continue": False,
            "readonly": True,
            "submit_allowed": False,
            "cancel_allowed": False,
            "flatten_allowed": False,
            "max_submit_count": 0,
            "blockers": sorted(set(blockers)),
            "warnings": sorted(set(warnings)),
            "required_next_actions": ["restore_required_archive_inputs"],
            "next_task_recommendation": "restore_inputs_and_retry_final_archive",
        }

    for payload in payloads:
        if _has_unsafe_marker(payload):
            blockers.append("UNSAFE_MARKER_DETECTED")

    if any(bool(p.get("submit_allowed")) or bool(p.get("cancel_allowed")) or bool(p.get("flatten_allowed")) for p in payloads):
        blockers.append("ACTION_PERMISSION_TRUE_NOT_ALLOWED")

    for payload in payloads:
        if int(payload.get("max_submit_count", 0)) != 0:
            blockers.append("MAX_SUBMIT_COUNT_NOT_ZERO")
            break

    replay_verdict = str(replay_index.get("verdict", ""))
    guard_verdict = str(regression_guard.get("verdict", ""))
    dashboard_verdict = str(safety_dashboard.get("verdict", ""))
    snapshot_verdict = str(closeout_snapshot.get("verdict", ""))
    snapshot_state = str(closeout_snapshot.get("lifecycle_status", ""))

    any_fail = any(v == "FAIL" for v in [replay_verdict, guard_verdict, dashboard_verdict, snapshot_verdict])
    any_partial = any(v == "PARTIAL" for v in [replay_verdict, guard_verdict, dashboard_verdict, snapshot_verdict])
    all_pass = all(v == "PASS" for v in [replay_verdict, guard_verdict, dashboard_verdict, snapshot_verdict])

    rollback_state = snapshot_state == "ROLLBACK_REVIEW"

    if rollback_state:
        verdict = "FAIL"
        ok = False
        decision = "REQUIRE_HUMAN_ROLLBACK_REVIEW"
        required_next_actions = ["require_human_rollback_review_before_archive"]
        next_task_recommendation = "human_rollback_review_required"
    elif blockers or any_fail:
        verdict = "FAIL"
        ok = False
        decision = "STOP"
        required_next_actions = ["stop_and_resolve_lifecycle_blockers"]
        next_task_recommendation = "resolve_blockers_before_archive"
    elif all_pass and snapshot_state == "CLOSED_HEALTHY":
        verdict = "PASS"
        ok = True
        decision = "ARCHIVED_CLOSED"
        required_next_actions = ["archive_lifecycle_bundle_complete"]
        next_task_recommendation = "complete_archive_and_start_repo_hygiene_review"
    elif any_partial and snapshot_state == "MONITOR":
        verdict = "PARTIAL"
        ok = False
        decision = "ARCHIVED_MONITOR"
        required_next_actions = ["archive_monitor_state_and_continue_observation"]
        next_task_recommendation = "monitor_then_replay_regression_guard"
    elif any_partial and snapshot_state == "REVIEW":
        verdict = "PARTIAL"
        ok = False
        decision = "ARCHIVED_REVIEW"
        required_next_actions = ["archive_review_state_and_initiate_human_review"]
        next_task_recommendation = "human_review_then_reissue_closeout_snapshot"
    else:
        verdict = "FAIL"
        ok = False
        decision = "STOP"
        required_next_actions = ["resolve_unhandled_archive_state"]
        next_task_recommendation = "manual_intervention_required"

    return {
        "ok": ok,
        "verdict": verdict,
        "phase": PHASE,
        "decision": decision,
        "can_continue": False,
        "readonly": True,
        "submit_allowed": False,
        "cancel_allowed": False,
        "flatten_allowed": False,
        "max_submit_count": 0,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "required_next_actions": required_next_actions,
        "next_task_recommendation": next_task_recommendation,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate one-shot submit lifecycle final archive phase control report")
    parser.add_argument("--replay-index-json", required=True)
    parser.add_argument("--regression-guard-json", required=True)
    parser.add_argument("--safety-dashboard-json", required=True)
    parser.add_argument("--closeout-snapshot-json", required=True)
    parser.add_argument("--output-json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = generate_final_archive_phase_control_report(
        load_json(args.replay_index_json),
        load_json(args.regression_guard_json),
        load_json(args.safety_dashboard_json),
        load_json(args.closeout_snapshot_json),
    )

    if args.output_json and not write_json(args.output_json, report):
        print("failed_to_write_output", file=sys.stderr)
        return 1
    if args.json:
        if args.pretty:
            print(json.dumps(report, sort_keys=True, indent=2, ensure_ascii=False))
        else:
            print(json.dumps(report, sort_keys=True, ensure_ascii=False))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
