#!/usr/bin/env python3
import argparse
import json
import os
import sys
from typing import Any, Dict, Optional

REQUIRED_BLOCKED_ACTIONS = [
    "EXCHANGE_API_CALL",
    "TESTNET_SUBMIT",
    "REAL_SUBMIT",
    "SUBMIT_ORDER",
    "CANCEL_ORDER",
    "FLATTEN_POSITION",
]

ALLOWED_PASS = [
    "READ_REPORTS",
    "TESTNET_DRY_RUN_ONLY",
    "REVIEW_DRY_RUN_ARTIFACTS",
    "GENERATE_NEXT_DRY_RUN_PLAN",
]
ALLOWED_BLOCKED = ["READ_REPORTS", "REVIEW_DRY_RUN_ARTIFACTS", "GENERATE_NEXT_DRY_RUN_PLAN"]


def _safety_flags(dry_run_allowed: bool) -> Dict[str, Any]:
    return {
        "testnet_dry_run_allowed": dry_run_allowed,
        "exchange_api_calls_allowed": False,
        "testnet_submit_allowed": False,
        "real_submit_allowed": False,
        "submit_order_allowed": False,
        "cancel_order_allowed": False,
        "flatten_position_allowed": False,
        "submit_attempted": False,
        "cancel_attempted": False,
        "flatten_attempted": False,
    }


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


def generate_iteration_approval_artifact(iteration_plan: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    ready = bool(
        iteration_plan
        and iteration_plan.get("ok") is True
        and iteration_plan.get("iteration_plan_status") == "NEXT_DRY_RUN_ITERATION_PLAN_READY"
        and iteration_plan.get("final_decision") == "READY_FOR_DRY_RUN_ITERATION_APPROVAL_ARTIFACT"
    )

    if ready:
        ok = True
        approval_status = "NEXT_DRY_RUN_ITERATION_APPROVED"
        approval_scope = "APPROVE_NEXT_ARTIFACT_ONLY_NO_SUBMIT_DRY_RUN_ITERATION"
        final_decision = "READY_FOR_DRY_RUN_ITERATION_REVIEW_PHASE_CONTROL"
        safety_flags = _safety_flags(True)
        allowed_actions = list(ALLOWED_PASS)
    else:
        ok = False
        approval_status = "BLOCKED"
        approval_scope = None
        final_decision = "CONTINUE_TESTNET_DRY_RUN_ITERATION_REVIEW"
        safety_flags = _safety_flags(False)
        allowed_actions = list(ALLOWED_BLOCKED)

    return {
        "ok": ok,
        "task": "T474",
        "phase": "TESTNET_DRY_RUN_ITERATION_REVIEW",
        "approval_status": approval_status,
        "approval_scope": approval_scope,
        "approval_limitations": [
            "NO_EXCHANGE_API_CALL",
            "NO_TESTNET_SUBMIT",
            "NO_REAL_SUBMIT",
            "NO_SUBMIT_ORDER",
            "NO_CANCEL_ORDER",
            "NO_FLATTEN_POSITION",
        ],
        "safety_flags": safety_flags,
        "allowed_actions": allowed_actions,
        "blocked_actions": list(REQUIRED_BLOCKED_ACTIONS),
        "final_decision": final_decision,
        "notes": [],
    }


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    parser = argparse.ArgumentParser(description="Generate TESTNET_DRY_RUN iteration approval artifact")
    parser.add_argument("--iteration-plan", required=True)
    parser.add_argument("--output")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    report = generate_iteration_approval_artifact(load_json(args.iteration_plan))

    if args.output and not write_json(args.output, report):
        print("Failed to write output", file=sys.stderr)
        return 1
    if args.json or not args.output:
        print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))

    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
