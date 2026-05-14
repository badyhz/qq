#!/usr/bin/env python3
import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional


REQUIRED_BLOCKED_ACTIONS = [
    "TESTNET_DRY_RUN_ONLY",
    "TESTNET_SUBMIT",
    "REAL_SUBMIT",
    "SUBMIT_ORDER",
    "CANCEL_ORDER",
    "FLATTEN_POSITION",
]

SAFETY_FLAGS = {
    "shadow_only": True,
    "testnet_dry_run_allowed": False,
    "testnet_submit_allowed": False,
    "real_submit_allowed": False,
    "submit_attempted": False,
    "cancel_attempted": False,
    "flatten_attempted": False,
}

ALLOWED_ACTIONS = [
    "READ_REPORTS",
    "GENERATE_TESTNET_DRY_RUN_READINESS_PHASE_CONTROL_REPORT",
    "MANUAL_REVIEW_ONLY",
]

BLOCKED_ACTIONS = list(REQUIRED_BLOCKED_ACTIONS)


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


def _execution_block_ok(report: Optional[Dict[str, Any]]) -> bool:
    if not report:
        return False

    safety = report.get("safety_flags") or {}
    if safety.get("testnet_dry_run_allowed") is not False:
        return False
    if safety.get("testnet_submit_allowed") is not False:
        return False
    if safety.get("real_submit_allowed") is not False:
        return False
    if safety.get("submit_attempted") is not False:
        return False
    if safety.get("cancel_attempted") is not False:
        return False
    if safety.get("flatten_attempted") is not False:
        return False

    allowed_actions = report.get("allowed_actions") or []
    blocked_actions = report.get("blocked_actions") or []

    for blocked in REQUIRED_BLOCKED_ACTIONS:
        if blocked in allowed_actions:
            return False

    for blocked in REQUIRED_BLOCKED_ACTIONS:
        if blocked not in blocked_actions:
            return False

    return True


def generate_phase_control_report(
    readiness_input_packet: Optional[Dict[str, Any]],
    safety_constraint_report: Optional[Dict[str, Any]],
    artifact_dependency_report: Optional[Dict[str, Any]],
    readiness_score_report: Optional[Dict[str, Any]],
    readiness_input_path: str,
    safety_constraint_path: str,
    artifact_dependency_path: str,
    readiness_score_path: str,
) -> Dict[str, Any]:
    blockers: List[str] = []

    t441_pass = (
        readiness_input_packet
        and readiness_input_packet.get("ok") is True
        and readiness_input_packet.get("final_decision")
        == "READY_FOR_TESTNET_DRY_RUN_READINESS_SAFETY_CONSTRAINT_REVIEW"
    )
    t442_pass = (
        safety_constraint_report
        and safety_constraint_report.get("ok") is True
        and safety_constraint_report.get("final_decision")
        == "READY_FOR_TESTNET_DRY_RUN_ARTIFACT_DEPENDENCY_REVIEW"
    )
    t443_pass = (
        artifact_dependency_report
        and artifact_dependency_report.get("ok") is True
        and artifact_dependency_report.get("final_decision")
        == "READY_FOR_TESTNET_DRY_RUN_READINESS_SCORE"
    )
    t444_pass = (
        readiness_score_report
        and readiness_score_report.get("ok") is True
        and readiness_score_report.get("readiness_score") == 100
        and readiness_score_report.get("final_decision")
        == "READY_FOR_MANUAL_TESTNET_DRY_RUN_APPROVAL_REVIEW"
    )

    if not t441_pass:
        blockers.append("T441_READINESS_INPUT_NOT_READY")
    if not t442_pass:
        blockers.append("T442_SAFETY_CONSTRAINTS_NOT_VERIFIED")
    if not t443_pass:
        blockers.append("T443_ARTIFACT_DEPENDENCIES_NOT_VERIFIED")
    if not t444_pass:
        blockers.append("T444_READINESS_SCORE_NOT_READY")

    execution_block_pass = (
        _execution_block_ok(readiness_input_packet)
        and _execution_block_ok(safety_constraint_report)
        and _execution_block_ok(artifact_dependency_report)
        and _execution_block_ok(readiness_score_report)
    )
    if not execution_block_pass:
        blockers.append("EXECUTION_BLOCK_NOT_CONFIRMED")

    component_statuses = {
        "t441": t441_pass,
        "t442": t442_pass,
        "t443": t443_pass,
        "t444": t444_pass,
        "execution_block_confirmed": execution_block_pass,
    }

    all_pass = t441_pass and t442_pass and t443_pass and t444_pass and execution_block_pass
    if all_pass:
        ok = True
        phase_completion_status = "COMPLETED_PENDING_MANUAL_TESTNET_DRY_RUN_APPROVAL_REVIEW"
        next_phase = "MANUAL_TESTNET_DRY_RUN_APPROVAL_REVIEW"
        final_decision = "READY_FOR_MANUAL_TESTNET_DRY_RUN_APPROVAL_REVIEW"
    else:
        ok = False
        phase_completion_status = "BLOCKED"
        next_phase = "TESTNET_DRY_RUN_READINESS_REVIEW"
        final_decision = "CONTINUE_TESTNET_DRY_RUN_READINESS_REVIEW"

    return {
        "ok": ok,
        "task": "T445",
        "phase": "TESTNET_DRY_RUN_READINESS_REVIEW",
        "source_reports": {
            "readiness_input_packet": readiness_input_path,
            "safety_constraint_report": safety_constraint_path,
            "artifact_dependency_report": artifact_dependency_path,
            "readiness_score_report": readiness_score_path,
        },
        "phase_completion_status": phase_completion_status,
        "current_phase": "TESTNET_DRY_RUN_READINESS_REVIEW",
        "next_phase": next_phase,
        "component_statuses": component_statuses,
        "blockers": blockers,
        "blocker_count": len(blockers),
        "safety_flags": dict(SAFETY_FLAGS),
        "allowed_actions": list(ALLOWED_ACTIONS),
        "blocked_actions": list(BLOCKED_ACTIONS),
        "final_decision": final_decision,
        "notes": [],
    }


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        description="Generate TESTNET_DRY_RUN_READINESS_REVIEW phase control report"
    )
    parser.add_argument(
        "--readiness-input-packet",
        type=str,
        required=True,
        help="Path to T441 readiness input packet JSON",
    )
    parser.add_argument(
        "--safety-constraint-report",
        type=str,
        required=True,
        help="Path to T442 safety constraint report JSON",
    )
    parser.add_argument(
        "--artifact-dependency-report",
        type=str,
        required=True,
        help="Path to T443 artifact dependency report JSON",
    )
    parser.add_argument(
        "--readiness-score-report",
        type=str,
        required=True,
        help="Path to T444 readiness score report JSON",
    )
    parser.add_argument("--output", type=str, help="Path to write output JSON")
    parser.add_argument("--json", action="store_true", help="Print JSON to stdout")

    args = parser.parse_args(argv)

    readiness_input_packet = load_json(args.readiness_input_packet)
    safety_constraint_report = load_json(args.safety_constraint_report)
    artifact_dependency_report = load_json(args.artifact_dependency_report)
    readiness_score_report = load_json(args.readiness_score_report)

    report = generate_phase_control_report(
        readiness_input_packet,
        safety_constraint_report,
        artifact_dependency_report,
        readiness_score_report,
        args.readiness_input_packet,
        args.safety_constraint_report,
        args.artifact_dependency_report,
        args.readiness_score_report,
    )

    if args.output:
        write_ok = write_json(args.output, report)
        if not write_ok:
            print("Failed to write output", file=sys.stderr)
            return 1

    if args.json or not args.output:
        print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))

    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
