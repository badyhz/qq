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

REQUIRED_STABILITY_ITEMS = [
    "FIRST_DRY_RUN_RESULT_REVIEW_COMPLETED",
    "SECOND_DRY_RUN_RESULT_REVIEW_COMPLETED",
    "TWO_ROUND_REPEATABILITY_REQUIRED",
    "STABILITY_SCORE_REQUIRED",
    "TESTNET_SUBMIT_READINESS_RECOMMENDATION_REQUIRED",
    "NO_EXCHANGE_API_CALLS",
    "NO_SUBMIT_CANCEL_FLATTEN",
]

ALLOWED_PASS = ["READ_REPORTS", "TESTNET_DRY_RUN_ONLY", "REVIEW_DRY_RUN_STABILITY"]
ALLOWED_BLOCKED = ["READ_REPORTS", "REVIEW_DRY_RUN_STABILITY"]


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
    safety = (report or {}).get("safety_flags") or {}
    if safety.get("exchange_api_calls_allowed") is not False:
        return False
    if safety.get("testnet_submit_allowed") is not False:
        return False
    if safety.get("real_submit_allowed") is not False:
        return False
    if safety.get("submit_order_allowed") is not False:
        return False
    if safety.get("cancel_order_allowed") is not False:
        return False
    if safety.get("flatten_position_allowed") is not False:
        return False
    if safety.get("submit_attempted") is not False:
        return False
    if safety.get("cancel_attempted") is not False:
        return False
    if safety.get("flatten_attempted") is not False:
        return False

    allowed = (report or {}).get("allowed_actions") or []
    blocked = (report or {}).get("blocked_actions") or []
    for action in REQUIRED_BLOCKED_ACTIONS:
        if action in allowed:
            return False
        if action not in blocked:
            return False
    return True


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


def generate_stability_review_packet(
    first_result_review_phase_report: Optional[Dict[str, Any]],
    second_result_review_phase_report: Optional[Dict[str, Any]],
    first_path: str,
    second_path: str,
) -> Dict[str, Any]:
    first_ready = bool(
        first_result_review_phase_report
        and first_result_review_phase_report.get("ok") is True
        and first_result_review_phase_report.get("phase_completion_status") == "COMPLETED_TESTNET_DRY_RUN_RESULT_REVIEW"
        and first_result_review_phase_report.get("final_decision") == "READY_FOR_TESTNET_DRY_RUN_ITERATION_REVIEW"
    )

    second_ready = bool(
        second_result_review_phase_report
        and second_result_review_phase_report.get("ok") is True
        and second_result_review_phase_report.get("phase_completion_status") == "COMPLETED_NEXT_TESTNET_DRY_RUN_RESULT_REVIEW"
        and second_result_review_phase_report.get("final_decision") == "READY_FOR_TESTNET_DRY_RUN_STABILITY_REVIEW"
    )

    safe = _safe(first_result_review_phase_report) and _safe(second_result_review_phase_report)
    ok = first_ready and second_ready and safe

    if ok:
        status = "READY_FOR_TWO_ROUND_DRY_RUN_REPEATABILITY_SUMMARY"
        scope = "REVIEW_TWO_ARTIFACT_ONLY_NO_SUBMIT_DRY_RUN_ROUNDS"
        final_decision = "READY_FOR_TWO_ROUND_DRY_RUN_REPEATABILITY_SUMMARY"
        safety_flags = _flags(True)
        allowed_actions = list(ALLOWED_PASS)
        notes = []
    else:
        status = "BLOCKED"
        scope = None
        final_decision = "CONTINUE_DRY_RUN_RESULT_REVIEW"
        safety_flags = _flags(False)
        allowed_actions = list(ALLOWED_BLOCKED)
        notes = []
        if not first_ready:
            notes.append("FIRST_RESULT_REVIEW_NOT_READY")
        if not second_ready:
            notes.append("SECOND_RESULT_REVIEW_NOT_READY")
        if not safe:
            notes.append("NO_SUBMIT_NO_EXCHANGE_BLOCK_NOT_CONFIRMED")

    return {
        "ok": ok,
        "task": "T486",
        "phase": "TESTNET_DRY_RUN_STABILITY_REVIEW",
        "source_reports": {
            "first_result_review_phase_report": first_path,
            "second_result_review_phase_report": second_path,
        },
        "stability_review_packet_status": status,
        "review_scope": scope,
        "required_stability_items": list(REQUIRED_STABILITY_ITEMS),
        "safety_flags": safety_flags,
        "allowed_actions": allowed_actions,
        "blocked_actions": list(REQUIRED_BLOCKED_ACTIONS),
        "final_decision": final_decision,
        "notes": notes,
    }


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    parser = argparse.ArgumentParser(description="Generate TESTNET_DRY_RUN stability review packet")
    parser.add_argument("--first-result-review-phase-report", required=True)
    parser.add_argument("--second-result-review-phase-report", required=True)
    parser.add_argument("--output")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    report = generate_stability_review_packet(
        load_json(args.first_result_review_phase_report),
        load_json(args.second_result_review_phase_report),
        args.first_result_review_phase_report,
        args.second_result_review_phase_report,
    )

    if args.output and not write_json(args.output, report):
        print("Failed to write output", file=sys.stderr)
        return 1
    if args.json or not args.output:
        print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
