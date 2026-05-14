#!/usr/bin/env python3
import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional

REQUIRED_BLOCKED_ACTIONS = [
    "EXCHANGE_API_CALL",
    "TESTNET_SUBMIT",
    "REAL_SUBMIT",
    "SUBMIT_ORDER",
    "CANCEL_ORDER",
    "FLATTEN_POSITION",
]

ALLOWED_PASS = [
    "READ_REPORTS",
    "TESTNET_DRY_RUN_ONLY",
    "MATERIALIZE_PAYLOAD_ARTIFACT",
    "GENERATE_NEXT_DRY_RUN_ARTIFACT",
]
ALLOWED_BLOCKED = ["READ_REPORTS", "MATERIALIZE_PAYLOAD_ARTIFACT", "GENERATE_NEXT_DRY_RUN_ARTIFACT"]


def _safety_flags(dry_run_allowed: bool) -> Dict[str, Any]:
    return {
        "testnet_dry_run_allowed": dry_run_allowed,
        "exchange_api_calls_allowed": False,
        "testnet_submit_allowed": False,
        "real_submit_allowed": False,
        "submit_order_allowed": False,
        "cancel_order_allowed": False,
        "flatten_position_allowed": False,
        "submit_attempted": False,
        "cancel_attempted": False,
        "flatten_attempted": False,
    }


def _safe(report: Optional[Dict[str, Any]]) -> bool:
    s = (report or {}).get("safety_flags") or {}
    if s.get("exchange_api_calls_allowed") is not False:
        return False
    if s.get("testnet_submit_allowed") is not False:
        return False
    if s.get("real_submit_allowed") is not False:
        return False
    if s.get("submit_order_allowed") is not False:
        return False
    if s.get("cancel_order_allowed") is not False:
        return False
    if s.get("flatten_position_allowed") is not False:
        return False
    if s.get("submit_attempted") is not False:
        return False
    if s.get("cancel_attempted") is not False:
        return False
    if s.get("flatten_attempted") is not False:
        return False

    allowed = (report or {}).get("allowed_actions") or []
    blocked = (report or {}).get("blocked_actions") or []
    for action in REQUIRED_BLOCKED_ACTIONS:
        if action in allowed:
            return False
        if action not in blocked:
            return False
    return True


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


def generate_phase_control_report(
    execution_packet: Optional[Dict[str, Any]],
    candidate_artifact: Optional[Dict[str, Any]],
    payload_plan: Optional[Dict[str, Any]],
    materialization_report: Optional[Dict[str, Any]],
    execution_packet_path: str,
    candidate_artifact_path: str,
    payload_plan_path: str,
    materialization_report_path: str,
) -> Dict[str, Any]:
    blockers: List[str] = []

    c1 = bool(execution_packet and execution_packet.get("final_decision") == "READY_FOR_NEXT_DRY_RUN_CANDIDATE_INPUT_ARTIFACT")
    c2 = bool(candidate_artifact and candidate_artifact.get("final_decision") == "READY_FOR_NEXT_NO_SUBMIT_PAYLOAD_PLAN")
    c3 = bool(payload_plan and payload_plan.get("final_decision") == "READY_FOR_NEXT_ARTIFACT_ONLY_MATERIALIZATION_REPORT")
    c4 = bool(materialization_report and materialization_report.get("final_decision") == "READY_FOR_NEXT_DRY_RUN_ONLY_ITERATION_PHASE_CONTROL")

    if not c1:
        blockers.append("T476_EXECUTION_PACKET_NOT_READY")
    if not c2:
        blockers.append("T477_CANDIDATE_ARTIFACT_NOT_READY")
    if not c3:
        blockers.append("T478_PAYLOAD_PLAN_NOT_READY")
    if not c4:
        blockers.append("T479_MATERIALIZATION_NOT_READY")

    safe = _safe(execution_packet) and _safe(candidate_artifact) and _safe(payload_plan) and _safe(materialization_report)
    if not safe:
        blockers.append("NO_SUBMIT_NO_EXCHANGE_BLOCK_NOT_CONFIRMED")

    ok = len(blockers) == 0

    if ok:
        phase_completion_status = "COMPLETED_NEXT_TESTNET_DRY_RUN_ONLY_ITERATION"
        next_phase = "NEXT_TESTNET_DRY_RUN_RESULT_REVIEW"
        final_decision = "READY_FOR_NEXT_TESTNET_DRY_RUN_RESULT_REVIEW"
        safety_flags = _safety_flags(True)
        allowed_actions = list(ALLOWED_PASS)
    else:
        phase_completion_status = "BLOCKED"
        next_phase = "NEXT_TESTNET_DRY_RUN_ONLY_ITERATION"
        final_decision = "CONTINUE_NEXT_TESTNET_DRY_RUN_ONLY_ITERATION"
        safety_flags = _safety_flags(False)
        allowed_actions = list(ALLOWED_BLOCKED)

    return {
        "ok": ok,
        "task": "T480",
        "phase": "NEXT_TESTNET_DRY_RUN_ONLY_ITERATION",
        "source_reports": {
            "execution_packet": execution_packet_path,
            "candidate_artifact": candidate_artifact_path,
            "payload_plan": payload_plan_path,
            "materialization_report": materialization_report_path,
        },
        "phase_completion_status": phase_completion_status,
        "current_phase": "NEXT_TESTNET_DRY_RUN_ONLY_ITERATION",
        "next_phase": next_phase,
        "component_statuses": {
            "t476": c1,
            "t477": c2,
            "t478": c3,
            "t479": c4,
            "no_submit_no_exchange_block_confirmed": safe,
        },
        "blockers": blockers,
        "blocker_count": len(blockers),
        "safety_flags": safety_flags,
        "allowed_actions": allowed_actions,
        "blocked_actions": list(REQUIRED_BLOCKED_ACTIONS),
        "final_decision": final_decision,
        "notes": [],
    }


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    parser = argparse.ArgumentParser(description="Generate next TESTNET_DRY_RUN_ONLY iteration phase control report")
    parser.add_argument("--execution-packet", required=True)
    parser.add_argument("--candidate-artifact", required=True)
    parser.add_argument("--payload-plan", required=True)
    parser.add_argument("--materialization-report", required=True)
    parser.add_argument("--output")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    report = generate_phase_control_report(
        load_json(args.execution_packet),
        load_json(args.candidate_artifact),
        load_json(args.payload_plan),
        load_json(args.materialization_report),
        args.execution_packet,
        args.candidate_artifact,
        args.payload_plan,
        args.materialization_report,
    )

    if args.output and not write_json(args.output, report):
        print("Failed to write output", file=sys.stderr)
        return 1
    if args.json or not args.output:
        print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))

    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
