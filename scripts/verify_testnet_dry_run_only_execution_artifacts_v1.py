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
    "MATERIALIZE_PAYLOAD_ARTIFACT",
    "VERIFY_TESTNET_DRY_RUN_ONLY_EXECUTION_ARTIFACTS",
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


def verify_execution_artifacts(materialized_payload: Optional[Dict[str, Any]], execution_result_report: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    violations: List[str] = []

    if not (
        materialized_payload
        and materialized_payload.get("ok") is True
        and materialized_payload.get("materialization_status") == "NO_SUBMIT_PAYLOAD_MATERIALIZED"
    ):
        violations.append("MATERIALIZED_PAYLOAD_NOT_READY")

    if not (
        execution_result_report
        and execution_result_report.get("ok") is True
        and execution_result_report.get("execution_result_status") == "TESTNET_DRY_RUN_ONLY_EXECUTION_REPORTED"
    ):
        violations.append("EXECUTION_RESULT_REPORT_NOT_READY")

    if not (materialized_payload or {}).get("payload_digest"):
        violations.append("PAYLOAD_DIGEST_MISSING")

    simulated = (execution_result_report or {}).get("simulated_execution_summary") or {}
    if simulated.get("status") != "ARTIFACT_ONLY_NO_SUBMIT_COMPLETED":
        violations.append("SIMULATED_EXECUTION_NOT_COMPLETED")

    payload = (materialized_payload or {}).get("materialized_payload") or {}
    attempted_detected = any(
        [
            payload.get("exchange_api_call_attempted") is True,
            payload.get("submit_attempted") is True,
            payload.get("cancel_attempted") is True,
            payload.get("flatten_attempted") is True,
            simulated.get("exchange_api_call_attempted") is True,
            simulated.get("submit_attempted") is True,
            simulated.get("cancel_attempted") is True,
            simulated.get("flatten_attempted") is True,
        ]
    )
    if attempted_detected:
        violations.append("SUBMIT_CANCEL_FLATTEN_ATTEMPT_DETECTED")

    ok = len(violations) == 0

    if ok:
        status = "TESTNET_DRY_RUN_ONLY_ARTIFACTS_VERIFIED"
        final_decision = "READY_FOR_TESTNET_DRY_RUN_ONLY_EXECUTION_PHASE_CONTROL"
        safety_flags = _flags(True)
        verified_artifacts = ["T462_MATERIALIZED_PAYLOAD", "T463_EXECUTION_RESULT_REPORT"]
    else:
        status = "TESTNET_DRY_RUN_ONLY_ARTIFACT_VERIFICATION_BLOCKED"
        final_decision = "BLOCK_TESTNET_DRY_RUN_ONLY_EXECUTION"
        safety_flags = _flags(False)
        verified_artifacts = []

    return {
        "ok": ok,
        "task": "T464",
        "phase": "TESTNET_DRY_RUN_ONLY_EXECUTION",
        "artifact_verification_status": status,
        "verified_artifacts": verified_artifacts,
        "violations": violations,
        "safety_flags": safety_flags,
        "allowed_actions": list(ALLOWED_ACTIONS),
        "blocked_actions": list(REQUIRED_BLOCKED_ACTIONS),
        "final_decision": final_decision,
        "notes": [],
    }


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    p = argparse.ArgumentParser(description="Verify TESTNET_DRY_RUN_ONLY execution artifacts")
    p.add_argument("--materialized-payload", required=True)
    p.add_argument("--execution-result-report", required=True)
    p.add_argument("--output")
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)

    m = load_json(a.materialized_payload)
    r = load_json(a.execution_result_report)
    report = verify_execution_artifacts(m, r)

    if a.output and not write_json(a.output, report):
        print("Failed to write output", file=sys.stderr)
        return 1
    if a.json or not a.output:
        print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
