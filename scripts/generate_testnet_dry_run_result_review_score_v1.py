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


def _safe(report: Optional[Dict[str, Any]]) -> bool:
    if not report:
        return False
    s = report.get("safety_flags") or {}
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

    allowed = report.get("allowed_actions") or []
    blocked = report.get("blocked_actions") or []
    for b in REQUIRED_BLOCKED_ACTIONS:
        if b in allowed or b not in blocked:
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


def generate_review_score(review_packet: Optional[Dict[str, Any]], consistency_report: Optional[Dict[str, Any]], safety_evidence_report: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    blockers: List[str] = []

    c1 = bool(review_packet and review_packet.get("ok") is True and review_packet.get("final_decision") == "READY_FOR_TESTNET_DRY_RUN_MATERIALIZED_PAYLOAD_CONSISTENCY_REVIEW")
    c2 = bool(consistency_report and consistency_report.get("ok") is True and consistency_report.get("consistency_status") == "MATERIALIZED_PAYLOAD_CONSISTENCY_VERIFIED")
    c3 = bool(safety_evidence_report and safety_evidence_report.get("ok") is True and safety_evidence_report.get("safety_evidence_status") == "DRY_RUN_RESULT_NO_SUBMIT_SAFETY_EVIDENCE_VERIFIED")
    c4 = _safe(review_packet) and _safe(consistency_report) and _safe(safety_evidence_report)

    if not c1:
        blockers.append("REVIEW_PACKET_NOT_READY")
    if not c2:
        blockers.append("PAYLOAD_CONSISTENCY_NOT_VERIFIED")
    if not c3:
        blockers.append("SAFETY_EVIDENCE_NOT_VERIFIED")
    if not c4:
        blockers.append("NO_SUBMIT_NO_EXCHANGE_BLOCK_NOT_CONFIRMED")

    component_scores = {
        "review_packet_ready": 25 if c1 else 0,
        "payload_consistency_verified": 25 if c2 else 0,
        "safety_evidence_verified": 25 if c3 else 0,
        "execution_still_no_submit_no_exchange": 25 if c4 else 0,
    }
    score = sum(component_scores.values())
    grade = _grade(score)

    if score == 100:
        ok = True
        review_status = "TESTNET_DRY_RUN_RESULT_REVIEW_PASSED"
        final_decision = "READY_FOR_TESTNET_DRY_RUN_RESULT_REVIEW_PHASE_CONTROL"
        safety_flags = _flags(True)
    else:
        ok = False
        review_status = "TESTNET_DRY_RUN_RESULT_REVIEW_BLOCKED"
        final_decision = "BLOCK_TESTNET_DRY_RUN_RESULT_REVIEW"
        safety_flags = _flags(False)

    return {
        "ok": ok,
        "task": "T469",
        "phase": "TESTNET_DRY_RUN_RESULT_REVIEW",
        "component_scores": component_scores,
        "review_score": score,
        "review_grade": grade,
        "review_status": review_status,
        "blockers": blockers,
        "blocker_count": len(blockers),
        "safety_flags": safety_flags,
        "allowed_actions": list(ALLOWED_ACTIONS),
        "blocked_actions": list(REQUIRED_BLOCKED_ACTIONS),
        "final_decision": final_decision,
        "notes": [],
    }


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    p = argparse.ArgumentParser(description="Generate TESTNET_DRY_RUN result review score")
    p.add_argument("--review-packet", required=True)
    p.add_argument("--consistency-report", required=True)
    p.add_argument("--safety-evidence-report", required=True)
    p.add_argument("--output")
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)

    rp = load_json(a.review_packet)
    cr = load_json(a.consistency_report)
    sr = load_json(a.safety_evidence_report)
    report = generate_review_score(rp, cr, sr)

    if a.output and not write_json(a.output, report):
        print("Failed to write output", file=sys.stderr)
        return 1
    if a.json or not a.output:
        print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
