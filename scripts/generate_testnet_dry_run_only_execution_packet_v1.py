#!/usr/bin/env python3
import argparse
import json
import os
import sys
from typing import Any, Dict, Optional

REQUIRED_BLOCKED_ACTIONS = [
    "EXCHANGE_API_CALL",
    "TESTNET_SUBMIT",
    "REAL_SUBMIT",
    "SUBMIT_ORDER",
    "CANCEL_ORDER",
    "FLATTEN_POSITION",
]

EXECUTION_CONSTRAINTS = [
    "ARTIFACT_ONLY_EXECUTION",
    "NO_EXCHANGE_API_CALLS",
    "NO_TESTNET_SUBMIT",
    "NO_REAL_SUBMIT",
    "NO_SUBMIT_ORDER",
    "NO_CANCEL_ORDER",
    "NO_FLATTEN_POSITION",
    "DETERMINISTIC_OUTPUT_REQUIRED",
]

ALLOWED_PASS = [
    "READ_REPORTS",
    "TESTNET_DRY_RUN_ONLY",
    "GENERATE_TESTNET_DRY_RUN_ONLY_EXECUTION_PACKET",
]
ALLOWED_BLOCKED = ["READ_REPORTS", "GENERATE_TESTNET_DRY_RUN_ONLY_EXECUTION_PACKET"]


def _flags(dry_run_allowed: bool) -> Dict[str, Any]:
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


def generate_execution_packet(dry_run_only_phase_report: Optional[Dict[str, Any]], source_path: str) -> Dict[str, Any]:
    s = (dry_run_only_phase_report or {}).get("safety_flags") or {}
    ready = bool(
        dry_run_only_phase_report
        and dry_run_only_phase_report.get("ok") is True
        and dry_run_only_phase_report.get("phase_completion_status") == "COMPLETED_READY_FOR_TESTNET_DRY_RUN_ONLY_EXECUTION"
        and dry_run_only_phase_report.get("final_decision") == "READY_FOR_TESTNET_DRY_RUN_ONLY_EXECUTION"
        and s.get("testnet_dry_run_allowed") is True
        and s.get("exchange_api_calls_allowed", False) is False
        and s.get("testnet_submit_allowed") is False
        and s.get("real_submit_allowed") is False
        and s.get("submit_order_allowed") is False
        and s.get("cancel_order_allowed") is False
        and s.get("flatten_position_allowed") is False
        and s.get("submit_attempted") is False
        and s.get("cancel_attempted") is False
        and s.get("flatten_attempted") is False
    )

    if ready:
        ok = True
        execution_packet_status = "READY_FOR_NO_SUBMIT_PAYLOAD_MATERIALIZATION"
        execution_scope = "TESTNET_DRY_RUN_ONLY_ARTIFACT_EXECUTION"
        safety_flags = _flags(True)
        allowed_actions = list(ALLOWED_PASS)
        final_decision = "READY_FOR_TESTNET_DRY_RUN_NO_SUBMIT_PAYLOAD_MATERIALIZATION"
    else:
        ok = False
        execution_packet_status = "BLOCKED"
        execution_scope = None
        safety_flags = _flags(False)
        allowed_actions = list(ALLOWED_BLOCKED)
        final_decision = "CONTINUE_TESTNET_DRY_RUN_ONLY_MODE"

    return {
        "ok": ok,
        "task": "T461",
        "phase": "TESTNET_DRY_RUN_ONLY_EXECUTION",
        "source_reports": {"dry_run_only_phase_report": source_path},
        "execution_packet_status": execution_packet_status,
        "execution_scope": execution_scope,
        "execution_constraints": list(EXECUTION_CONSTRAINTS),
        "safety_flags": safety_flags,
        "allowed_actions": allowed_actions,
        "blocked_actions": list(REQUIRED_BLOCKED_ACTIONS),
        "final_decision": final_decision,
        "notes": [],
    }


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    p = argparse.ArgumentParser(description="Generate TESTNET_DRY_RUN_ONLY_EXECUTION packet")
    p.add_argument("--dry-run-only-phase-report", required=True)
    p.add_argument("--output")
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)

    src = load_json(a.dry_run_only_phase_report)
    report = generate_execution_packet(src, a.dry_run_only_phase_report)

    if a.output and not write_json(a.output, report):
        print("Failed to write output", file=sys.stderr)
        return 1
    if a.json or not a.output:
        print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
