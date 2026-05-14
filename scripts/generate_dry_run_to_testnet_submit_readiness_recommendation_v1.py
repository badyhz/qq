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

REQUIRED_NEXT_REVIEWS = [
    "TESTNET_SUBMIT_READINESS_REVIEW",
    "TESTNET_SUBMIT_SAFETY_CONSTRAINT_REVIEW",
    "TESTNET_SUBMIT_PAYLOAD_REVIEW",
    "MANUAL_TESTNET_SUBMIT_APPROVAL_REVIEW",
    "FINAL_TESTNET_SUBMIT_GATE",
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


def generate_recommendation(stability_score_report: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    ready = bool(
        stability_score_report
        and stability_score_report.get("ok") is True
        and stability_score_report.get("stability_score") == 100
        and stability_score_report.get("stability_status") == "TESTNET_DRY_RUN_STABILITY_CONFIRMED"
        and stability_score_report.get("final_decision") == "READY_FOR_DRY_RUN_TO_TESTNET_SUBMIT_READINESS_RECOMMENDATION"
        and _safe(stability_score_report)
    )

    if ready:
        ok = True
        recommendation_status = "DRY_RUN_TO_TESTNET_SUBMIT_READINESS_RECOMMENDED"
        recommendation = "PROCEED_TO_TESTNET_SUBMIT_READINESS_REVIEW"
        recommendation_scope = "REVIEW_ONLY_NOT_APPROVAL_TO_SUBMIT"
        final_decision = "READY_FOR_TESTNET_SUBMIT_READINESS_REVIEW_PHASE_CONTROL"
        safety_flags = _flags(True)
        allowed_actions = list(ALLOWED_PASS)
        notes = []
    else:
        ok = False
        recommendation_status = "BLOCKED"
        recommendation = "CONTINUE_TESTNET_DRY_RUN_STABILITY_REVIEW"
        recommendation_scope = None
        final_decision = "BLOCK_TESTNET_DRY_RUN_STABILITY_REVIEW"
        safety_flags = _flags(False)
        allowed_actions = list(ALLOWED_BLOCKED)
        notes = []

    return {
        "ok": ok,
        "task": "T489",
        "phase": "TESTNET_DRY_RUN_STABILITY_REVIEW",
        "recommendation_status": recommendation_status,
        "recommendation": recommendation,
        "recommendation_scope": recommendation_scope,
        "required_next_reviews": list(REQUIRED_NEXT_REVIEWS),
        "safety_flags": safety_flags,
        "allowed_actions": allowed_actions,
        "blocked_actions": list(REQUIRED_BLOCKED_ACTIONS),
        "final_decision": final_decision,
        "notes": notes,
    }


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    parser = argparse.ArgumentParser(description="Generate dry-run to testnet submit readiness recommendation")
    parser.add_argument("--stability-score-report", required=True)
    parser.add_argument("--output")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    report = generate_recommendation(load_json(args.stability_score_report))

    if args.output and not write_json(args.output, report):
        print("Failed to write output", file=sys.stderr)
        return 1
    if args.json or not args.output:
        print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
