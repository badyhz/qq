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

ALLOWED_ACTIONS = [
    "READ_REPORTS",
    "TESTNET_DRY_RUN_ONLY",
    "MATERIALIZE_PAYLOAD_ARTIFACT",
    "GENERATE_TESTNET_DRY_RUN_ONLY_EXECUTION_RESULT_REPORT",
]


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


def generate_execution_result_report(materialized_payload_report: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    mp = materialized_payload_report or {}
    payload = mp.get("materialized_payload") or {}

    ready = bool(
        mp
        and mp.get("ok") is True
        and mp.get("materialization_status") == "NO_SUBMIT_PAYLOAD_MATERIALIZED"
        and mp.get("final_decision") == "READY_FOR_TESTNET_DRY_RUN_ONLY_EXECUTION_RESULT_REPORT"
        and payload.get("dry_run_only") is True
        and payload.get("artifact_only") is True
        and payload.get("exchange_api_call_attempted") is False
        and payload.get("submit_attempted") is False
        and payload.get("cancel_attempted") is False
        and payload.get("flatten_attempted") is False
    )

    if ready:
        ok = True
        execution_result_status = "TESTNET_DRY_RUN_ONLY_EXECUTION_REPORTED"
        simulated_execution_summary = {
            "status": "ARTIFACT_ONLY_NO_SUBMIT_COMPLETED",
            "exchange_api_call_attempted": False,
            "submit_attempted": False,
            "cancel_attempted": False,
            "flatten_attempted": False,
        }
        final_decision = "READY_FOR_TESTNET_DRY_RUN_ONLY_ARTIFACT_VERIFICATION"
        safety_flags = _flags(True)
    else:
        ok = False
        execution_result_status = "TESTNET_DRY_RUN_ONLY_EXECUTION_BLOCKED"
        simulated_execution_summary = {
            "status": "BLOCKED",
            "exchange_api_call_attempted": False,
            "submit_attempted": False,
            "cancel_attempted": False,
            "flatten_attempted": False,
        }
        final_decision = "BLOCK_TESTNET_DRY_RUN_ONLY_EXECUTION"
        safety_flags = _flags(False)

    return {
        "ok": ok,
        "task": "T463",
        "phase": "TESTNET_DRY_RUN_ONLY_EXECUTION",
        "execution_result_status": execution_result_status,
        "simulated_execution_summary": simulated_execution_summary,
        "safety_flags": safety_flags,
        "allowed_actions": list(ALLOWED_ACTIONS),
        "blocked_actions": list(REQUIRED_BLOCKED_ACTIONS),
        "final_decision": final_decision,
        "notes": [],
    }


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    p = argparse.ArgumentParser(description="Generate TESTNET_DRY_RUN_ONLY execution result report")
    p.add_argument("--materialized-payload", required=True)
    p.add_argument("--output")
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)

    src = load_json(a.materialized_payload)
    report = generate_execution_result_report(src)

    if a.output and not write_json(a.output, report):
        print("Failed to write output", file=sys.stderr)
        return 1
    if a.json or not a.output:
        print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
