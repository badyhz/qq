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
    "GENERATE_TESTNET_DRY_RUN_PLAN_RISK_REVIEW",
    "TESTNET_DRY_RUN_PLANNING_ONLY"
]

BLOCKED_ACTIONS = list(REQUIRED_BLOCKED_ACTIONS)

RISK_ITEMS = [
    "ACCIDENTAL_EXCHANGE_CALL_RISK",
    "ORDER_SUBMISSION_RISK",
    "CANCEL_OR_FLATTEN_RISK",
    "WRONG_ENVIRONMENT_RISK",
    "ARTIFACT_MISMATCH_RISK",
    "OPERATOR_CONFIRMATION_RISK"
]

REQUIRED_CONTROLS = [
    "DRY_RUN_PLANNING_ONLY_MODE",
    "EXCHANGE_API_CALLS_DISABLED",
    "SUBMIT_CANCEL_FLATTEN_DISABLED",
    "MANUAL_OPERATOR_REVIEW_REQUIRED",
    "DETERMINISTIC_ARTIFACTS_REQUIRED"
]


def generate_risk_review(
    constraint_report: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    ok = False
    notes: List[str] = []
    residual_risks: List[str] = [
        "HUMAN_ERROR_IN_CONFIGURATION",
        "DEPENDENCY_BEHAVIOR_CHANGE"
    ]

    if constraint_report:
        t437_ok = constraint_report.get("ok") is True
        t437_constraint_status = constraint_report.get("constraint_status") == "TESTNET_DRY_RUN_PLAN_CONSTRAINTS_VERIFIED"
        t437_final_decision = constraint_report.get("final_decision") == "READY_FOR_TESTNET_DRY_RUN_PLAN_RISK_REVIEW"

        if t437_ok and t437_constraint_status and t437_final_decision:
            ok = True
            risk_review_status = "TESTNET_DRY_RUN_PLAN_RISK_REVIEW_PASSED"
            final_decision = "READY_FOR_TESTNET_DRY_RUN_PLANNING_APPROVAL_ARTIFACT"
        else:
            ok = False
            risk_review_status = "BLOCKED"
            final_decision = "CONTINUE_TESTNET_DRY_RUN_PLANNING_REVIEW"
    else:
        ok = False
        risk_review_status = "BLOCKED"
        final_decision = "CONTINUE_TESTNET_DRY_RUN_PLANNING_REVIEW"

    return {
        "ok": ok,
        "task": "T438",
        "phase": "TESTNET_DRY_RUN_PLANNING_REVIEW",
        "risk_review_status": risk_review_status,
        "risk_items": RISK_ITEMS,
        "residual_risks": residual_risks,
        "required_controls": REQUIRED_CONTROLS,
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
        description="Generate TESTNET_DRY_RUN_PLAN risk review"
    )
    parser.add_argument("--constraint-report", type=str, required=True, help="Path to T437 constraint report JSON")
    parser.add_argument("--output", type=str, help="Path to write output JSON")
    parser.add_argument("--json", action="store_true", help="Print JSON to stdout")

    args = parser.parse_args(argv)

    constraint_report = load_json(args.constraint_report)

    report = generate_risk_review(constraint_report)

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
