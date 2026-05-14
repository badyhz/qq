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


def summarize_repeatability(
    stability_review_packet: Optional[Dict[str, Any]],
    first_result_score_report: Optional[Dict[str, Any]],
    second_result_score_report: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    blockers: List[str] = []

    if not (
        stability_review_packet
        and stability_review_packet.get("ok") is True
        and stability_review_packet.get("final_decision") == "READY_FOR_TWO_ROUND_DRY_RUN_REPEATABILITY_SUMMARY"
    ):
        blockers.append("STABILITY_REVIEW_PACKET_NOT_READY")

    first_score = (first_result_score_report or {}).get("review_score")
    second_score = (second_result_score_report or {}).get("review_score")

    if not (first_result_score_report and first_result_score_report.get("ok") is True and first_score is not None):
        blockers.append("FIRST_ROUND_SCORE_NOT_READY")
    if not (second_result_score_report and second_result_score_report.get("ok") is True and second_score is not None):
        blockers.append("SECOND_ROUND_SCORE_NOT_READY")

    if first_score is not None and first_score < 100:
        blockers.append("FIRST_ROUND_SCORE_BELOW_100")
    if second_score is not None and second_score < 100:
        blockers.append("SECOND_ROUND_SCORE_BELOW_100")

    safe = _safe(stability_review_packet) and _safe(first_result_score_report) and _safe(second_result_score_report)
    if not safe:
        blockers.append("NO_SUBMIT_EVIDENCE_NOT_CONFIRMED")

    ok = len(blockers) == 0

    if ok:
        repeatability_status = "TWO_ROUND_DRY_RUN_REPEATABILITY_CONFIRMED"
        final_decision = "READY_FOR_TESTNET_DRY_RUN_STABILITY_SCORE"
        warnings = ["NO_REAL_TESTNET_SUBMIT_YET"]
        safety_flags = _flags(True)
        allowed_actions = list(ALLOWED_PASS)
        notes = []
    else:
        repeatability_status = "TWO_ROUND_DRY_RUN_REPEATABILITY_BLOCKED"
        final_decision = "BLOCK_TESTNET_DRY_RUN_STABILITY_REVIEW"
        warnings = []
        safety_flags = _flags(False)
        allowed_actions = list(ALLOWED_BLOCKED)
        notes = list(blockers)

    return {
        "ok": ok,
        "task": "T487",
        "phase": "TESTNET_DRY_RUN_STABILITY_REVIEW",
        "repeatability_status": repeatability_status,
        "first_round_summary": {
            "ok": bool((first_result_score_report or {}).get("ok") is True),
            "review_score": first_score,
        },
        "second_round_summary": {
            "ok": bool((second_result_score_report or {}).get("ok") is True),
            "review_score": second_score,
        },
        "repeatability_summary": {
            "rounds_reviewed": 2,
            "all_scores_100": (first_score == 100 and second_score == 100),
            "no_submit_evidence_confirmed": safe,
        },
        "warnings": warnings,
        "safety_flags": safety_flags,
        "allowed_actions": allowed_actions,
        "blocked_actions": list(REQUIRED_BLOCKED_ACTIONS),
        "final_decision": final_decision,
        "notes": notes,
    }


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    parser = argparse.ArgumentParser(description="Summarize two-round TESTNET_DRY_RUN repeatability")
    parser.add_argument("--stability-review-packet", required=True)
    parser.add_argument("--first-result-score-report", required=True)
    parser.add_argument("--second-result-score-report", required=True)
    parser.add_argument("--output")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    report = summarize_repeatability(
        load_json(args.stability_review_packet),
        load_json(args.first_result_score_report),
        load_json(args.second_result_score_report),
    )

    if args.output and not write_json(args.output, report):
        print("Failed to write output", file=sys.stderr)
        return 1
    if args.json or not args.output:
        print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
