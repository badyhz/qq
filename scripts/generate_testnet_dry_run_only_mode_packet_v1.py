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

DRY_RUN_ONLY_CONSTRAINTS = [
    "NO_EXCHANGE_API_CALLS",
    "NO_TESTNET_SUBMIT",
    "NO_REAL_SUBMIT",
    "NO_SUBMIT_ORDER",
    "NO_CANCEL_ORDER",
    "NO_FLATTEN_POSITION",
    "PAYLOAD_CONSTRUCTION_ONLY",
    "ARTIFACT_OUTPUT_ONLY",
]

ALLOWED_ACTIONS_PASS = [
    "READ_REPORTS",
    "TESTNET_DRY_RUN_ONLY",
    "GENERATE_TESTNET_DRY_RUN_ONLY_MODE_PACKET",
]
ALLOWED_ACTIONS_BLOCKED = [
    "READ_REPORTS",
    "GENERATE_TESTNET_DRY_RUN_ONLY_MODE_PACKET",
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


def generate_mode_packet(enablement_phase_report: Optional[Dict[str, Any]], source_path: str) -> Dict[str, Any]:
    safety_in = (enablement_phase_report or {}).get("safety_flags") or {}
    ready = bool(
        enablement_phase_report
        and enablement_phase_report.get("ok") is True
        and enablement_phase_report.get("phase_completion_status")
        == "COMPLETED_READY_FOR_TESTNET_DRY_RUN_ONLY_MODE"
        and enablement_phase_report.get("final_decision") == "READY_FOR_TESTNET_DRY_RUN_ONLY_MODE"
        and safety_in.get("testnet_dry_run_allowed") is True
        and safety_in.get("submit_attempted") is False
        and safety_in.get("cancel_attempted") is False
        and safety_in.get("flatten_attempted") is False
    )

    if ready:
        ok = True
        mode_packet_status = "READY_FOR_NO_SUBMIT_PAYLOAD_PLAN"
        mode_scope = "TESTNET_DRY_RUN_ONLY_NO_SUBMIT_NO_EXCHANGE_API"
        safety_flags = _safety_flags(True)
        allowed_actions = list(ALLOWED_ACTIONS_PASS)
        final_decision = "READY_FOR_TESTNET_DRY_RUN_NO_SUBMIT_PAYLOAD_PLAN"
    else:
        ok = False
        mode_packet_status = "BLOCKED"
        mode_scope = None
        safety_flags = _safety_flags(False)
        allowed_actions = list(ALLOWED_ACTIONS_BLOCKED)
        final_decision = "CONTINUE_TESTNET_DRY_RUN_ENABLEMENT_REVIEW"

    return {
        "ok": ok,
        "task": "T456",
        "phase": "TESTNET_DRY_RUN_ONLY_MODE",
        "source_reports": {"enablement_phase_report": source_path},
        "mode_packet_status": mode_packet_status,
        "mode_scope": mode_scope,
        "dry_run_only_constraints": list(DRY_RUN_ONLY_CONSTRAINTS),
        "safety_flags": safety_flags,
        "allowed_actions": allowed_actions,
        "blocked_actions": list(BLOCKED_ACTIONS),
        "final_decision": final_decision,
        "notes": [],
    }


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(description="Generate TESTNET_DRY_RUN_ONLY_MODE packet")
    parser.add_argument("--enablement-phase-report", required=True)
    parser.add_argument("--output")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    enablement_phase_report = load_json(args.enablement_phase_report)
    report = generate_mode_packet(enablement_phase_report, args.enablement_phase_report)

    if args.output and not write_json(args.output, report):
        print("Failed to write output", file=sys.stderr)
        return 1

    if args.json or not args.output:
        print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))

    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
