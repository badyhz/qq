#!/usr/bin/env python3
import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional


REQUIRED_BLOCKED_ACTIONS = [
    "TESTNET_SUBMIT",
    "REAL_SUBMIT",
    "SUBMIT_ORDER",
    "CANCEL_ORDER",
    "FLATTEN_POSITION",
]

ALLOWED_ACTIONS = [
    "READ_REPORTS",
    "TESTNET_DRY_RUN_ONLY",
    "VERIFY_TESTNET_DRY_RUN_NO_SUBMIT_RUNNER_GUARD",
]

BLOCKED_ACTIONS = list(REQUIRED_BLOCKED_ACTIONS)


def _safety_flags(testnet_dry_run_allowed: bool) -> Dict[str, Any]:
    return {
        "testnet_dry_run_allowed": testnet_dry_run_allowed,
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


def verify_runner_guard(payload_plan: Optional[Dict[str, Any]], runner_config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    violations: List[str] = []
    if not (payload_plan and payload_plan.get("ok") is True):
        violations.append("PAYLOAD_PLAN_NOT_READY")

    cfg = runner_config or {}

    if cfg.get("dry_run_only") is not True:
        violations.append("DRY_RUN_ONLY_NOT_ENABLED")
    if cfg.get("exchange_api_calls_enabled") is not False:
        violations.append("EXCHANGE_API_CALLS_ENABLED")
    if cfg.get("submit_enabled") is not False:
        violations.append("SUBMIT_ENABLED")
    if cfg.get("cancel_enabled") is not False:
        violations.append("CANCEL_ENABLED")
    if cfg.get("flatten_enabled") is not False:
        violations.append("FLATTEN_ENABLED")
    if cfg.get("write_artifacts_only") is not True:
        violations.append("WRITE_ARTIFACTS_ONLY_NOT_ENABLED")
    if cfg.get("operator_review_required") is not True:
        violations.append("OPERATOR_REVIEW_NOT_REQUIRED")

    ok = len(violations) == 0

    if ok:
        runner_guard_status = "NO_SUBMIT_RUNNER_GUARD_VERIFIED"
        final_decision = "READY_FOR_TESTNET_DRY_RUN_ONLY_PREFLIGHT_REPORT"
        safety_flags = _safety_flags(True)
    else:
        runner_guard_status = "NO_SUBMIT_RUNNER_GUARD_VIOLATION"
        final_decision = "BLOCK_TESTNET_DRY_RUN_ONLY_MODE"
        safety_flags = _safety_flags(False)

    return {
        "ok": ok,
        "task": "T458",
        "phase": "TESTNET_DRY_RUN_ONLY_MODE",
        "runner_guard_status": runner_guard_status,
        "checked_guards": [
            "DRY_RUN_ONLY_ENABLED",
            "EXCHANGE_API_CALLS_DISABLED",
            "SUBMIT_DISABLED",
            "CANCEL_DISABLED",
            "FLATTEN_DISABLED",
            "WRITE_ARTIFACTS_ONLY_ENABLED",
            "OPERATOR_REVIEW_REQUIRED",
        ],
        "violations": violations,
        "safety_flags": safety_flags,
        "allowed_actions": list(ALLOWED_ACTIONS),
        "blocked_actions": list(BLOCKED_ACTIONS),
        "final_decision": final_decision,
        "notes": [],
    }


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(description="Verify TESTNET_DRY_RUN no-submit runner guard")
    parser.add_argument("--payload-plan", required=True)
    parser.add_argument("--runner-config", required=True)
    parser.add_argument("--output")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    payload_plan = load_json(args.payload_plan)
    runner_config = load_json(args.runner_config)
    report = verify_runner_guard(payload_plan, runner_config)

    if args.output and not write_json(args.output, report):
        print("Failed to write output", file=sys.stderr)
        return 1

    if args.json or not args.output:
        print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))

    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
