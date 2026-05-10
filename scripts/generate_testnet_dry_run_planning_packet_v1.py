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
    "GENERATE_TESTNET_DRY_RUN_PLANNING_PACKET",
    "TESTNET_DRY_RUN_PLANNING_ONLY"
]

BLOCKED_ACTIONS = list(REQUIRED_BLOCKED_ACTIONS)

REQUIRED_PLAN_ITEMS = [
    "DRY_RUN_MODE_DEFINITION",
    "NO_EXCHANGE_API_CALLS",
    "NO_ORDER_SUBMIT",
    "NO_CANCEL",
    "NO_FLATTEN",
    "INPUT_ARTIFACT_PATHS",
    "OUTPUT_ARTIFACT_PATHS",
    "OPERATOR_REVIEW_REQUIRED",
    "ROLLBACK_PLAN",
    "SAFETY_FLAGS_STILL_BLOCKED"
]


def generate_planning_packet(
    manual_pre_dry_run_phase_report: Optional[Dict[str, Any]],
    manual_pre_dry_run_phase_report_path: str
) -> Dict[str, Any]:
    ok = False
    notes: List[str] = []

    if manual_pre_dry_run_phase_report:
        t435_ok = manual_pre_dry_run_phase_report.get("ok") is True
        t435_phase_status = manual_pre_dry_run_phase_report.get("phase_completion_status") == "COMPLETED_PENDING_TESTNET_DRY_RUN_PLANNING_REVIEW"
        t435_final_decision = manual_pre_dry_run_phase_report.get("final_decision") == "READY_FOR_TESTNET_DRY_RUN_PLANNING_REVIEW"

        if t435_ok and t435_phase_status and t435_final_decision:
            ok = True
            planning_packet_status = "READY_FOR_TESTNET_DRY_RUN_PLAN_CONSTRAINT_REVIEW"
            planning_scope = "PLAN_TESTNET_DRY_RUN_ONLY_BUT_DO_NOT_ENABLE"
            final_decision = "READY_FOR_TESTNET_DRY_RUN_PLAN_CONSTRAINT_REVIEW"
        else:
            ok = False
            planning_packet_status = "BLOCKED"
            planning_scope = "NONE"
            final_decision = "CONTINUE_MANUAL_PRE_DRY_RUN_REVIEW"
    else:
        ok = False
        planning_packet_status = "BLOCKED"
        planning_scope = "NONE"
        final_decision = "CONTINUE_MANUAL_PRE_DRY_RUN_REVIEW"

    return {
        "ok": ok,
        "task": "T436",
        "phase": "TESTNET_DRY_RUN_PLANNING_REVIEW",
        "source_reports": {
            "manual_pre_dry_run_phase_report": manual_pre_dry_run_phase_report_path
        },
        "planning_packet_status": planning_packet_status,
        "planning_scope": planning_scope,
        "planning_constraints": [
            "NO_TESTNET_DRY_RUN_ONLY_ENABLED",
            "NO_EXCHANGE_API_CALLS",
            "NO_ORDER_SUBMIT",
            "NO_CANCEL",
            "NO_FLATTEN"
        ],
        "required_plan_items": REQUIRED_PLAN_ITEMS,
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
        description="Generate TESTNET_DRY_RUN_PLANNING_REVIEW packet"
    )
    parser.add_argument("--manual-pre-dry-run-phase-report", type=str, required=True, help="Path to T435 phase control report JSON")
    parser.add_argument("--output", type=str, help="Path to write output JSON")
    parser.add_argument("--json", action="store_true", help="Print JSON to stdout")

    args = parser.parse_args(argv)

    manual_pre_dry_run_phase_report = load_json(args.manual_pre_dry_run_phase_report)

    report = generate_planning_packet(
        manual_pre_dry_run_phase_report,
        args.manual_pre_dry_run_phase_report
    )

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
