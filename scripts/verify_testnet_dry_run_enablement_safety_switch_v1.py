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

SAFETY_FLAGS = {
    "shadow_only": True,
    "testnet_dry_run_allowed": False,
    "testnet_submit_allowed": False,
    "real_submit_allowed": False,
    "submit_attempted": False,
    "cancel_attempted": False,
    "flatten_attempted": False,
}

ALLOWED_ACTIONS = [
    "READ_REPORTS",
    "VERIFY_TESTNET_DRY_RUN_ENABLEMENT_SAFETY_SWITCH",
    "MANUAL_REVIEW_ONLY",
]

BLOCKED_ACTIONS = list(REQUIRED_BLOCKED_ACTIONS)


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


def verify_safety_switch(
    enablement_packet: Optional[Dict[str, Any]],
    safety_switch_config: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    violations: List[str] = []

    if not (enablement_packet and enablement_packet.get("ok") is True):
        violations.append("ENABLEMENT_PACKET_NOT_READY")

    config = safety_switch_config or {}

    if config.get("mode") != "TESTNET_DRY_RUN_ONLY":
        violations.append("INVALID_MODE")

    if config.get("enable_testnet_dry_run_only") is not True:
        violations.append("TESTNET_DRY_RUN_ONLY_NOT_ENABLED_IN_CONFIG")

    if config.get("testnet_submit_allowed") is not False:
        violations.append("TESTNET_SUBMIT_NOT_ALLOWED")

    if config.get("real_submit_allowed") is not False:
        violations.append("REAL_SUBMIT_NOT_ALLOWED")

    if config.get("submit_order_allowed") is not False:
        violations.append("SUBMIT_ORDER_NOT_ALLOWED")

    if config.get("cancel_order_allowed") is not False:
        violations.append("CANCEL_ORDER_NOT_ALLOWED")

    if config.get("flatten_position_allowed") is not False:
        violations.append("FLATTEN_POSITION_NOT_ALLOWED")

    if config.get("operator_confirmation_required") is not True:
        violations.append("OPERATOR_CONFIRMATION_NOT_REQUIRED")

    if config.get("manual_final_gate_required") is not True:
        violations.append("MANUAL_FINAL_GATE_NOT_REQUIRED")

    ok = len(violations) == 0

    if ok:
        safety_switch_status = "TESTNET_DRY_RUN_ENABLEMENT_SAFETY_SWITCH_VERIFIED"
        final_decision = "READY_FOR_TESTNET_DRY_RUN_OPERATOR_CONFIRMATION"
    else:
        safety_switch_status = "SAFETY_SWITCH_VIOLATION"
        final_decision = "BLOCK_TESTNET_DRY_RUN_ENABLEMENT_REVIEW"

    return {
        "ok": ok,
        "task": "T452",
        "phase": "TESTNET_DRY_RUN_ENABLEMENT_REVIEW",
        "safety_switch_status": safety_switch_status,
        "checked_constraints": [
            "ENABLEMENT_PACKET_READY",
            "MODE_TESTNET_DRY_RUN_ONLY",
            "ENABLE_TESTNET_DRY_RUN_ONLY_TRUE",
            "TESTNET_SUBMIT_BLOCKED",
            "REAL_SUBMIT_BLOCKED",
            "SUBMIT_ORDER_BLOCKED",
            "CANCEL_ORDER_BLOCKED",
            "FLATTEN_POSITION_BLOCKED",
            "OPERATOR_CONFIRMATION_REQUIRED",
            "MANUAL_FINAL_GATE_REQUIRED",
        ],
        "violations": violations,
        "safety_flags": dict(SAFETY_FLAGS),
        "allowed_actions": list(ALLOWED_ACTIONS),
        "blocked_actions": list(BLOCKED_ACTIONS),
        "final_decision": final_decision,
        "notes": [],
    }


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        description="Verify TESTNET_DRY_RUN enablement safety switch"
    )
    parser.add_argument("--enablement-packet", required=True, help="Path to T451 enablement packet JSON")
    parser.add_argument("--safety-switch-config", required=True, help="Path to safety switch config JSON")
    parser.add_argument("--output", help="Path to write output JSON")
    parser.add_argument("--json", action="store_true", help="Print JSON to stdout")
    args = parser.parse_args(argv)

    enablement_packet = load_json(args.enablement_packet)
    safety_switch_config = load_json(args.safety_switch_config)
    report = verify_safety_switch(enablement_packet, safety_switch_config)

    if args.output:
        if not write_json(args.output, report):
            print("Failed to write output", file=sys.stderr)
            return 1

    if args.json or not args.output:
        print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))

    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
