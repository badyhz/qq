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

ALLOWED_ACTIONS = ["READ_REPORTS", "TESTNET_DRY_RUN_ONLY", "REVIEW_NEXT_DRY_RUN_ARTIFACTS"]


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


def _sha(payload: Dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


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


def verify_consistency(review_packet: Optional[Dict[str, Any]], materialization_report: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    violations: List[str] = []

    if not (
        review_packet
        and review_packet.get("ok") is True
        and review_packet.get("final_decision") == "READY_FOR_NEXT_TESTNET_DRY_RUN_PAYLOAD_MATERIALIZATION_CONSISTENCY_REVIEW"
    ):
        violations.append("REVIEW_PACKET_NOT_READY")

    if not (
        materialization_report
        and materialization_report.get("ok") is True
        and materialization_report.get("materialization_status") == "NEXT_ARTIFACT_ONLY_MATERIALIZATION_REPORTED"
    ):
        violations.append("MATERIALIZATION_REPORT_NOT_READY")

    payload = (materialization_report or {}).get("materialized_payload")
    if not isinstance(payload, dict):
        violations.append("MATERIALIZED_PAYLOAD_MISSING")

    expected = (materialization_report or {}).get("payload_digest")
    if not expected:
        violations.append("PAYLOAD_DIGEST_MISSING")

    recomputed = None
    if isinstance(payload, dict):
        recomputed = _sha(payload)
        if expected and recomputed != expected:
            violations.append("PAYLOAD_DIGEST_MISMATCH")

        if payload.get("dry_run_only") is not True:
            violations.append("DRY_RUN_ONLY_NOT_CONFIRMED")
        if payload.get("artifact_only") is not True:
            violations.append("ARTIFACT_ONLY_NOT_CONFIRMED")

    artifact = (materialization_report or {}).get("artifact_report") or {}
    if artifact.get("status") != "NEXT_ARTIFACT_ONLY_NO_SUBMIT_MATERIALIZED":
        violations.append("ARTIFACT_REPORT_NOT_CONFIRMED")

    attempted = False
    if isinstance(payload, dict):
        attempted = attempted or payload.get("exchange_api_call_attempted") is True
        attempted = attempted or payload.get("submit_attempted") is True
        attempted = attempted or payload.get("cancel_attempted") is True
        attempted = attempted or payload.get("flatten_attempted") is True

    attempted = attempted or artifact.get("exchange_api_call_attempted") is True
    attempted = attempted or artifact.get("submit_attempted") is True
    attempted = attempted or artifact.get("cancel_attempted") is True
    attempted = attempted or artifact.get("flatten_attempted") is True

    if attempted:
        violations.append("EXCHANGE_OR_SUBMIT_ATTEMPT_DETECTED")

    ok = len(violations) == 0

    if ok:
        status = "NEXT_PAYLOAD_MATERIALIZATION_CONSISTENCY_VERIFIED"
        final_decision = "READY_FOR_NEXT_TESTNET_DRY_RUN_NO_SUBMIT_SAFETY_EVIDENCE_REVIEW"
        safety_flags = _flags(True)
    else:
        status = "NEXT_PAYLOAD_MATERIALIZATION_CONSISTENCY_BLOCKED"
        final_decision = "BLOCK_NEXT_TESTNET_DRY_RUN_RESULT_REVIEW"
        safety_flags = _flags(False)

    return {
        "ok": ok,
        "task": "T482",
        "phase": "NEXT_TESTNET_DRY_RUN_RESULT_REVIEW",
        "consistency_status": status,
        "recomputed_payload_digest": recomputed,
        "expected_payload_digest": expected,
        "consistency_checks": [
            "REVIEW_PACKET_READY",
            "MATERIALIZATION_REPORT_READY",
            "PAYLOAD_DIGEST_MATCH",
            "DRY_RUN_ONLY_CONFIRMED",
            "ARTIFACT_ONLY_CONFIRMED",
            "ARTIFACT_REPORT_CONFIRMED",
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
    parser = argparse.ArgumentParser(description="Verify next TESTNET_DRY_RUN payload materialization consistency")
    parser.add_argument("--review-packet", required=True)
    parser.add_argument("--materialization-report", required=True)
    parser.add_argument("--output")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    report = verify_consistency(load_json(args.review_packet), load_json(args.materialization_report))

    if args.output and not write_json(args.output, report):
        print("Failed to write output", file=sys.stderr)
        return 1
    if args.json or not args.output:
        print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
