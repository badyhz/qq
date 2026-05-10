#!/usr/bin/env python3
import argparse
import json
import os
import sys
from typing import Optional, Dict, Any, List


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


REQUIRED_BLOCKED_ACTIONS = [
    "TESTNET_DRY_RUN_ONLY",
    "TESTNET_SUBMIT",
    "REAL_SUBMIT",
    "SUBMIT_ORDER",
    "CANCEL_ORDER",
    "FLATTEN_POSITION"
]

ALLOWED_ACTIONS = [
    "READ_REPORTS",
    "GENERATE_TESTNET_DRY_RUN_PLANNING_PHASE_CONTROL_REPORT",
    "TESTNET_DRY_RUN_PLANNING_ONLY"
]

BLOCKED_ACTIONS = list(REQUIRED_BLOCKED_ACTIONS)


def generate_phase_control_report(
    planning_packet: Optional[Dict[str, Any]],
    constraint_report: Optional[Dict[str, Any]],
    risk_review_report: Optional[Dict[str, Any]],
    approval_artifact: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    ok = False
    notes: List[str] = []
    blockers: List[str] = []

    component_statuses = {
        "T436": "UNKNOWN",
        "T437": "UNKNOWN",
        "T438": "UNKNOWN",
        "T439": "UNKNOWN",
        "EXECUTION_BLOCK": "UNKNOWN"
    }

    if planning_packet:
        if (planning_packet.get("ok") is True and
                planning_packet.get("final_decision") == "READY_FOR_TESTNET_DRY_RUN_PLAN_CONSTRAINT_REVIEW"):
            component_statuses["T436"] = "PASS"
        else:
            component_statuses["T436"] = "FAIL"
            blockers.append("T436_PLANNING_PACKET_NOT_READY")
    else:
        component_statuses["T436"] = "FAIL"
        blockers.append("T436_PLANNING_PACKET_NOT_READY")

    if constraint_report:
        if (constraint_report.get("ok") is True and
                constraint_report.get("final_decision") == "READY_FOR_TESTNET_DRY_RUN_PLAN_RISK_REVIEW"):
            component_statuses["T437"] = "PASS"
        else:
            component_statuses["T437"] = "FAIL"
            blockers.append("T437_CONSTRAINTS_NOT_VERIFIED")
    else:
        component_statuses["T437"] = "FAIL"
        blockers.append("T437_CONSTRAINTS_NOT_VERIFIED")

    if risk_review_report:
        if (risk_review_report.get("ok") is True and
                risk_review_report.get("final_decision") == "READY_FOR_TESTNET_DRY_RUN_PLANNING_APPROVAL_ARTIFACT"):
            component_statuses["T438"] = "PASS"
        else:
            component_statuses["T438"] = "FAIL"
            blockers.append("T438_RISK_REVIEW_NOT_PASSED")
    else:
        component_statuses["T438"] = "FAIL"
        blockers.append("T438_RISK_REVIEW_NOT_PASSED")

    if approval_artifact:
        if (approval_artifact.get("ok") is True and
                approval_artifact.get("final_decision") == "READY_FOR_TESTNET_DRY_RUN_PLANNING_FINAL_GATE"):
            component_statuses["T439"] = "PASS"
        else:
            component_statuses["T439"] = "FAIL"
            blockers.append("T439_APPROVAL_ARTIFACT_NOT_READY")
    else:
        component_statuses["T439"] = "FAIL"
        blockers.append("T439_APPROVAL_ARTIFACT_NOT_READY")

    execution_block_ok = True
    all_reports = [planning_packet, constraint_report, risk_review_report, approval_artifact]
    for report in all_reports:
        if report:
            sf = report.get("safety_flags", {})
            if (sf.get("testnet_dry_run_allowed") is True or
                    sf.get("testnet_submit_allowed") is True or
                    sf.get("real_submit_allowed") is True or
                    sf.get("submit_attempted") is True or
                    sf.get("cancel_attempted") is True or
                    sf.get("flatten_attempted") is True):
                execution_block_ok = False
                break
            allowed = report.get("allowed_actions", [])
            for blocked_action in REQUIRED_BLOCKED_ACTIONS:
                if blocked_action in allowed:
                    execution_block_ok = False
                    break
            if not execution_block_ok:
                break
            blocked_reported = report.get("blocked_actions", [])
            for required in REQUIRED_BLOCKED_ACTIONS:
                if required not in blocked_reported:
                    execution_block_ok = False
                    break
            if not execution_block_ok:
                break

    if execution_block_ok:
        component_statuses["EXECUTION_BLOCK"] = "PASS"
    else:
        component_statuses["EXECUTION_BLOCK"] = "FAIL"
        blockers.append("EXECUTION_BLOCK_NOT_CONFIRMED")

    if (component_statuses["T436"] == "PASS" and
            component_statuses["T437"] == "PASS" and
            component_statuses["T438"] == "PASS" and
            component_statuses["T439"] == "PASS" and
            component_statuses["EXECUTION_BLOCK"] == "PASS"):
        ok = True
        phase_completion_status = "COMPLETED_PENDING_TESTNET_DRY_RUN_READINESS_REVIEW"
        current_phase = "TESTNET_DRY_RUN_PLANNING_REVIEW"
        next_phase = "TESTNET_DRY_RUN_READINESS_REVIEW"
        final_decision = "READY_FOR_TESTNET_DRY_RUN_READINESS_REVIEW"
    else:
        ok = False
        phase_completion_status = "BLOCKED"
        current_phase = "TESTNET_DRY_RUN_PLANNING_REVIEW"
        next_phase = "TESTNET_DRY_RUN_PLANNING_REVIEW"
        final_decision = "CONTINUE_TESTNET_DRY_RUN_PLANNING_REVIEW"

    return {
        "ok": ok,
        "task": "T440",
        "phase": "TESTNET_DRY_RUN_PLANNING_REVIEW",
        "phase_completion_status": phase_completion_status,
        "current_phase": current_phase,
        "next_phase": next_phase,
        "component_statuses": component_statuses,
        "blockers": blockers,
        "blocker_count": len(blockers),
        "safety_flags": {
            "shadow_only": True,
            "testnet_dry_run_allowed": False,
            "testnet_submit_allowed": False,
            "real_submit_allowed": False,
            "submit_attempted": False,
            "cancel_attempted": False,
            "flatten_attempted": False
        },
        "allowed_actions": ALLOWED_ACTIONS,
        "blocked_actions": BLOCKED_ACTIONS,
        "final_decision": final_decision,
        "notes": notes
    }


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        description="Generate TESTNET_DRY_RUN_PLANNING_REVIEW phase control report"
    )
    parser.add_argument("--planning-packet", type=str, required=True, help="Path to T436 planning packet JSON")
    parser.add_argument("--constraint-report", type=str, required=True, help="Path to T437 constraint report JSON")
    parser.add_argument("--risk-review-report", type=str, required=True, help="Path to T438 risk review report JSON")
    parser.add_argument("--approval-artifact", type=str, required=True, help="Path to T439 approval artifact JSON")
    parser.add_argument("--output", type=str, help="Path to write output JSON")
    parser.add_argument("--json", action="store_true", help="Print JSON to stdout")

    args = parser.parse_args(argv)

    planning_packet = load_json(args.planning_packet)
    constraint_report = load_json(args.constraint_report)
    risk_review_report = load_json(args.risk_review_report)
    approval_artifact = load_json(args.approval_artifact)

    report = generate_phase_control_report(
        planning_packet,
        constraint_report,
        risk_review_report,
        approval_artifact
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
