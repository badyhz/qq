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
    "VERIFY_TESTNET_DRY_RUN_PLAN_CONSTRAINTS",
    "TESTNET_DRY_RUN_PLANNING_ONLY"
]

BLOCKED_ACTIONS = list(REQUIRED_BLOCKED_ACTIONS)


def verify_plan_constraints(
    planning_packet: Optional[Dict[str, Any]],
    dry_run_plan: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    ok = False
    notes: List[str] = []
    violations: List[str] = []

    checked_constraints = [
        "MODE_CHECK",
        "EXCHANGE_API_CALLS_CHECK",
        "SUBMIT_ORDER_CHECK",
        "CANCEL_ORDER_CHECK",
        "FLATTEN_POSITION_CHECK",
        "INPUT_ARTIFACTS_CHECK",
        "OUTPUT_ARTIFACTS_CHECK",
        "OPERATOR_REVIEW_CHECK",
        "ROLLBACK_PLAN_CHECK"
    ]

    if not planning_packet or planning_packet.get("ok") is not True:
        violations.append("PLANNING_PACKET_NOT_READY")
    elif not dry_run_plan:
        violations.append("PLANNING_PACKET_NOT_READY")
    else:
        if dry_run_plan.get("mode") != "TESTNET_DRY_RUN_PLANNING_ONLY":
            violations.append("INVALID_MODE")

        if dry_run_plan.get("exchange_api_calls") is not False:
            violations.append("EXCHANGE_API_CALLS_NOT_ALLOWED")

        if dry_run_plan.get("submit_order") is not False:
            violations.append("SUBMIT_ORDER_NOT_ALLOWED")

        if dry_run_plan.get("cancel_order") is not False:
            violations.append("CANCEL_ORDER_NOT_ALLOWED")

        if dry_run_plan.get("flatten_position") is not False:
            violations.append("FLATTEN_POSITION_NOT_ALLOWED")

        input_artifacts = dry_run_plan.get("input_artifacts", [])
        if not input_artifacts or len(input_artifacts) == 0:
            violations.append("INPUT_ARTIFACTS_MISSING")

        output_artifacts = dry_run_plan.get("output_artifacts", [])
        if not output_artifacts or len(output_artifacts) == 0:
            violations.append("OUTPUT_ARTIFACTS_MISSING")

        if dry_run_plan.get("operator_review_required") is not True:
            violations.append("OPERATOR_REVIEW_NOT_REQUIRED")

        rollback_plan = dry_run_plan.get("rollback_plan", "")
        if not rollback_plan or len(rollback_plan.strip()) == 0:
            violations.append("ROLLBACK_PLAN_MISSING")

    if len(violations) == 0:
        ok = True
        constraint_status = "TESTNET_DRY_RUN_PLAN_CONSTRAINTS_VERIFIED"
        final_decision = "READY_FOR_TESTNET_DRY_RUN_PLAN_RISK_REVIEW"
    else:
        ok = False
        constraint_status = "TESTNET_DRY_RUN_PLAN_CONSTRAINT_VIOLATION"
        final_decision = "BLOCK_TESTNET_DRY_RUN_PLANNING_REVIEW"

    return {
        "ok": ok,
        "task": "T437",
        "phase": "TESTNET_DRY_RUN_PLANNING_REVIEW",
        "constraint_status": constraint_status,
        "checked_constraints": checked_constraints,
        "violations": violations,
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
        description="Verify TESTNET_DRY_RUN_PLAN constraints"
    )
    parser.add_argument("--planning-packet", type=str, required=True, help="Path to T436 planning packet JSON")
    parser.add_argument("--dry-run-plan", type=str, required=True, help="Path to dry-run plan JSON")
    parser.add_argument("--output", type=str, help="Path to write output JSON")
    parser.add_argument("--json", action="store_true", help="Print JSON to stdout")

    args = parser.parse_args(argv)

    planning_packet = load_json(args.planning_packet)
    dry_run_plan = load_json(args.dry_run_plan)

    report = verify_plan_constraints(planning_packet, dry_run_plan)

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
