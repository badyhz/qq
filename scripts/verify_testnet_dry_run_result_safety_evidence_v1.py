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


def _safe_flags(report: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    return (report or {}).get("safety_flags") or {}


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


def verify_safety_evidence(consistency_report: Optional[Dict[str, Any]], execution_result_report: Optional[Dict[str, Any]], artifact_verification_report: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    violations: List[str] = []

    if not (
        consistency_report
        and consistency_report.get("ok") is True
        and consistency_report.get("final_decision") == "READY_FOR_TESTNET_DRY_RUN_RESULT_SAFETY_EVIDENCE_REVIEW"
    ):
        violations.append("CONSISTENCY_REPORT_NOT_READY")

    if not (
        execution_result_report
        and execution_result_report.get("ok") is True
        and execution_result_report.get("execution_result_status") == "TESTNET_DRY_RUN_ONLY_EXECUTION_REPORTED"
    ):
        violations.append("EXECUTION_RESULT_REPORT_NOT_READY")

    if not (
        artifact_verification_report
        and artifact_verification_report.get("ok") is True
        and artifact_verification_report.get("artifact_verification_status") == "TESTNET_DRY_RUN_ONLY_ARTIFACTS_VERIFIED"
    ):
        violations.append("ARTIFACT_VERIFICATION_REPORT_NOT_READY")

    simulated = (execution_result_report or {}).get("simulated_execution_summary") or {}
    if simulated.get("status") != "ARTIFACT_ONLY_NO_SUBMIT_COMPLETED":
        violations.append("SIMULATED_EXECUTION_NOT_COMPLETED")

    s1 = _safe_flags(consistency_report)
    s2 = _safe_flags(execution_result_report)
    s3 = _safe_flags(artifact_verification_report)

    if any([s1.get("exchange_api_calls_allowed") is True, s2.get("exchange_api_calls_allowed") is True, s3.get("exchange_api_calls_allowed") is True, simulated.get("exchange_api_call_attempted") is True]):
        violations.append("EXCHANGE_API_ATTEMPT_DETECTED")

    if any([s1.get("submit_attempted") is True, s2.get("submit_attempted") is True, s3.get("submit_attempted") is True, simulated.get("submit_attempted") is True]):
        violations.append("SUBMIT_ATTEMPT_DETECTED")

    if any([s1.get("cancel_attempted") is True, s2.get("cancel_attempted") is True, s3.get("cancel_attempted") is True, simulated.get("cancel_attempted") is True]):
        violations.append("CANCEL_ATTEMPT_DETECTED")

    if any([s1.get("flatten_attempted") is True, s2.get("flatten_attempted") is True, s3.get("flatten_attempted") is True, simulated.get("flatten_attempted") is True]):
        violations.append("FLATTEN_ATTEMPT_DETECTED")

    ok = len(violations) == 0

    if ok:
        status = "DRY_RUN_RESULT_NO_SUBMIT_SAFETY_EVIDENCE_VERIFIED"
        final_decision = "READY_FOR_TESTNET_DRY_RUN_RESULT_REVIEW_SCORE"
        safety_flags = _flags(True)
    else:
        status = "DRY_RUN_RESULT_SAFETY_EVIDENCE_BLOCKED"
        final_decision = "BLOCK_TESTNET_DRY_RUN_RESULT_REVIEW"
        safety_flags = _flags(False)

    return {
        "ok": ok,
        "task": "T468",
        "phase": "TESTNET_DRY_RUN_RESULT_REVIEW",
        "safety_evidence_status": status,
        "evidence_summary": {
            "consistency_ready": consistency_report.get("ok") is True if consistency_report else False,
            "execution_result_ready": execution_result_report.get("ok") is True if execution_result_report else False,
            "artifact_verification_ready": artifact_verification_report.get("ok") is True if artifact_verification_report else False,
            "simulated_status": simulated.get("status"),
        },
        "violations": violations,
        "safety_flags": safety_flags,
        "allowed_actions": list(ALLOWED_ACTIONS),
        "blocked_actions": list(REQUIRED_BLOCKED_ACTIONS),
        "final_decision": final_decision,
        "notes": [],
    }


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    p = argparse.ArgumentParser(description="Verify TESTNET_DRY_RUN result safety evidence")
    p.add_argument("--consistency-report", required=True)
    p.add_argument("--execution-result-report", required=True)
    p.add_argument("--artifact-verification-report", required=True)
    p.add_argument("--output")
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)

    c = load_json(a.consistency_report)
    e = load_json(a.execution_result_report)
    v = load_json(a.artifact_verification_report)
    report = verify_safety_evidence(c, e, v)

    if a.output and not write_json(a.output, report):
        print("Failed to write output", file=sys.stderr)
        return 1
    if a.json or not a.output:
        print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
