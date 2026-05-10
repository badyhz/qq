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
    "GENERATE_TESTNET_DRY_RUN_PLANNING_APPROVAL_ARTIFACT",
    "TESTNET_DRY_RUN_PLANNING_ONLY"
]

BLOCKED_ACTIONS = list(REQUIRED_BLOCKED_ACTIONS)


def generate_approval_artifact(
    risk_review_report: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    ok = False
    notes: List[str] = []

    if risk_review_report:
        t438_ok = risk_review_report.get("ok") is True
        t438_risk_status = risk_review_report.get("risk_review_status") == "TESTNET_DRY_RUN_PLAN_RISK_REVIEW_PASSED"
        t438_final_decision = risk_review_report.get("final_decision") == "READY_FOR_TESTNET_DRY_RUN_PLANNING_APPROVAL_ARTIFACT"

        if t438_ok and t438_risk_status and t438_final_decision:
            ok = True
            approval_status = "TESTNET_DRY_RUN_PLANNING_APPROVED"
            approval_scope = "APPROVE_TESTNET_DRY_RUN_READINESS_REVIEW_ONLY"
            approval_limitations = [
                "TESTNET_DRY_RUN_ONLY_STILL_BLOCKED",
                "NO_EXCHANGE_API_CALLS_ALLOWED",
                "NO_ORDER_SUBMIT_ALLOWED",
                "NO_CANCEL_OR_FLATTEN_ALLOWED",
                "ONLY_READINESS_REVIEW_APPROVED"
            ]
            final_decision = "READY_FOR_TESTNET_DRY_RUN_PLANNING_FINAL_GATE"
        else:
            ok = False
            approval_status = "BLOCKED"
            approval_scope = "NONE"
            approval_limitations = ["Risk review not passed"]
            final_decision = "CONTINUE_TESTNET_DRY_RUN_PLANNING_REVIEW"
    else:
        ok = False
        approval_status = "BLOCKED"
        approval_scope = "NONE"
        approval_limitations = ["No risk review report provided"]
        final_decision = "CONTINUE_TESTNET_DRY_RUN_PLANNING_REVIEW"

    return {
        "ok": ok,
        "task": "T439",
        "phase": "TESTNET_DRY_RUN_PLANNING_REVIEW",
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
        description="Generate TESTNET_DRY_RUN_PLANNING approval artifact"
    )
    parser.add_argument("--risk-review-report", type=str, required=True, help="Path to T438 risk review report JSON")
    parser.add_argument("--output", type=str, help="Path to write output JSON")
    parser.add_argument("--json", action="store_true", help="Print JSON to stdout")

    args = parser.parse_args(argv)

    risk_review_report = load_json(args.risk_review_report)

    report = generate_approval_artifact(risk_review_report)

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
