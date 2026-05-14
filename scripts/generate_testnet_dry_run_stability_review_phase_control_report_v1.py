#!/usr/bin/env python3
import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional

REQUIRED_BLOCKED_ACTIONS = [
    "EXCHANGE_API_CALL",
    "TESTNET_SUBMIT",
    "REAL_SUBMIT",
    "SUBMIT_ORDER",
    "CANCEL_ORDER",
    "FLATTEN_POSITION",
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


def generate_phase_control_report(
    stability_review_packet: Optional[Dict[str, Any]],
    repeatability_report: Optional[Dict[str, Any]],
    stability_score_report: Optional[Dict[str, Any]],
    readiness_recommendation: Optional[Dict[str, Any]],
    stability_review_packet_path: str,
    repeatability_report_path: str,
    stability_score_report_path: str,
    readiness_recommendation_path: str,
) -> Dict[str, Any]:
    blockers: List[str] = []

    c1 = bool(stability_review_packet and stability_review_packet.get("final_decision") == "READY_FOR_TWO_ROUND_DRY_RUN_REPEATABILITY_SUMMARY")
    c2 = bool(repeatability_report and repeatability_report.get("final_decision") == "READY_FOR_TESTNET_DRY_RUN_STABILITY_SCORE")
    c3 = bool(stability_score_report and stability_score_report.get("final_decision") == "READY_FOR_DRY_RUN_TO_TESTNET_SUBMIT_READINESS_RECOMMENDATION")
    c4 = bool(readiness_recommendation and readiness_recommendation.get("final_decision") == "READY_FOR_TESTNET_SUBMIT_READINESS_REVIEW_PHASE_CONTROL")

    if not c1:
        blockers.append("T486_STABILITY_REVIEW_PACKET_NOT_READY")
    if not c2:
        blockers.append("T487_REPEATABILITY_NOT_CONFIRMED")
    if not c3:
        blockers.append("T488_STABILITY_SCORE_NOT_READY")
    if not c4:
        blockers.append("T489_READINESS_RECOMMENDATION_NOT_READY")

    safe = _safe(stability_review_packet) and _safe(repeatability_report) and _safe(stability_score_report) and _safe(readiness_recommendation)
    if not safe:
        blockers.append("NO_SUBMIT_NO_EXCHANGE_BLOCK_NOT_CONFIRMED")

    ok = len(blockers) == 0

    if ok:
        phase_completion_status = "COMPLETED_TESTNET_DRY_RUN_STABILITY_REVIEW"
        next_phase = "TESTNET_SUBMIT_READINESS_REVIEW"
        final_decision = "READY_FOR_TESTNET_SUBMIT_READINESS_REVIEW"
        safety_flags = _flags(True)
        allowed_actions = list(ALLOWED_PASS)
    else:
        phase_completion_status = "BLOCKED"
        next_phase = "TESTNET_DRY_RUN_STABILITY_REVIEW"
        final_decision = "CONTINUE_TESTNET_DRY_RUN_STABILITY_REVIEW"
        safety_flags = _flags(False)
        allowed_actions = list(ALLOWED_BLOCKED)

    return {
        "ok": ok,
        "task": "T490",
        "phase": "TESTNET_DRY_RUN_STABILITY_REVIEW",
        "source_reports": {
            "stability_review_packet": stability_review_packet_path,
            "repeatability_report": repeatability_report_path,
            "stability_score_report": stability_score_report_path,
            "readiness_recommendation": readiness_recommendation_path,
        },
        "phase_completion_status": phase_completion_status,
        "current_phase": "TESTNET_DRY_RUN_STABILITY_REVIEW",
        "next_phase": next_phase,
        "component_statuses": {
            "t486": c1,
            "t487": c2,
            "t488": c3,
            "t489": c4,
            "no_submit_no_exchange_block_confirmed": safe,
        },
        "blockers": blockers,
        "blocker_count": len(blockers),
        "safety_flags": safety_flags,
        "allowed_actions": allowed_actions,
        "blocked_actions": list(REQUIRED_BLOCKED_ACTIONS),
        "final_decision": final_decision,
        "notes": [],
    }


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    parser = argparse.ArgumentParser(description="Generate TESTNET_DRY_RUN stability review phase control report")
    parser.add_argument("--stability-review-packet", required=True)
    parser.add_argument("--repeatability-report", required=True)
    parser.add_argument("--stability-score-report", required=True)
    parser.add_argument("--readiness-recommendation", required=True)
    parser.add_argument("--output")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    report = generate_phase_control_report(
        load_json(args.stability_review_packet),
        load_json(args.repeatability_report),
        load_json(args.stability_score_report),
        load_json(args.readiness_recommendation),
        args.stability_review_packet,
        args.repeatability_report,
        args.stability_score_report,
        args.readiness_recommendation,
    )

    if args.output and not write_json(args.output, report):
        print("Failed to write output", file=sys.stderr)
        return 1
    if args.json or not args.output:
        print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
