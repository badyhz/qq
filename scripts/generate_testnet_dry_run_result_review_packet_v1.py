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

REQUIRED_REVIEW_ITEMS = [
    "EXECUTION_PHASE_COMPLETED",
    "MATERIALIZED_PAYLOAD_PRESENT",
    "PAYLOAD_DIGEST_PRESENT",
    "RESULT_REPORT_PRESENT",
    "ARTIFACT_VERIFICATION_PRESENT",
    "NO_EXCHANGE_API_CALL_EVIDENCE",
    "NO_SUBMIT_CANCEL_FLATTEN_EVIDENCE",
]

ALLOWED_PASS = [
    "READ_REPORTS",
    "TESTNET_DRY_RUN_ONLY",
    "REVIEW_DRY_RUN_ARTIFACTS",
]
ALLOWED_BLOCKED = ["READ_REPORTS", "REVIEW_DRY_RUN_ARTIFACTS"]


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


def generate_result_review_packet(execution_phase_report: Optional[Dict[str, Any]], source_path: str) -> Dict[str, Any]:
    s = (execution_phase_report or {}).get("safety_flags") or {}
    ready = bool(
        execution_phase_report
        and execution_phase_report.get("ok") is True
        and execution_phase_report.get("phase_completion_status") == "COMPLETED_TESTNET_DRY_RUN_ONLY_EXECUTION"
        and execution_phase_report.get("final_decision") == "READY_FOR_TESTNET_DRY_RUN_RESULT_REVIEW"
        and s.get("testnet_dry_run_allowed") is True
        and s.get("exchange_api_calls_allowed") is False
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
        review_packet_status = "READY_FOR_MATERIALIZED_PAYLOAD_CONSISTENCY_REVIEW"
        review_scope = "REVIEW_ARTIFACT_ONLY_NO_SUBMIT_DRY_RUN_RESULT"
        safety_flags = _flags(True)
        allowed_actions = list(ALLOWED_PASS)
        final_decision = "READY_FOR_TESTNET_DRY_RUN_MATERIALIZED_PAYLOAD_CONSISTENCY_REVIEW"
    else:
        ok = False
        review_packet_status = "BLOCKED"
        review_scope = None
        safety_flags = _flags(False)
        allowed_actions = list(ALLOWED_BLOCKED)
        final_decision = "CONTINUE_TESTNET_DRY_RUN_ONLY_EXECUTION"

    return {
        "ok": ok,
        "task": "T466",
        "phase": "TESTNET_DRY_RUN_RESULT_REVIEW",
        "source_reports": {"execution_phase_report": source_path},
        "review_packet_status": review_packet_status,
        "review_scope": review_scope,
        "required_review_items": list(REQUIRED_REVIEW_ITEMS),
        "safety_flags": safety_flags,
        "allowed_actions": allowed_actions,
        "blocked_actions": list(REQUIRED_BLOCKED_ACTIONS),
        "final_decision": final_decision,
        "notes": [],
    }


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    p = argparse.ArgumentParser(description="Generate TESTNET_DRY_RUN result review packet")
    p.add_argument("--execution-phase-report", required=True)
    p.add_argument("--output")
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)

    src = load_json(a.execution_phase_report)
    report = generate_result_review_packet(src, a.execution_phase_report)

    if a.output and not write_json(a.output, report):
        print("Failed to write output", file=sys.stderr)
        return 1
    if a.json or not a.output:
        print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
