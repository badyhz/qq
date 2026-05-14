#!/usr/bin/env python3
import argparse
import json
import os
import sys
from typing import Any, Dict, Optional


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

CHECKLIST_ITEMS = [
    "REVIEW_T441_READINESS_INPUT",
    "REVIEW_T442_SAFETY_CONSTRAINTS",
    "REVIEW_T443_ARTIFACT_DEPENDENCIES",
    "REVIEW_T444_READINESS_SCORE",
    "REVIEW_T445_PHASE_CONTROL",
    "CONFIRM_TESTNET_DRY_RUN_STILL_BLOCKED",
    "CONFIRM_NO_SUBMIT_CANCEL_FLATTEN",
    "CONFIRM_OPERATOR_APPROVAL_REQUIRED",
]

ALLOWED_ACTIONS = [
    "READ_REPORTS",
    "GENERATE_MANUAL_TESTNET_DRY_RUN_APPROVAL_REVIEW_PACKET",
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


def generate_review_packet(
    readiness_phase_report: Optional[Dict[str, Any]], readiness_phase_report_path: str
) -> Dict[str, Any]:
    ready = (
        readiness_phase_report
        and readiness_phase_report.get("ok") is True
        and readiness_phase_report.get("phase_completion_status")
        == "COMPLETED_PENDING_MANUAL_TESTNET_DRY_RUN_APPROVAL_REVIEW"
        and readiness_phase_report.get("final_decision")
        == "READY_FOR_MANUAL_TESTNET_DRY_RUN_APPROVAL_REVIEW"
    )

    if ready:
        ok = True
        review_packet_status = "READY_FOR_MANUAL_TESTNET_DRY_RUN_APPROVAL_CHECKLIST"
        required_manual_decision = "APPROVE_OR_REJECT_TESTNET_DRY_RUN_ENABLEMENT_REVIEW"
        final_decision = "READY_FOR_MANUAL_TESTNET_DRY_RUN_APPROVAL_CHECKLIST"
    else:
        ok = False
        review_packet_status = "BLOCKED"
        required_manual_decision = None
        final_decision = "CONTINUE_TESTNET_DRY_RUN_READINESS_REVIEW"

    return {
        "ok": ok,
        "task": "T446",
        "phase": "MANUAL_TESTNET_DRY_RUN_APPROVAL_REVIEW",
        "source_reports": {"readiness_phase_report": readiness_phase_report_path},
        "review_packet_status": review_packet_status,
        "checklist_items": list(CHECKLIST_ITEMS),
        "required_manual_decision": required_manual_decision,
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
        description="Generate MANUAL_TESTNET_DRY_RUN_APPROVAL_REVIEW packet"
    )
    parser.add_argument(
        "--readiness-phase-report",
        required=True,
        help="Path to T445 readiness phase control report JSON",
    )
    parser.add_argument("--output", help="Path to write output JSON")
    parser.add_argument("--json", action="store_true", help="Print JSON to stdout")
    args = parser.parse_args(argv)

    readiness_phase_report = load_json(args.readiness_phase_report)
    report = generate_review_packet(readiness_phase_report, args.readiness_phase_report)

    if args.output:
        if not write_json(args.output, report):
            print("Failed to write output", file=sys.stderr)
            return 1

    if args.json or not args.output:
        print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))

    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
