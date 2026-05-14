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


def _grade(score: int) -> str:
    if score == 100:
        return "A"
    if 75 <= score <= 99:
        return "B"
    if 50 <= score <= 74:
        return "C"
    if 1 <= score <= 49:
        return "D"
    return "F"


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


def generate_stability_score(
    stability_review_packet: Optional[Dict[str, Any]],
    repeatability_report: Optional[Dict[str, Any]],
    first_result_score_report: Optional[Dict[str, Any]],
    second_result_score_report: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    blockers: List[str] = []
    score = 0

    if (
        stability_review_packet
        and stability_review_packet.get("ok") is True
        and stability_review_packet.get("final_decision") == "READY_FOR_TWO_ROUND_DRY_RUN_REPEATABILITY_SUMMARY"
    ):
        score += 20
    else:
        blockers.append("STABILITY_REVIEW_PACKET_NOT_READY")

    if (
        repeatability_report
        and repeatability_report.get("ok") is True
        and repeatability_report.get("final_decision") == "READY_FOR_TESTNET_DRY_RUN_STABILITY_SCORE"
    ):
        score += 30
    else:
        blockers.append("REPEATABILITY_NOT_CONFIRMED")

    if first_result_score_report and first_result_score_report.get("review_score") == 100:
        score += 20
    else:
        blockers.append("FIRST_DRY_RUN_SCORE_NOT_100")

    if second_result_score_report and second_result_score_report.get("review_score") == 100:
        score += 20
    else:
        blockers.append("SECOND_DRY_RUN_SCORE_NOT_100")

    safe = (
        _safe(stability_review_packet)
        and _safe(repeatability_report)
        and _safe(first_result_score_report)
        and _safe(second_result_score_report)
    )
    if safe:
        score += 10
    else:
        blockers.append("NO_SUBMIT_NO_EXCHANGE_BLOCK_NOT_CONFIRMED")

    ok = score == 100

    if ok:
        stability_status = "TESTNET_DRY_RUN_STABILITY_CONFIRMED"
        final_decision = "READY_FOR_DRY_RUN_TO_TESTNET_SUBMIT_READINESS_RECOMMENDATION"
        safety_flags = _flags(True)
        allowed_actions = list(ALLOWED_PASS)
    else:
        stability_status = "TESTNET_DRY_RUN_STABILITY_BLOCKED"
        final_decision = "BLOCK_TESTNET_DRY_RUN_STABILITY_REVIEW"
        safety_flags = _flags(False)
        allowed_actions = list(ALLOWED_BLOCKED)

    return {
        "ok": ok,
        "task": "T488",
        "phase": "TESTNET_DRY_RUN_STABILITY_REVIEW",
        "stability_score": score,
        "stability_grade": _grade(score),
        "stability_status": stability_status,
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
    parser = argparse.ArgumentParser(description="Generate TESTNET_DRY_RUN stability score")
    parser.add_argument("--stability-review-packet", required=True)
    parser.add_argument("--repeatability-report", required=True)
    parser.add_argument("--first-result-score-report", required=True)
    parser.add_argument("--second-result-score-report", required=True)
    parser.add_argument("--output")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    report = generate_stability_score(
        load_json(args.stability_review_packet),
        load_json(args.repeatability_report),
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
