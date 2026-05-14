#!/usr/bin/env python3
import argparse
import json
import os
import sys
from typing import Any, Dict, Optional


REQUIRED_BLOCKED_ACTIONS = [
    "TESTNET_SUBMIT",
    "REAL_SUBMIT",
    "SUBMIT_ORDER",
    "CANCEL_ORDER",
    "FLATTEN_POSITION",
]

REQUIRED_ENABLEMENT_ITEMS = [
    "MANUAL_APPROVAL_PHASE_COMPLETED",
    "SAFETY_SWITCH_REVIEW",
    "OPERATOR_CONFIRMATION_REQUIRED",
    "FINAL_GATE_REQUIRED",
    "TESTNET_DRY_RUN_ONLY_MODE_ONLY",
    "TESTNET_SUBMIT_STILL_BLOCKED",
    "REAL_SUBMIT_STILL_BLOCKED",
    "NO_SUBMIT_CANCEL_FLATTEN",
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
    "GENERATE_TESTNET_DRY_RUN_ENABLEMENT_REVIEW_PACKET",
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


def generate_enablement_review_packet(
    manual_approval_phase_report: Optional[Dict[str, Any]],
    manual_approval_phase_report_path: str,
) -> Dict[str, Any]:
    ready = (
        manual_approval_phase_report
        and manual_approval_phase_report.get("ok") is True
        and manual_approval_phase_report.get("phase_completion_status")
        == "COMPLETED_PENDING_TESTNET_DRY_RUN_ENABLEMENT_REVIEW"
        and manual_approval_phase_report.get("final_decision")
        == "READY_FOR_TESTNET_DRY_RUN_ENABLEMENT_REVIEW"
    )

    if ready:
        ok = True
        enablement_packet_status = "READY_FOR_TESTNET_DRY_RUN_ENABLEMENT_SAFETY_SWITCH_REVIEW"
        enablement_scope = "REVIEW_TESTNET_DRY_RUN_ONLY_MODE_ENABLEMENT"
        final_decision = "READY_FOR_TESTNET_DRY_RUN_ENABLEMENT_SAFETY_SWITCH_REVIEW"
    else:
        ok = False
        enablement_packet_status = "BLOCKED"
        enablement_scope = None
        final_decision = "CONTINUE_MANUAL_TESTNET_DRY_RUN_APPROVAL_REVIEW"

    return {
        "ok": ok,
        "task": "T451",
        "phase": "TESTNET_DRY_RUN_ENABLEMENT_REVIEW",
        "source_reports": {"manual_approval_phase_report": manual_approval_phase_report_path},
        "enablement_packet_status": enablement_packet_status,
        "enablement_scope": enablement_scope,
        "required_enablement_items": list(REQUIRED_ENABLEMENT_ITEMS),
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
        description="Generate TESTNET_DRY_RUN_ENABLEMENT_REVIEW packet"
    )
    parser.add_argument(
        "--manual-approval-phase-report",
        required=True,
        help="Path to T450 manual approval phase control report JSON",
    )
    parser.add_argument("--output", help="Path to write output JSON")
    parser.add_argument("--json", action="store_true", help="Print JSON to stdout")
    args = parser.parse_args(argv)

    manual_approval_phase_report = load_json(args.manual_approval_phase_report)
    report = generate_enablement_review_packet(
        manual_approval_phase_report, args.manual_approval_phase_report
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
