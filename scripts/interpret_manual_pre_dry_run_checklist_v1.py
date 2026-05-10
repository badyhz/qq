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
    "INTERPRET_MANUAL_PRE_DRY_RUN_CHECKLIST",
    "MANUAL_REVIEW_ONLY"
]

BLOCKED_ACTIONS = list(REQUIRED_BLOCKED_ACTIONS)

REQUIRED_CHECKLIST_ITEMS = [
    "REVIEW_T426_INPUT_PACKET",
    "REVIEW_T427_SAFETY_GATES",
    "REVIEW_T428_DATA_LINEAGE_LEDGER",
    "REVIEW_T429_READINESS_SCORE",
    "REVIEW_T430_PHASE_CONTROL",
    "CONFIRM_TESTNET_DRY_RUN_STILL_BLOCKED",
    "CONFIRM_NO_SUBMIT_CANCEL_FLATTEN"
]


def interpret_checklist(
    review_packet: Optional[Dict[str, Any]],
    checklist_result: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    ok = False
    notes: List[str] = []
    missing_items: List[str] = []
    failed_items: List[str] = []
    reviewer = "UNKNOWN"

    # First check review packet is valid
    if not review_packet or review_packet.get("ok") is not True:
        checklist_status = "MANUAL_PRE_DRY_RUN_CHECKLIST_REJECTED_OR_INCOMPLETE"
        final_decision = "CONTINUE_MANUAL_PRE_DRY_RUN_REVIEW"
        return {
            "ok": ok,
            "task": "T432",
            "phase": "MANUAL_PRE_DRY_RUN_REVIEW",
            "checklist_status": checklist_status,
            "missing_items": missing_items,
            "failed_items": failed_items,
            "reviewer": reviewer,
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

    if checklist_result:
        reviewer = checklist_result.get("reviewer", "UNKNOWN")
        approved = checklist_result.get("approved", False)
        checklist = checklist_result.get("checklist", {})

        # Check all required items present
        for item in REQUIRED_CHECKLIST_ITEMS:
            if item not in checklist:
                missing_items.append(item)

        # Check all items are True
        if not missing_items:
            for item in REQUIRED_CHECKLIST_ITEMS:
                if checklist.get(item) is not True:
                    failed_items.append(item)

        # Determine final status
        if approved and not missing_items and not failed_items:
            ok = True
            checklist_status = "MANUAL_PRE_DRY_RUN_CHECKLIST_APPROVED"
            final_decision = "READY_FOR_MANUAL_PRE_DRY_RUN_APPROVAL_ARTIFACT"
        else:
            ok = False
            checklist_status = "MANUAL_PRE_DRY_RUN_CHECKLIST_REJECTED_OR_INCOMPLETE"
            final_decision = "CONTINUE_MANUAL_PRE_DRY_RUN_REVIEW"
    else:
        ok = False
        checklist_status = "MANUAL_PRE_DRY_RUN_CHECKLIST_REJECTED_OR_INCOMPLETE"
        final_decision = "CONTINUE_MANUAL_PRE_DRY_RUN_REVIEW"

    return {
        "ok": ok,
        "task": "T432",
        "phase": "MANUAL_PRE_DRY_RUN_REVIEW",
        "checklist_status": checklist_status,
        "missing_items": missing_items,
        "failed_items": failed_items,
        "reviewer": reviewer,
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
        description="Interpret MANUAL_PRE_DRY_RUN_REVIEW checklist"
    )
    parser.add_argument("--review-packet", type=str, required=True, help="Path to T431 review packet JSON")
    parser.add_argument("--checklist-result", type=str, required=True, help="Path to checklist result JSON")
    parser.add_argument("--output", type=str, help="Path to write output JSON")
    parser.add_argument("--json", action="store_true", help="Print JSON to stdout")

    args = parser.parse_args(argv)

    review_packet = load_json(args.review_packet)
    checklist_result = load_json(args.checklist_result)

    report = interpret_checklist(review_packet, checklist_result)

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
