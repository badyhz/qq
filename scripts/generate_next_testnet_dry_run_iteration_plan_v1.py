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

NEXT_ITERATION_STEPS = [
    "SELECT_NEXT_DRY_RUN_CANDIDATE_INPUT",
    "BUILD_NO_SUBMIT_PAYLOAD_PLAN",
    "MATERIALIZE_PAYLOAD_ARTIFACT",
    "GENERATE_EXECUTION_RESULT_REPORT",
    "VERIFY_NO_SUBMIT_EVIDENCE",
    "REVIEW_ITERATION_RESULT",
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


def generate_iteration_plan(blocker_analysis_report: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    ready = bool(
        blocker_analysis_report
        and blocker_analysis_report.get("ok") is True
        and blocker_analysis_report.get("blocker_analysis_status") == "DRY_RUN_RESULT_BLOCKER_ANALYSIS_COMPLETED"
        and blocker_analysis_report.get("final_decision") == "READY_FOR_NEXT_DRY_RUN_ITERATION_PLAN"
    )

    if ready:
        ok = True
        status = "NEXT_DRY_RUN_ITERATION_PLAN_READY"
        scope = "NEXT_ARTIFACT_ONLY_NO_SUBMIT_DRY_RUN_ITERATION"
        final_decision = "READY_FOR_DRY_RUN_ITERATION_APPROVAL_ARTIFACT"
        safety_flags = _safety_flags(True)
        allowed_actions = list(ALLOWED_PASS)
    else:
        ok = False
        status = "BLOCKED"
        scope = None
        final_decision = "CONTINUE_TESTNET_DRY_RUN_ITERATION_REVIEW"
        safety_flags = _safety_flags(False)
        allowed_actions = list(ALLOWED_BLOCKED)

    return {
        "ok": ok,
        "task": "T473",
        "phase": "TESTNET_DRY_RUN_ITERATION_REVIEW",
        "iteration_plan_status": status,
        "next_iteration_scope": scope,
        "next_iteration_steps": list(NEXT_ITERATION_STEPS),
        "safety_flags": safety_flags,
        "allowed_actions": allowed_actions,
        "blocked_actions": list(REQUIRED_BLOCKED_ACTIONS),
        "final_decision": final_decision,
        "notes": [],
    }


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    parser = argparse.ArgumentParser(description="Generate next TESTNET_DRY_RUN iteration plan")
    parser.add_argument("--blocker-analysis-report", required=True)
    parser.add_argument("--output")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    report = generate_iteration_plan(load_json(args.blocker_analysis_report))

    if args.output and not write_json(args.output, report):
        print("Failed to write output", file=sys.stderr)
        return 1
    if args.json or not args.output:
        print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))

    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
