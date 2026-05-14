#!/usr/bin/env python3
import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional

REQUIRED_BLOCKED_ACTIONS = [
    "EXCHANGE_API_CALL",
    "TESTNET_SUBMIT",
    "REAL_SUBMIT",
    "SUBMIT_ORDER",
    "CANCEL_ORDER",
    "FLATTEN_POSITION",
]

ALLOWED_ACTIONS = [
    "READ_REPORTS",
    "TESTNET_DRY_RUN_ONLY",
    "REVIEW_DRY_RUN_ARTIFACTS",
    "GENERATE_NEXT_DRY_RUN_ARTIFACT",
]


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


def generate_candidate_input_artifact(execution_packet: Optional[Dict[str, Any]], iteration_plan: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    violations: List[str] = []

    if not (
        execution_packet
        and execution_packet.get("ok") is True
        and execution_packet.get("final_decision") == "READY_FOR_NEXT_DRY_RUN_CANDIDATE_INPUT_ARTIFACT"
    ):
        violations.append("EXECUTION_PACKET_NOT_READY")

    if not (
        iteration_plan
        and iteration_plan.get("ok") is True
        and iteration_plan.get("iteration_plan_status") == "NEXT_DRY_RUN_ITERATION_PLAN_READY"
    ):
        violations.append("ITERATION_PLAN_NOT_READY")

    candidate_input = {
        "candidate_id": "next-dryrun-candidate-001",
        "symbol": "BTCUSDT",
        "side": "BUY",
        "quantity": "0.001",
        "order_type": "MARKET",
        "dry_run_only": True,
        "artifact_only": True,
    }

    if candidate_input.get("dry_run_only") is not True:
        violations.append("CANDIDATE_NOT_DRY_RUN_ONLY")
    if candidate_input.get("artifact_only") is not True:
        violations.append("CANDIDATE_NOT_ARTIFACT_ONLY")

    ok = len(violations) == 0

    if ok:
        status = "NEXT_DRY_RUN_CANDIDATE_INPUT_READY"
        final_decision = "READY_FOR_NEXT_NO_SUBMIT_PAYLOAD_PLAN"
        safety_flags = _safety_flags(True)
    else:
        status = "CANDIDATE_INPUT_BLOCKED"
        final_decision = "BLOCK_NEXT_TESTNET_DRY_RUN_ONLY_ITERATION"
        safety_flags = _safety_flags(False)

    return {
        "ok": ok,
        "task": "T477",
        "phase": "NEXT_TESTNET_DRY_RUN_ONLY_ITERATION",
        "candidate_artifact_status": status,
        "violations": violations,
        "candidate_input": candidate_input if ok else None,
        "candidate_source": "GENERATED_FROM_NEXT_ITERATION_PLAN",
        "safety_flags": safety_flags,
        "allowed_actions": list(ALLOWED_ACTIONS),
        "blocked_actions": list(REQUIRED_BLOCKED_ACTIONS),
        "final_decision": final_decision,
        "notes": [],
    }


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    parser = argparse.ArgumentParser(description="Generate next TESTNET_DRY_RUN candidate input artifact")
    parser.add_argument("--execution-packet", required=True)
    parser.add_argument("--iteration-plan", required=True)
    parser.add_argument("--output")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    report = generate_candidate_input_artifact(load_json(args.execution_packet), load_json(args.iteration_plan))

    if args.output and not write_json(args.output, report):
        print("Failed to write output", file=sys.stderr)
        return 1
    if args.json or not args.output:
        print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))

    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
