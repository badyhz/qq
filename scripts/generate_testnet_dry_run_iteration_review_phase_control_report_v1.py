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
    "REVIEW_DRY_RUN_ARTIFACTS",
    "GENERATE_NEXT_DRY_RUN_PLAN",
]
ALLOWED_BLOCKED = ["READ_REPORTS", "REVIEW_DRY_RUN_ARTIFACTS", "GENERATE_NEXT_DRY_RUN_PLAN"]


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
    iteration_review_packet: Optional[Dict[str, Any]],
    blocker_analysis_report: Optional[Dict[str, Any]],
    iteration_plan: Optional[Dict[str, Any]],
    approval_artifact: Optional[Dict[str, Any]],
    packet_path: str,
    blocker_path: str,
    plan_path: str,
    approval_path: str,
) -> Dict[str, Any]:
    blockers: List[str] = []

    c1 = bool(iteration_review_packet and iteration_review_packet.get("final_decision") == "READY_FOR_DRY_RUN_RESULT_BLOCKER_ANALYSIS")
    c2 = bool(blocker_analysis_report and blocker_analysis_report.get("final_decision") == "READY_FOR_NEXT_DRY_RUN_ITERATION_PLAN")
    c3 = bool(iteration_plan and iteration_plan.get("final_decision") == "READY_FOR_DRY_RUN_ITERATION_APPROVAL_ARTIFACT")
    c4 = bool(approval_artifact and approval_artifact.get("final_decision") == "READY_FOR_DRY_RUN_ITERATION_REVIEW_PHASE_CONTROL")

    if not c1:
        blockers.append("T471_ITERATION_REVIEW_PACKET_NOT_READY")
    if not c2:
        blockers.append("T472_BLOCKER_ANALYSIS_NOT_READY")
    if not c3:
        blockers.append("T473_ITERATION_PLAN_NOT_READY")
    if not c4:
        blockers.append("T474_APPROVAL_ARTIFACT_NOT_READY")

    safe = _safe(iteration_review_packet) and _safe(blocker_analysis_report) and _safe(iteration_plan) and _safe(approval_artifact)
    if not safe:
        blockers.append("NO_SUBMIT_NO_EXCHANGE_BLOCK_NOT_CONFIRMED")

    ok = len(blockers) == 0

    if ok:
        phase_completion_status = "COMPLETED_TESTNET_DRY_RUN_ITERATION_REVIEW"
        next_phase = "NEXT_TESTNET_DRY_RUN_ONLY_ITERATION"
        final_decision = "READY_FOR_NEXT_TESTNET_DRY_RUN_ONLY_ITERATION"
        safety_flags = _safety_flags(True)
        allowed_actions = list(ALLOWED_PASS)
    else:
        phase_completion_status = "BLOCKED"
        next_phase = "TESTNET_DRY_RUN_ITERATION_REVIEW"
        final_decision = "CONTINUE_TESTNET_DRY_RUN_ITERATION_REVIEW"
        safety_flags = _safety_flags(False)
        allowed_actions = list(ALLOWED_BLOCKED)

    return {
        "ok": ok,
        "task": "T475",
        "phase": "TESTNET_DRY_RUN_ITERATION_REVIEW",
        "source_reports": {
            "iteration_review_packet": packet_path,
            "blocker_analysis_report": blocker_path,
            "iteration_plan": plan_path,
            "approval_artifact": approval_path,
        },
        "phase_completion_status": phase_completion_status,
        "current_phase": "TESTNET_DRY_RUN_ITERATION_REVIEW",
        "next_phase": next_phase,
        "component_statuses": {
            "t471": c1,
            "t472": c2,
            "t473": c3,
            "t474": c4,
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
    parser = argparse.ArgumentParser(description="Generate TESTNET_DRY_RUN iteration review phase control report")
    parser.add_argument("--iteration-review-packet", required=True)
    parser.add_argument("--blocker-analysis-report", required=True)
    parser.add_argument("--iteration-plan", required=True)
    parser.add_argument("--approval-artifact", required=True)
    parser.add_argument("--output")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    report = generate_phase_control_report(
        load_json(args.iteration_review_packet),
        load_json(args.blocker_analysis_report),
        load_json(args.iteration_plan),
        load_json(args.approval_artifact),
        args.iteration_review_packet,
        args.blocker_analysis_report,
        args.iteration_plan,
        args.approval_artifact,
    )

    if args.output and not write_json(args.output, report):
        print("Failed to write output", file=sys.stderr)
        return 1
    if args.json or not args.output:
        print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))

    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
