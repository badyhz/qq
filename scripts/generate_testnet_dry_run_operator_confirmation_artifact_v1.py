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

REQUIRED_CONFIRMATIONS = [
    "TESTNET_DRY_RUN_ONLY_MODE",
    "NO_TESTNET_SUBMIT",
    "NO_REAL_SUBMIT",
    "NO_SUBMIT_ORDER",
    "NO_CANCEL_ORDER",
    "NO_FLATTEN_POSITION",
    "MANUAL_FINAL_GATE_REQUIRED",
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
    "GENERATE_TESTNET_DRY_RUN_OPERATOR_CONFIRMATION_ARTIFACT",
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


def generate_operator_confirmation_artifact(
    safety_switch_report: Optional[Dict[str, Any]],
    operator_confirmation: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    missing_items: List[str] = []
    failed_items: List[str] = []

    safety_ready = safety_switch_report and safety_switch_report.get("ok") is True
    confirmation = operator_confirmation or {}

    confirmed = confirmation.get("confirmed") is True
    confirmations = confirmation.get("confirmations")
    if not isinstance(confirmations, dict):
        confirmations = {}

    for item in REQUIRED_CONFIRMATIONS:
        if item not in confirmations:
            missing_items.append(item)
        elif confirmations.get(item) is not True:
            failed_items.append(item)

    ok = bool(safety_ready and confirmed and not missing_items and not failed_items)

    if ok:
        operator_confirmation_status = "TESTNET_DRY_RUN_OPERATOR_CONFIRMED"
        final_decision = "READY_FOR_TESTNET_DRY_RUN_ENABLEMENT_FINAL_GATE"
    else:
        operator_confirmation_status = "OPERATOR_CONFIRMATION_REJECTED_OR_INCOMPLETE"
        final_decision = "CONTINUE_TESTNET_DRY_RUN_ENABLEMENT_REVIEW"

    notes: List[str] = []
    if confirmation.get("notes") is not None:
        notes.append(str(confirmation.get("notes")))

    return {
        "ok": ok,
        "task": "T453",
        "phase": "TESTNET_DRY_RUN_ENABLEMENT_REVIEW",
        "operator_confirmation_status": operator_confirmation_status,
        "operator": confirmation.get("operator"),
        "missing_items": missing_items,
        "failed_items": failed_items,
        "safety_flags": dict(SAFETY_FLAGS),
        "allowed_actions": list(ALLOWED_ACTIONS),
        "blocked_actions": list(BLOCKED_ACTIONS),
        "final_decision": final_decision,
        "notes": notes,
    }


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        description="Generate TESTNET_DRY_RUN operator confirmation artifact"
    )
    parser.add_argument("--safety-switch-report", required=True, help="Path to T452 safety switch report JSON")
    parser.add_argument(
        "--operator-confirmation", required=True, help="Path to operator confirmation JSON"
    )
    parser.add_argument("--output", help="Path to write output JSON")
    parser.add_argument("--json", action="store_true", help="Print JSON to stdout")
    args = parser.parse_args(argv)

    safety_switch_report = load_json(args.safety_switch_report)
    operator_confirmation = load_json(args.operator_confirmation)
    report = generate_operator_confirmation_artifact(
        safety_switch_report, operator_confirmation
    )

    if args.output:
        if not write_json(args.output, report):
            print("Failed to write output", file=sys.stderr)
            return 1

    if args.json or not args.output:
        print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))

    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
