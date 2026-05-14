#!/usr/bin/env python3
import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional


REQUIRED_BLOCKED_ACTIONS = [
    "TESTNET_SUBMIT",
    "REAL_SUBMIT",
    "SUBMIT_ORDER",
    "CANCEL_ORDER",
    "FLATTEN_POSITION",
]

ALLOWED_ACTIONS_PASS = [
    "READ_REPORTS",
    "TESTNET_DRY_RUN_ONLY",
    "GENERATE_TESTNET_DRY_RUN_ONLY_MODE_PHASE_CONTROL_REPORT",
]
ALLOWED_ACTIONS_BLOCKED = [
    "READ_REPORTS",
    "GENERATE_TESTNET_DRY_RUN_ONLY_MODE_PHASE_CONTROL_REPORT",
]

BLOCKED_ACTIONS = list(REQUIRED_BLOCKED_ACTIONS)


def _safety_flags(testnet_dry_run_allowed: bool) -> Dict[str, Any]:
    return {
        "testnet_dry_run_allowed": testnet_dry_run_allowed,
        "testnet_submit_allowed": False,
        "real_submit_allowed": False,
        "submit_order_allowed": False,
        "cancel_order_allowed": False,
        "flatten_position_allowed": False,
        "submit_attempted": False,
        "cancel_attempted": False,
        "flatten_attempted": False,
    }


def load_json(path: str) -> Optional[Dict[str, Any]]:
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def write_json(path: str, data: Dict[str, Any]) -> bool:
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=True, ensure_ascii=False)
        return True
    except Exception:
        return False


def _submit_cancel_flatten_block_ok(report: Optional[Dict[str, Any]]) -> bool:
    if not report:
        return False

    safety = report.get("safety_flags") or {}
    if safety.get("testnet_submit_allowed") is not False:
        return False
    if safety.get("real_submit_allowed") is not False:
        return False
    if safety.get("submit_order_allowed") is not False:
        return False
    if safety.get("cancel_order_allowed") is not False:
        return False
    if safety.get("flatten_position_allowed") is not False:
        return False
    if safety.get("submit_attempted") is not False:
        return False
    if safety.get("cancel_attempted") is not False:
        return False
    if safety.get("flatten_attempted") is not False:
        return False

    allowed = report.get("allowed_actions") or []
    blocked = report.get("blocked_actions") or []

    for item in REQUIRED_BLOCKED_ACTIONS:
        if item in allowed:
            return False
        if item not in blocked:
            return False

    return True


def generate_phase_control_report(
    mode_packet: Optional[Dict[str, Any]],
    payload_plan: Optional[Dict[str, Any]],
    runner_guard_report: Optional[Dict[str, Any]],
    preflight_report: Optional[Dict[str, Any]],
    mode_packet_path: str,
    payload_plan_path: str,
    runner_guard_report_path: str,
    preflight_report_path: str,
) -> Dict[str, Any]:
    blockers: List[str] = []

    t456_ok = bool(
        mode_packet
        and mode_packet.get("final_decision") == "READY_FOR_TESTNET_DRY_RUN_NO_SUBMIT_PAYLOAD_PLAN"
    )
    t457_ok = bool(
        payload_plan
        and payload_plan.get("final_decision") == "READY_FOR_TESTNET_DRY_RUN_NO_SUBMIT_RUNNER_GUARD"
    )
    t458_ok = bool(
        runner_guard_report
        and runner_guard_report.get("final_decision") == "READY_FOR_TESTNET_DRY_RUN_ONLY_PREFLIGHT_REPORT"
    )
    t459_ok = bool(
        preflight_report
        and preflight_report.get("final_decision") == "READY_FOR_TESTNET_DRY_RUN_ONLY_PHASE_CONTROL"
    )

    if not t456_ok:
        blockers.append("T456_MODE_PACKET_NOT_READY")
    if not t457_ok:
        blockers.append("T457_PAYLOAD_PLAN_NOT_READY")
    if not t458_ok:
        blockers.append("T458_RUNNER_GUARD_NOT_VERIFIED")
    if not t459_ok:
        blockers.append("T459_PREFLIGHT_NOT_PASSED")

    block_ok = (
        _submit_cancel_flatten_block_ok(mode_packet)
        and _submit_cancel_flatten_block_ok(payload_plan)
        and _submit_cancel_flatten_block_ok(runner_guard_report)
        and _submit_cancel_flatten_block_ok(preflight_report)
    )
    if not block_ok:
        blockers.append("SUBMIT_CANCEL_FLATTEN_BLOCK_NOT_CONFIRMED")

    ok = len(blockers) == 0

    if ok:
        phase_completion_status = "COMPLETED_READY_FOR_TESTNET_DRY_RUN_ONLY_EXECUTION"
        next_phase = "TESTNET_DRY_RUN_ONLY_EXECUTION"
        safety_flags = _safety_flags(True)
        allowed_actions = list(ALLOWED_ACTIONS_PASS)
        final_decision = "READY_FOR_TESTNET_DRY_RUN_ONLY_EXECUTION"
    else:
        phase_completion_status = "BLOCKED"
        next_phase = "TESTNET_DRY_RUN_ONLY_MODE"
        safety_flags = _safety_flags(False)
        allowed_actions = list(ALLOWED_ACTIONS_BLOCKED)
        final_decision = "CONTINUE_TESTNET_DRY_RUN_ONLY_MODE"

    return {
        "ok": ok,
        "task": "T460",
        "phase": "TESTNET_DRY_RUN_ONLY_MODE",
        "source_reports": {
            "mode_packet": mode_packet_path,
            "payload_plan": payload_plan_path,
            "runner_guard_report": runner_guard_report_path,
            "preflight_report": preflight_report_path,
        },
        "phase_completion_status": phase_completion_status,
        "current_phase": "TESTNET_DRY_RUN_ONLY_MODE",
        "next_phase": next_phase,
        "component_statuses": {
            "t456": t456_ok,
            "t457": t457_ok,
            "t458": t458_ok,
            "t459": t459_ok,
            "submit_cancel_flatten_block_confirmed": block_ok,
        },
        "blockers": blockers,
        "blocker_count": len(blockers),
        "safety_flags": safety_flags,
        "allowed_actions": allowed_actions,
        "blocked_actions": list(BLOCKED_ACTIONS),
        "final_decision": final_decision,
        "notes": [],
    }


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        description="Generate TESTNET_DRY_RUN_ONLY_MODE phase control report"
    )
    parser.add_argument("--mode-packet", required=True)
    parser.add_argument("--payload-plan", required=True)
    parser.add_argument("--runner-guard-report", required=True)
    parser.add_argument("--preflight-report", required=True)
    parser.add_argument("--output")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    mode_packet = load_json(args.mode_packet)
    payload_plan = load_json(args.payload_plan)
    runner_guard_report = load_json(args.runner_guard_report)
    preflight_report = load_json(args.preflight_report)

    report = generate_phase_control_report(
        mode_packet,
        payload_plan,
        runner_guard_report,
        preflight_report,
        args.mode_packet,
        args.payload_plan,
        args.runner_guard_report,
        args.preflight_report,
    )

    if args.output and not write_json(args.output, report):
        print("Failed to write output", file=sys.stderr)
        return 1

    if args.json or not args.output:
        print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))

    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
