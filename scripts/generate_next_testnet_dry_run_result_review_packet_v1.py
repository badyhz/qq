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
    "NEXT_ITERATION_COMPLETED",
    "NEXT_MATERIALIZED_PAYLOAD_PRESENT",
    "NEXT_PAYLOAD_DIGEST_PRESENT",
    "NEXT_ARTIFACT_REPORT_PRESENT",
    "NO_EXCHANGE_API_CALL_EVIDENCE",
    "NO_SUBMIT_CANCEL_FLATTEN_EVIDENCE",
    "SECOND_ITERATION_REPEATABILITY_REVIEW",
]

ALLOWED_PASS = ["READ_REPORTS", "TESTNET_DRY_RUN_ONLY", "REVIEW_NEXT_DRY_RUN_ARTIFACTS"]
ALLOWED_BLOCKED = ["READ_REPORTS", "REVIEW_NEXT_DRY_RUN_ARTIFACTS"]


def _flags(allow_dry_run: bool) -> Dict[str, Any]:
    return {
        "testnet_dry_run_allowed": allow_dry_run,
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


def _safe(report: Optional[Dict[str, Any]]) -> bool:
    s = (report or {}).get("safety_flags") or {}
    return (
        s.get("exchange_api_calls_allowed") is False
        and s.get("testnet_submit_allowed") is False
        and s.get("real_submit_allowed") is False
        and s.get("submit_order_allowed") is False
        and s.get("cancel_order_allowed") is False
        and s.get("flatten_position_allowed") is False
        and s.get("submit_attempted") is False
        and s.get("cancel_attempted") is False
        and s.get("flatten_attempted") is False
    )


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


def generate_review_packet(next_iteration_phase_report: Optional[Dict[str, Any]], source_path: str) -> Dict[str, Any]:
    ready = bool(
        next_iteration_phase_report
        and next_iteration_phase_report.get("ok") is True
        and next_iteration_phase_report.get("phase_completion_status") == "COMPLETED_NEXT_TESTNET_DRY_RUN_ONLY_ITERATION"
        and next_iteration_phase_report.get("final_decision") == "READY_FOR_NEXT_TESTNET_DRY_RUN_RESULT_REVIEW"
        and _safe(next_iteration_phase_report)
    )

    if ready:
        ok = True
        review_packet_status = "READY_FOR_NEXT_PAYLOAD_MATERIALIZATION_CONSISTENCY_REVIEW"
        review_scope = "REVIEW_NEXT_ARTIFACT_ONLY_NO_SUBMIT_DRY_RUN_RESULT"
        final_decision = "READY_FOR_NEXT_TESTNET_DRY_RUN_PAYLOAD_MATERIALIZATION_CONSISTENCY_REVIEW"
        safety_flags = _flags(True)
        allowed_actions = list(ALLOWED_PASS)
    else:
        ok = False
        review_packet_status = "BLOCKED"
        review_scope = None
        final_decision = "CONTINUE_NEXT_TESTNET_DRY_RUN_ONLY_ITERATION"
        safety_flags = _flags(False)
        allowed_actions = list(ALLOWED_BLOCKED)

    return {
        "ok": ok,
        "task": "T481",
        "phase": "NEXT_TESTNET_DRY_RUN_RESULT_REVIEW",
        "source_reports": {"next_iteration_phase_report": source_path},
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
    parser = argparse.ArgumentParser(description="Generate next TESTNET_DRY_RUN result review packet")
    parser.add_argument("--next-iteration-phase-report", required=True)
    parser.add_argument("--output")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    report = generate_review_packet(load_json(args.next_iteration_phase_report), args.next_iteration_phase_report)

    if args.output and not write_json(args.output, report):
        print("Failed to write output", file=sys.stderr)
        return 1
    if args.json or not args.output:
        print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
