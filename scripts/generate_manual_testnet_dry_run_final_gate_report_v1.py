#!/usr/bin/env python3
import argparse
import json
import os
import sys
from typing import Any, Dict, Optional


REQUIRED_BLOCKED_ACTIONS = [
    "TESTNET_DRY_RUN_ONLY",
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
    "GENERATE_MANUAL_TESTNET_DRY_RUN_FINAL_GATE_REPORT",
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


def generate_final_gate_report(approval_artifact: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    pass_gate = (
        approval_artifact
        and approval_artifact.get("ok") is True
        and approval_artifact.get("approval_status")
        == "MANUAL_TESTNET_DRY_RUN_APPROVED_FOR_ENABLEMENT_REVIEW"
        and approval_artifact.get("final_decision")
        == "READY_FOR_MANUAL_TESTNET_DRY_RUN_FINAL_GATE"
    )

    if pass_gate:
        ok = True
        final_gate_status = "MANUAL_TESTNET_DRY_RUN_FINAL_GATE_PASSED"
        gate_result = "READY_FOR_TESTNET_DRY_RUN_ENABLEMENT_REVIEW"
        final_decision = "READY_FOR_TESTNET_DRY_RUN_ENABLEMENT_REVIEW"
    else:
        ok = False
        final_gate_status = "BLOCKED"
        gate_result = "BLOCKED"
        final_decision = "CONTINUE_MANUAL_TESTNET_DRY_RUN_APPROVAL_REVIEW"

    return {
        "ok": ok,
        "task": "T449",
        "phase": "MANUAL_TESTNET_DRY_RUN_APPROVAL_REVIEW",
        "final_gate_status": final_gate_status,
        "gate_result": gate_result,
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
        description="Generate MANUAL_TESTNET_DRY_RUN final gate report"
    )
    parser.add_argument("--approval-artifact", required=True, help="Path to T448 approval artifact JSON")
    parser.add_argument("--output", help="Path to write output JSON")
    parser.add_argument("--json", action="store_true", help="Print JSON to stdout")
    args = parser.parse_args(argv)

    approval_artifact = load_json(args.approval_artifact)
    report = generate_final_gate_report(approval_artifact)

    if args.output:
        if not write_json(args.output, report):
            print("Failed to write output", file=sys.stderr)
            return 1

    if args.json or not args.output:
        print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))

    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
