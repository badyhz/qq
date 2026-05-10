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
    "GENERATE_MANUAL_PRE_DRY_RUN_PHASE_CONTROL_REPORT",
    "MANUAL_REVIEW_ONLY"
]

BLOCKED_ACTIONS = list(REQUIRED_BLOCKED_ACTIONS)


def generate_phase_control_report(
    review_packet: Optional[Dict[str, Any]],
    checklist_interpretation: Optional[Dict[str, Any]],
    approval_artifact: Optional[Dict[str, Any]],
    final_gate_report: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    ok = False
    notes: List[str] = []
    blockers: List[str] = []

    component_statuses = {
        "T431": "UNKNOWN",
        "T432": "UNKNOWN",
        "T433": "UNKNOWN",
        "T434": "UNKNOWN",
        "EXECUTION_BLOCK": "UNKNOWN"
    }

    # Check T431
    if review_packet:
        if (review_packet.get("ok") is True and
                review_packet.get("final_decision") == "READY_FOR_MANUAL_PRE_DRY_RUN_CHECKLIST"):
            component_statuses["T431"] = "PASS"
        else:
            component_statuses["T431"] = "FAIL"
            blockers.append("T431_REVIEW_PACKET_NOT_READY")
    else:
        component_statuses["T431"] = "FAIL"
        blockers.append("T431_REVIEW_PACKET_NOT_READY")

    # Check T432
    if checklist_interpretation:
        if (checklist_interpretation.get("ok") is True and
                checklist_interpretation.get("final_decision") == "READY_FOR_MANUAL_PRE_DRY_RUN_APPROVAL_ARTIFACT"):
            component_statuses["T432"] = "PASS"
        else:
            component_statuses["T432"] = "FAIL"
            blockers.append("T432_CHECKLIST_NOT_APPROVED")
    else:
        component_statuses["T432"] = "FAIL"
        blockers.append("T432_CHECKLIST_NOT_APPROVED")

    # Check T433
    if approval_artifact:
        if (approval_artifact.get("ok") is True and
                approval_artifact.get("final_decision") == "READY_FOR_MANUAL_PRE_DRY_RUN_FINAL_GATE"):
            component_statuses["T433"] = "PASS"
        else:
            component_statuses["T433"] = "FAIL"
            blockers.append("T433_APPROVAL_ARTIFACT_NOT_READY")
    else:
        component_statuses["T433"] = "FAIL"
        blockers.append("T433_APPROVAL_ARTIFACT_NOT_READY")

    # Check T434
    if final_gate_report:
        if (final_gate_report.get("ok") is True and
                final_gate_report.get("final_decision") == "READY_FOR_TESTNET_DRY_RUN_PLANNING_REVIEW"):
            component_statuses["T434"] = "PASS"
        else:
            component_statuses["T434"] = "FAIL"
            blockers.append("T434_FINAL_GATE_NOT_PASSED")
    else:
        component_statuses["T434"] = "FAIL"
        blockers.append("T434_FINAL_GATE_NOT_PASSED")

    # Check execution block (safety invariants across all components)
    execution_block_ok = True
    all_reports = [review_packet, checklist_interpretation, approval_artifact, final_gate_report]
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

    # Determine final status
    if (component_statuses["T431"] == "PASS" and
            component_statuses["T432"] == "PASS" and
            component_statuses["T433"] == "PASS" and
            component_statuses["T434"] == "PASS" and
            component_statuses["EXECUTION_BLOCK"] == "PASS"):
        ok = True
        phase_completion_status = "COMPLETED_PENDING_TESTNET_DRY_RUN_PLANNING_REVIEW"
        current_phase = "MANUAL_PRE_DRY_RUN_REVIEW"
        next_phase = "TESTNET_DRY_RUN_PLANNING_REVIEW"
        final_decision = "READY_FOR_TESTNET_DRY_RUN_PLANNING_REVIEW"
    else:
        ok = False
        phase_completion_status = "BLOCKED"
        current_phase = "MANUAL_PRE_DRY_RUN_REVIEW"
        next_phase = "MANUAL_PRE_DRY_RUN_REVIEW"
        final_decision = "CONTINUE_MANUAL_PRE_DRY_RUN_REVIEW"

    return {
        "ok": ok,
        "task": "T435",
        "phase": "MANUAL_PRE_DRY_RUN_REVIEW",
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
        description="Generate MANUAL_PRE_DRY_RUN_REVIEW phase control report"
    )
    parser.add_argument("--review-packet", type=str, required=True, help="Path to T431 review packet JSON")
    parser.add_argument("--checklist-interpretation", type=str, required=True, help="Path to T432 checklist interpretation JSON")
    parser.add_argument("--approval-artifact", type=str, required=True, help="Path to T433 approval artifact JSON")
    parser.add_argument("--final-gate-report", type=str, required=True, help="Path to T434 final gate report JSON")
    parser.add_argument("--output", type=str, help="Path to write output JSON")
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
        final_gate_report
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
