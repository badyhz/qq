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
    "GENERATE_MANUAL_PRE_DRY_RUN_FINAL_GATE_REPORT",
    "MANUAL_REVIEW_ONLY"
]

BLOCKED_ACTIONS = list(REQUIRED_BLOCKED_ACTIONS)


def generate_final_gate_report(
    approval_artifact: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    ok = False
    notes: List[str] = []

    if approval_artifact:
        t433_ok = approval_artifact.get("ok") is True
        t433_approval_status = approval_artifact.get("approval_status") == "MANUAL_PRE_DRY_RUN_APPROVED"
        t433_final_decision = approval_artifact.get("final_decision") == "READY_FOR_MANUAL_PRE_DRY_RUN_FINAL_GATE"

        if t433_ok and t433_approval_status and t433_final_decision:
            ok = True
            final_gate_status = "MANUAL_PRE_DRY_RUN_FINAL_GATE_PASSED"
            gate_result = "READY_FOR_TESTNET_DRY_RUN_PLANNING_REVIEW"
            final_decision = "READY_FOR_TESTNET_DRY_RUN_PLANNING_REVIEW"
        else:
            ok = False
            final_gate_status = "BLOCKED"
            gate_result = "NOT_READY"
            final_decision = "CONTINUE_MANUAL_PRE_DRY_RUN_REVIEW"
    else:
        ok = False
        final_gate_status = "BLOCKED"
        gate_result = "NOT_READY"
        final_decision = "CONTINUE_MANUAL_PRE_DRY_RUN_REVIEW"

    return {
        "ok": ok,
        "task": "T434",
        "phase": "MANUAL_PRE_DRY_RUN_REVIEW",
        "final_gate_status": final_gate_status,
        "gate_result": gate_result,
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
        description="Generate MANUAL_PRE_DRY_RUN_REVIEW final gate report"
    )
    parser.add_argument("--approval-artifact", type=str, required=True, help="Path to T433 approval artifact JSON")
    parser.add_argument("--output", type=str, help="Path to write output JSON")
    parser.add_argument("--json", action="store_true", help="Print JSON to stdout")

    args = parser.parse_args(argv)

    approval_artifact = load_json(args.approval_artifact)

    report = generate_final_gate_report(approval_artifact)

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
