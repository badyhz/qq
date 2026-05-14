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

REQUIRED_CHECKLIST_ITEMS = [
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
    "INTERPRET_MANUAL_TESTNET_DRY_RUN_APPROVAL_CHECKLIST",
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


def interpret_checklist(
    review_packet: Optional[Dict[str, Any]],
    checklist_result: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    missing_items: List[str] = []
    failed_items: List[str] = []

    review_packet_ready = (
        review_packet
        and review_packet.get("ok") is True
        and review_packet.get("final_decision")
        == "READY_FOR_MANUAL_TESTNET_DRY_RUN_APPROVAL_CHECKLIST"
    )

    approved = bool(checklist_result.get("approved") is True) if checklist_result else False
    checklist = checklist_result.get("checklist") if checklist_result else {}
    if not isinstance(checklist, dict):
        checklist = {}

    for item in REQUIRED_CHECKLIST_ITEMS:
        if item not in checklist:
            missing_items.append(item)
        elif checklist.get(item) is not True:
            failed_items.append(item)

    ok = review_packet_ready and approved and not missing_items and not failed_items

    if ok:
        checklist_status = "MANUAL_TESTNET_DRY_RUN_APPROVAL_CHECKLIST_APPROVED"
        final_decision = "READY_FOR_MANUAL_TESTNET_DRY_RUN_APPROVAL_ARTIFACT"
    else:
        checklist_status = "MANUAL_TESTNET_DRY_RUN_APPROVAL_CHECKLIST_REJECTED_OR_INCOMPLETE"
        final_decision = "CONTINUE_MANUAL_TESTNET_DRY_RUN_APPROVAL_REVIEW"

    reviewer = checklist_result.get("reviewer") if checklist_result else None
    notes: List[str] = []
    if checklist_result and checklist_result.get("notes") is not None:
        notes.append(str(checklist_result.get("notes")))

    return {
        "ok": ok,
        "task": "T447",
        "phase": "MANUAL_TESTNET_DRY_RUN_APPROVAL_REVIEW",
        "checklist_status": checklist_status,
        "missing_items": missing_items,
        "failed_items": failed_items,
        "reviewer": reviewer,
        "safety_flags": dict(SAFETY_FLAGS),
        "allowed_actions": list(ALLOWED_ACTIONS),
        "blocked_actions": list(BLOCKED_ACTIONS),
        "final_decision": final_decision,
        "notes": notes,
    }


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        description="Interpret MANUAL_TESTNET_DRY_RUN_APPROVAL_REVIEW checklist"
    )
    parser.add_argument("--review-packet", required=True, help="Path to T446 review packet JSON")
    parser.add_argument("--checklist-result", required=True, help="Path to checklist result JSON")
    parser.add_argument("--output", help="Path to write output JSON")
    parser.add_argument("--json", action="store_true", help="Print JSON to stdout")
    args = parser.parse_args(argv)

    review_packet = load_json(args.review_packet)
    checklist_result = load_json(args.checklist_result)
    report = interpret_checklist(review_packet, checklist_result)

    if args.output:
        if not write_json(args.output, report):
            print("Failed to write output", file=sys.stderr)
            return 1

    if args.json or not args.output:
        print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))

    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
