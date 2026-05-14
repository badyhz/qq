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
    if s.get("exchange_api_calls_allowed") is not False:
        return False
    if s.get("testnet_submit_allowed") is not False:
        return False
    if s.get("real_submit_allowed") is not False:
        return False
    if s.get("submit_order_allowed") is not False:
        return False
    if s.get("cancel_order_allowed") is not False:
        return False
    if s.get("flatten_position_allowed") is not False:
        return False
    if s.get("submit_attempted") is not False:
        return False
    if s.get("cancel_attempted") is not False:
        return False
    if s.get("flatten_attempted") is not False:
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
    review_packet: Optional[Dict[str, Any]],
    consistency_report: Optional[Dict[str, Any]],
    safety_evidence_report: Optional[Dict[str, Any]],
    review_score_report: Optional[Dict[str, Any]],
    review_packet_path: str,
    consistency_report_path: str,
    safety_evidence_report_path: str,
    review_score_report_path: str,
) -> Dict[str, Any]:
    blockers: List[str] = []

    c1 = bool(review_packet and review_packet.get("final_decision") == "READY_FOR_NEXT_TESTNET_DRY_RUN_PAYLOAD_MATERIALIZATION_CONSISTENCY_REVIEW")
    c2 = bool(consistency_report and consistency_report.get("final_decision") == "READY_FOR_NEXT_TESTNET_DRY_RUN_NO_SUBMIT_SAFETY_EVIDENCE_REVIEW")
    c3 = bool(safety_evidence_report and safety_evidence_report.get("final_decision") == "READY_FOR_NEXT_TESTNET_DRY_RUN_RESULT_REVIEW_SCORE")
    c4 = bool(review_score_report and review_score_report.get("final_decision") == "READY_FOR_NEXT_TESTNET_DRY_RUN_RESULT_REVIEW_PHASE_CONTROL")

    if not c1:
        blockers.append("T481_REVIEW_PACKET_NOT_READY")
    if not c2:
        blockers.append("T482_CONSISTENCY_NOT_VERIFIED")
    if not c3:
        blockers.append("T483_SAFETY_EVIDENCE_NOT_VERIFIED")
    if not c4:
        blockers.append("T484_REVIEW_SCORE_NOT_READY")

    safe = _safe(review_packet) and _safe(consistency_report) and _safe(safety_evidence_report) and _safe(review_score_report)
    if not safe:
        blockers.append("NO_SUBMIT_NO_EXCHANGE_BLOCK_NOT_CONFIRMED")

    ok = len(blockers) == 0

    if ok:
        phase_completion_status = "COMPLETED_NEXT_TESTNET_DRY_RUN_RESULT_REVIEW"
        next_phase = "TESTNET_DRY_RUN_STABILITY_REVIEW"
        final_decision = "READY_FOR_TESTNET_DRY_RUN_STABILITY_REVIEW"
        safety_flags = _flags(True)
        allowed_actions = list(ALLOWED_PASS)
    else:
        phase_completion_status = "BLOCKED"
        next_phase = "NEXT_TESTNET_DRY_RUN_RESULT_REVIEW"
        final_decision = "CONTINUE_NEXT_TESTNET_DRY_RUN_RESULT_REVIEW"
        safety_flags = _flags(False)
        allowed_actions = list(ALLOWED_BLOCKED)

    return {
        "ok": ok,
        "task": "T485",
        "phase": "NEXT_TESTNET_DRY_RUN_RESULT_REVIEW",
        "source_reports": {
            "review_packet": review_packet_path,
            "consistency_report": consistency_report_path,
            "safety_evidence_report": safety_evidence_report_path,
            "review_score_report": review_score_report_path,
        },
        "phase_completion_status": phase_completion_status,
        "current_phase": "NEXT_TESTNET_DRY_RUN_RESULT_REVIEW",
        "next_phase": next_phase,
        "component_statuses": {
            "t481": c1,
            "t482": c2,
            "t483": c3,
            "t484": c4,
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
    parser = argparse.ArgumentParser(description="Generate next TESTNET_DRY_RUN result review phase control report")
    parser.add_argument("--review-packet", required=True)
    parser.add_argument("--consistency-report", required=True)
    parser.add_argument("--safety-evidence-report", required=True)
    parser.add_argument("--review-score-report", required=True)
    parser.add_argument("--output")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    report = generate_phase_control_report(
        load_json(args.review_packet),
        load_json(args.consistency_report),
        load_json(args.safety_evidence_report),
        load_json(args.review_score_report),
        args.review_packet,
        args.consistency_report,
        args.safety_evidence_report,
        args.review_score_report,
    )

    if args.output and not write_json(args.output, report):
        print("Failed to write output", file=sys.stderr)
        return 1
    if args.json or not args.output:
        print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
