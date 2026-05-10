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
    "GENERATE_PRE_DRY_RUN_READINESS_INPUT_PACKET",
    "MANUAL_REVIEW_ONLY"
]

BLOCKED_ACTIONS = list(REQUIRED_BLOCKED_ACTIONS)


def verify_safety_gates(
    packet: Optional[Dict[str, Any]],
    input_path: str
) -> Dict[str, Any]:
    ok = False
    safety_gate_status = "UNKNOWN"
    violations: List[str] = []
    notes: List[str] = []

    # Get input packet data (or safe defaults)
    input_safety_flags = packet.get("safety_flags", {}) if packet else {}
    input_allowed_actions = packet.get("allowed_actions", []) if packet else []
    input_blocked_actions = packet.get("blocked_actions", []) if packet else []

    # Check each safety flag
    if input_safety_flags.get("testnet_dry_run_allowed", False) is True:
        violations.append("testnet_dry_run_allowed is true")
    if input_safety_flags.get("testnet_submit_allowed", False) is True:
        violations.append("testnet_submit_allowed is true")
    if input_safety_flags.get("real_submit_allowed", False) is True:
        violations.append("real_submit_allowed is true")
    if input_safety_flags.get("submit_attempted", False) is True:
        violations.append("submit_attempted is true")
    if input_safety_flags.get("cancel_attempted", False) is True:
        violations.append("cancel_attempted is true")
    if input_safety_flags.get("flatten_attempted", False) is True:
        violations.append("flatten_attempted is true")

    # Check allowed actions don't contain blocked actions
    for blocked_action in REQUIRED_BLOCKED_ACTIONS:
        if blocked_action in input_allowed_actions:
            violations.append(f"allowed_actions contains {blocked_action}")

    # Check blocked actions contain all required
    for required in REQUIRED_BLOCKED_ACTIONS:
        if required not in input_blocked_actions:
            violations.append(f"blocked_actions missing {required}")

    # Determine status and decision
    if not violations:
        ok = True
        safety_gate_status = "ALL_EXECUTION_GATES_BLOCKED"
        final_decision = "SAFETY_GATES_VERIFIED_FOR_PRE_DRY_RUN_REVIEW"
    else:
        ok = False
        safety_gate_status = "SAFETY_GATE_VIOLATION"
        final_decision = "BLOCK_PRE_DRY_RUN_REVIEW"

    # Build checked flags dict
    checked_flags = {
        "testnet_dry_run_allowed": input_safety_flags.get("testnet_dry_run_allowed", False),
        "testnet_submit_allowed": input_safety_flags.get("testnet_submit_allowed", False),
        "real_submit_allowed": input_safety_flags.get("real_submit_allowed", False),
        "submit_attempted": input_safety_flags.get("submit_attempted", False),
        "cancel_attempted": input_safety_flags.get("cancel_attempted", False),
        "flatten_attempted": input_safety_flags.get("flatten_attempted", False)
    }

    # Build allowed/blocked check dicts
    allowed_actions_check = {action: (action not in REQUIRED_BLOCKED_ACTIONS) for action in input_allowed_actions}
    blocked_actions_check = {action: (action in input_blocked_actions) for action in REQUIRED_BLOCKED_ACTIONS}

    return {
        "ok": ok,
        "task": "T427",
        "phase": "PRE_DRY_RUN_READINESS_REVIEW",
        "input_packet": input_path,
        "safety_gate_status": safety_gate_status,
        "checked_flags": checked_flags,
        "allowed_actions_check": allowed_actions_check,
        "blocked_actions_check": blocked_actions_check,
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
        description="Verify pre-dry-run safety gates"
    )
    parser.add_argument("--input-packet", type=str, required=True, help="Path to T426 input packet JSON")
    parser.add_argument("--output", type=str, help="Path to write output JSON")
    parser.add_argument("--json", action="store_true", help="Print JSON to stdout")

    args = parser.parse_args(argv)

    packet = load_json(args.input_packet)
    report = verify_safety_gates(packet, args.input_packet)

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
