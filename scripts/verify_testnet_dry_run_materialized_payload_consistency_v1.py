#!/usr/bin/env python3
import argparse
import hashlib
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


def _digest(payload: Dict[str, Any]) -> str:
    s = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


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


def verify_payload_consistency(review_packet: Optional[Dict[str, Any]], materialized_payload_report: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    violations: List[str] = []

    if not (
        review_packet
        and review_packet.get("ok") is True
        and review_packet.get("final_decision") == "READY_FOR_TESTNET_DRY_RUN_MATERIALIZED_PAYLOAD_CONSISTENCY_REVIEW"
    ):
        violations.append("REVIEW_PACKET_NOT_READY")

    if not (
        materialized_payload_report
        and materialized_payload_report.get("ok") is True
        and materialized_payload_report.get("materialization_status") == "NO_SUBMIT_PAYLOAD_MATERIALIZED"
    ):
        violations.append("MATERIALIZED_PAYLOAD_NOT_READY")

    payload = (materialized_payload_report or {}).get("materialized_payload")
    if not isinstance(payload, dict):
        violations.append("MATERIALIZED_PAYLOAD_MISSING")

    expected = (materialized_payload_report or {}).get("payload_digest")
    if not expected:
        violations.append("PAYLOAD_DIGEST_MISSING")

    recomputed = None
    if isinstance(payload, dict):
        recomputed = _digest(payload)
        if expected and recomputed != expected:
            violations.append("PAYLOAD_DIGEST_MISMATCH")

    if isinstance(payload, dict) and payload.get("dry_run_only") is not True:
        violations.append("DRY_RUN_ONLY_NOT_CONFIRMED")

    if isinstance(payload, dict) and payload.get("artifact_only") is not True:
        violations.append("ARTIFACT_ONLY_NOT_CONFIRMED")

    if isinstance(payload, dict) and any(
        [
            payload.get("exchange_api_call_attempted") is True,
            payload.get("submit_attempted") is True,
            payload.get("cancel_attempted") is True,
            payload.get("flatten_attempted") is True,
        ]
    ):
        violations.append("EXCHANGE_OR_SUBMIT_ATTEMPT_DETECTED")

    ok = len(violations) == 0

    if ok:
        consistency_status = "MATERIALIZED_PAYLOAD_CONSISTENCY_VERIFIED"
        final_decision = "READY_FOR_TESTNET_DRY_RUN_RESULT_SAFETY_EVIDENCE_REVIEW"
        safety_flags = _flags(True)
    else:
        consistency_status = "MATERIALIZED_PAYLOAD_CONSISTENCY_BLOCKED"
        final_decision = "BLOCK_TESTNET_DRY_RUN_RESULT_REVIEW"
        safety_flags = _flags(False)

    return {
        "ok": ok,
        "task": "T467",
        "phase": "TESTNET_DRY_RUN_RESULT_REVIEW",
        "consistency_status": consistency_status,
        "recomputed_payload_digest": recomputed,
        "expected_payload_digest": expected,
        "consistency_checks": [
            "REVIEW_PACKET_READY",
            "MATERIALIZED_PAYLOAD_READY",
            "PAYLOAD_DIGEST_MATCH",
            "DRY_RUN_ONLY_CONFIRMED",
            "ARTIFACT_ONLY_CONFIRMED",
            "NO_EXCHANGE_OR_SUBMIT_ATTEMPT",
        ],
        "violations": violations,
        "safety_flags": safety_flags,
        "allowed_actions": list(ALLOWED_ACTIONS),
        "blocked_actions": list(REQUIRED_BLOCKED_ACTIONS),
        "final_decision": final_decision,
        "notes": [],
    }


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    p = argparse.ArgumentParser(description="Verify TESTNET_DRY_RUN materialized payload consistency")
    p.add_argument("--review-packet", required=True)
    p.add_argument("--materialized-payload", required=True)
    p.add_argument("--output")
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)

    rp = load_json(a.review_packet)
    mp = load_json(a.materialized_payload)
    report = verify_payload_consistency(rp, mp)

    if a.output and not write_json(a.output, report):
        print("Failed to write output", file=sys.stderr)
        return 1
    if a.json or not a.output:
        print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
