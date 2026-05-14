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
    "GENERATE_MANUAL_TESTNET_DRY_RUN_APPROVAL_PHASE_CONTROL_REPORT",
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
    review_packet: Optional[Dict[str, Any]],
    checklist_interpretation: Optional[Dict[str, Any]],
    approval_artifact: Optional[Dict[str, Any]],
    final_gate_report: Optional[Dict[str, Any]],
    review_packet_path: str,
    checklist_interpretation_path: str,
    approval_artifact_path: str,
    final_gate_report_path: str,
) -> Dict[str, Any]:
    blockers: List[str] = []

    t446_ok = (
        review_packet
        and review_packet.get("ok") is True
        and review_packet.get("final_decision")
        == "READY_FOR_MANUAL_TESTNET_DRY_RUN_APPROVAL_CHECKLIST"
    )
    t447_ok = (
        checklist_interpretation
        and checklist_interpretation.get("ok") is True
        and checklist_interpretation.get("final_decision")
        == "READY_FOR_MANUAL_TESTNET_DRY_RUN_APPROVAL_ARTIFACT"
    )
    t448_ok = (
        approval_artifact
        and approval_artifact.get("ok") is True
        and approval_artifact.get("final_decision")
        == "READY_FOR_MANUAL_TESTNET_DRY_RUN_FINAL_GATE"
    )
    t449_ok = (
        final_gate_report
        and final_gate_report.get("ok") is True
        and final_gate_report.get("final_decision")
        == "READY_FOR_TESTNET_DRY_RUN_ENABLEMENT_REVIEW"
    )

    if not t446_ok:
        blockers.append("T446_REVIEW_PACKET_NOT_READY")
    if not t447_ok:
        blockers.append("T447_CHECKLIST_NOT_APPROVED")
    if not t448_ok:
        blockers.append("T448_APPROVAL_ARTIFACT_NOT_READY")
    if not t449_ok:
        blockers.append("T449_FINAL_GATE_NOT_PASSED")

    execution_block_ok = (
        _execution_block_ok(review_packet)
        and _execution_block_ok(checklist_interpretation)
        and _execution_block_ok(approval_artifact)
        and _execution_block_ok(final_gate_report)
    )
    if not execution_block_ok:
        blockers.append("EXECUTION_BLOCK_NOT_CONFIRMED")

    all_ok = t446_ok and t447_ok and t448_ok and t449_ok and execution_block_ok

    if all_ok:
        ok = True
        phase_completion_status = "COMPLETED_PENDING_TESTNET_DRY_RUN_ENABLEMENT_REVIEW"
        next_phase = "TESTNET_DRY_RUN_ENABLEMENT_REVIEW"
        final_decision = "READY_FOR_TESTNET_DRY_RUN_ENABLEMENT_REVIEW"
    else:
        ok = False
        phase_completion_status = "BLOCKED"
        next_phase = "MANUAL_TESTNET_DRY_RUN_APPROVAL_REVIEW"
        final_decision = "CONTINUE_MANUAL_TESTNET_DRY_RUN_APPROVAL_REVIEW"

    return {
        "ok": ok,
        "task": "T450",
        "phase": "MANUAL_TESTNET_DRY_RUN_APPROVAL_REVIEW",
        "source_reports": {
            "review_packet": review_packet_path,
            "checklist_interpretation": checklist_interpretation_path,
            "approval_artifact": approval_artifact_path,
            "final_gate_report": final_gate_report_path,
        },
        "phase_completion_status": phase_completion_status,
        "current_phase": "MANUAL_TESTNET_DRY_RUN_APPROVAL_REVIEW",
        "next_phase": next_phase,
        "component_statuses": {
            "t446": t446_ok,
            "t447": t447_ok,
            "t448": t448_ok,
            "t449": t449_ok,
            "execution_block_confirmed": execution_block_ok,
        },
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
        description="Generate MANUAL_TESTNET_DRY_RUN_APPROVAL_REVIEW phase control report"
    )
    parser.add_argument("--review-packet", required=True, help="Path to T446 review packet JSON")
    parser.add_argument(
        "--checklist-interpretation", required=True, help="Path to T447 checklist interpretation JSON"
    )
    parser.add_argument("--approval-artifact", required=True, help="Path to T448 approval artifact JSON")
    parser.add_argument("--final-gate-report", required=True, help="Path to T449 final gate report JSON")
    parser.add_argument("--output", help="Path to write output JSON")
    parser.add_argument("--json", action="store_true", help="Print JSON to stdout")
    args = parser.parse_args(argv)

    review_packet = load_json(args.review_packet)
    checklist_interpretation = load_json(args.checklist_interpretation)
    approval_artifact = load_json(args.approval_artifact)
    final_gate_report = load_json(args.final_gate_report)

    report = generate_phase_control_report(
        review_packet,
        checklist_interpretation,
        approval_artifact,
        final_gate_report,
        args.review_packet,
        args.checklist_interpretation,
        args.approval_artifact,
        args.final_gate_report,
    )

    if args.output:
        if not write_json(args.output, report):
            print("Failed to write output", file=sys.stderr)
            return 1

    if args.json or not args.output:
        print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))

    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
