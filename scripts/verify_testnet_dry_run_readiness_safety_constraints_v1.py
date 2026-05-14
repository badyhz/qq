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
    "VERIFY_TESTNET_DRY_RUN_READINESS_SAFETY_CONSTRAINTS",
    "MANUAL_REVIEW_ONLY"
]

BLOCKED_ACTIONS = list(REQUIRED_BLOCKED_ACTIONS)


def verify_safety_constraints(
    readiness_packet: Optional[Dict[str, Any]],
    readiness_path: str
) -> Dict[str, Any]:
    violations = []
    ok = False
    safety_packet = readiness_packet.get("safety_flags", {}) if readiness_packet else {}
    allowed_actions_packet = readiness_packet.get("allowed_actions", []) if readiness_packet else []
    blocked_actions_packet = readiness_packet.get("blocked_actions", []) if readiness_packet else []

    if not (readiness_packet and readiness_packet.get("ok") is True and
            readiness_packet.get("final_decision") == "READY_FOR_TESTNET_DRY_RUN_READINESS_SAFETY_CONSTRAINT_REVIEW"):
        violations.append("READINESS_INPUT_PACKET_NOT_READY")
    else:
        if safety_packet.get("testnet_dry_run_allowed") is True:
            violations.append("TESTNET_DRY_RUN_NOT_BLOCKED")
        if safety_packet.get("testnet_submit_allowed") is True:
            violations.append("TESTNET_SUBMIT_NOT_BLOCKED")
        if safety_packet.get("real_submit_allowed") is True:
            violations.append("REAL_SUBMIT_NOT_BLOCKED")
        if safety_packet.get("submit_attempted") is True:
            violations.append("SUBMIT_ATTEMPTED")
        if safety_packet.get("cancel_attempted") is True:
            violations.append("CANCEL_ATTEMPTED")
        if safety_packet.get("flatten_attempted") is True:
            violations.append("FLATTEN_ATTEMPTED")

        for blocked in REQUIRED_BLOCKED_ACTIONS:
            if blocked in allowed_actions_packet:
                violations.append("ALLOWED_ACTION_CONTAINS_BLOCKED_ACTION")
                break

        for blocked in REQUIRED_BLOCKED_ACTIONS:
            if blocked not in blocked_actions_packet:
                violations.append("BLOCKED_ACTION_MISSING")
                break

    if not violations:
        ok = True
        safety_constraint_status = "TESTNET_DRY_RUN_READINESS_SAFETY_CONSTRAINTS_VERIFIED"
        final_decision = "READY_FOR_TESTNET_DRY_RUN_ARTIFACT_DEPENDENCY_REVIEW"
    else:
        safety_constraint_status = "SAFETY_CONSTRAINT_VIOLATION"
        final_decision = "BLOCK_TESTNET_DRY_RUN_READINESS_REVIEW"

    return {
        "ok": ok,
        "task": "T442",
        "phase": "TESTNET_DRY_RUN_READINESS_REVIEW",
        "source_reports": {
            "readiness_input_packet": readiness_path
        },
        "safety_constraint_status": safety_constraint_status,
        "checked_constraints": [
            "TESTNET_DRY_RUN_BLOCKED",
            "TESTNET_SUBMIT_BLOCKED",
            "REAL_SUBMIT_BLOCKED",
            "NO_SUBMIT_ATTEMPTED",
            "NO_CANCEL_ATTEMPTED",
            "NO_FLATTEN_ATTEMPTED",
            "NO_BLOCKED_ACTIONS_IN_ALLOWED",
            "ALL_BLOCKED_ACTIONS_PRESENT"
        ],
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
        "notes": []
    }


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        description="Verify TESTNET_DRY_RUN_READINESS_REVIEW safety constraints"
    )
    parser.add_argument("--readiness-input-packet", type=str, required=True, help="Path to T441 readiness input packet JSON")
    parser.add_argument("--output", type=str, help="Path to write output JSON")
    parser.add_argument("--json", action="store_true", help="Print JSON to stdout")

    args = parser.parse_args(argv)

    readiness_packet = load_json(args.readiness_input_packet)
    report = verify_safety_constraints(readiness_packet, args.readiness_input_packet)

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
