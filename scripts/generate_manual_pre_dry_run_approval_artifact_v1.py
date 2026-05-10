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
    "GENERATE_MANUAL_PRE_DRY_RUN_APPROVAL_ARTIFACT",
    "MANUAL_REVIEW_ONLY"
]

BLOCKED_ACTIONS = list(REQUIRED_BLOCKED_ACTIONS)


def generate_approval_artifact(
    checklist_interpretation: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    ok = False
    notes: List[str] = []

    if checklist_interpretation:
        t432_ok = checklist_interpretation.get("ok") is True
        t432_checklist_status = checklist_interpretation.get("checklist_status") == "MANUAL_PRE_DRY_RUN_CHECKLIST_APPROVED"
        t432_final_decision = checklist_interpretation.get("final_decision") == "READY_FOR_MANUAL_PRE_DRY_RUN_APPROVAL_ARTIFACT"

        if t432_ok and t432_checklist_status and t432_final_decision:
            ok = True
            approval_status = "MANUAL_PRE_DRY_RUN_APPROVED"
            approval_scope = "APPROVE_TESTNET_DRY_RUN_PLANNING_REVIEW_ONLY"
            approval_limitations = [
                "TESTNET_DRY_RUN_ONLY still blocked",
                "No submit/cancel/flatten allowed",
                "Only planning review approved"
            ]
            final_decision = "READY_FOR_MANUAL_PRE_DRY_RUN_FINAL_GATE"
        else:
            ok = False
            approval_status = "BLOCKED"
            approval_scope = "NONE"
            approval_limitations = ["Checklist interpretation not approved"]
            final_decision = "CONTINUE_MANUAL_PRE_DRY_RUN_REVIEW"
    else:
        ok = False
        approval_status = "BLOCKED"
        approval_scope = "NONE"
        approval_limitations = ["No checklist interpretation provided"]
        final_decision = "CONTINUE_MANUAL_PRE_DRY_RUN_REVIEW"

    return {
        "ok": ok,
        "task": "T433",
        "phase": "MANUAL_PRE_DRY_RUN_REVIEW",
        "approval_status": approval_status,
        "approval_scope": approval_scope,
        "approval_limitations": approval_limitations,
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
        description="Generate MANUAL_PRE_DRY_RUN_REVIEW approval artifact"
    )
    parser.add_argument("--checklist-interpretation", type=str, required=True, help="Path to T432 checklist interpretation JSON")
    parser.add_argument("--output", type=str, help="Path to write output JSON")
    parser.add_argument("--json", action="store_true", help="Print JSON to stdout")

    args = parser.parse_args(argv)

    checklist_interpretation = load_json(args.checklist_interpretation)

    report = generate_approval_artifact(checklist_interpretation)

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
