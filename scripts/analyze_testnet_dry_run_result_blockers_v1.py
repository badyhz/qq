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

ALLOWED_ACTIONS = [
    "READ_REPORTS",
    "TESTNET_DRY_RUN_ONLY",
    "REVIEW_DRY_RUN_ARTIFACTS",
    "GENERATE_NEXT_DRY_RUN_PLAN",
]


def _safety_flags(dry_run_allowed: bool) -> Dict[str, Any]:
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


def _attempt_detected(report: Optional[Dict[str, Any]]) -> bool:
    s = (report or {}).get("safety_flags") or {}
    return bool(
        s.get("exchange_api_calls_allowed") is True
        or s.get("submit_attempted") is True
        or s.get("cancel_attempted") is True
        or s.get("flatten_attempted") is True
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


def analyze_blockers(
    iteration_review_packet: Optional[Dict[str, Any]],
    result_review_score_report: Optional[Dict[str, Any]],
    artifact_verification_report: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    blockers: List[str] = []
    warnings: List[str] = []
    improvement_items: List[str] = []

    packet_ready = bool(iteration_review_packet and iteration_review_packet.get("ok") is True)
    score_ready = bool(result_review_score_report and result_review_score_report.get("review_score") is not None)
    artifact_ready = bool(
        artifact_verification_report and artifact_verification_report.get("artifact_verification_status") is not None
    )

    if not packet_ready:
        blockers.append("ITERATION_REVIEW_PACKET_NOT_READY")
    if not score_ready:
        blockers.append("RESULT_REVIEW_SCORE_NOT_READY")
    if not artifact_ready:
        blockers.append("ARTIFACT_VERIFICATION_NOT_READY")

    score = (result_review_score_report or {}).get("review_score")
    artifact_ok = bool(artifact_verification_report and artifact_verification_report.get("ok") is True)

    if score_ready and score != 100:
        blockers.append("DRY_RUN_RESULT_SCORE_BELOW_100")
    if artifact_ready and not artifact_ok:
        blockers.append("ARTIFACT_VERIFICATION_NOT_READY")

    if _attempt_detected(iteration_review_packet) or _attempt_detected(result_review_score_report) or _attempt_detected(artifact_verification_report):
        blockers.append("SUBMIT_CANCEL_FLATTEN_ATTEMPT_DETECTED")

    ok = len(blockers) == 0

    if ok:
        status = "DRY_RUN_RESULT_BLOCKER_ANALYSIS_COMPLETED"
        final_decision = "READY_FOR_NEXT_DRY_RUN_ITERATION_PLAN"
        warnings.append("NO_REAL_MARKET_EXECUTION_YET")
        improvement_items.append("RUN_NEXT_ARTIFACT_ONLY_DRY_RUN_SAMPLE")
        safety_flags = _safety_flags(True)
    else:
        status = "DRY_RUN_RESULT_BLOCKER_ANALYSIS_BLOCKED"
        final_decision = "BLOCK_TESTNET_DRY_RUN_ITERATION_REVIEW"
        safety_flags = _safety_flags(False)

    return {
        "ok": ok,
        "task": "T472",
        "phase": "TESTNET_DRY_RUN_ITERATION_REVIEW",
        "blocker_analysis_status": status,
        "blockers": blockers,
        "warnings": warnings,
        "improvement_items": improvement_items,
        "source_score": score,
        "safety_flags": safety_flags,
        "allowed_actions": list(ALLOWED_ACTIONS),
        "blocked_actions": list(REQUIRED_BLOCKED_ACTIONS),
        "final_decision": final_decision,
        "notes": [],
    }


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    parser = argparse.ArgumentParser(description="Analyze TESTNET_DRY_RUN result blockers")
    parser.add_argument("--iteration-review-packet", required=True)
    parser.add_argument("--result-review-score-report", required=True)
    parser.add_argument("--artifact-verification-report", required=True)
    parser.add_argument("--output")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    report = analyze_blockers(
        load_json(args.iteration_review_packet),
        load_json(args.result_review_score_report),
        load_json(args.artifact_verification_report),
    )

    if args.output and not write_json(args.output, report):
        print("Failed to write output", file=sys.stderr)
        return 1
    if args.json or not args.output:
        print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))

    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
