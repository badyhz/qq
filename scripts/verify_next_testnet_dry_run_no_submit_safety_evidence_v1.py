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


def _attempts(report: Optional[Dict[str, Any]]) -> Dict[str, bool]:
    s = (report or {}).get("safety_flags") or {}
    return {
        "exchange": s.get("exchange_api_calls_allowed") is True,
        "submit": s.get("submit_attempted") is True,
        "cancel": s.get("cancel_attempted") is True,
        "flatten": s.get("flatten_attempted") is True,
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


def verify_safety_evidence(consistency_report: Optional[Dict[str, Any]], materialization_report: Optional[Dict[str, Any]], phase_control_report: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    violations: List[str] = []

    if not (
        consistency_report
        and consistency_report.get("ok") is True
        and consistency_report.get("final_decision") == "READY_FOR_NEXT_TESTNET_DRY_RUN_NO_SUBMIT_SAFETY_EVIDENCE_REVIEW"
    ):
        violations.append("CONSISTENCY_REPORT_NOT_READY")

    if not (materialization_report and materialization_report.get("ok") is True):
        violations.append("MATERIALIZATION_REPORT_NOT_READY")

    if not (phase_control_report and phase_control_report.get("ok") is True):
        violations.append("PHASE_CONTROL_REPORT_NOT_READY")

    artifact = (materialization_report or {}).get("artifact_report") or {}
    if artifact.get("status") != "NEXT_ARTIFACT_ONLY_NO_SUBMIT_MATERIALIZED":
        violations.append("ARTIFACT_ONLY_MATERIALIZATION_NOT_CONFIRMED")

    if (phase_control_report or {}).get("final_decision") != "READY_FOR_NEXT_TESTNET_DRY_RUN_RESULT_REVIEW":
        violations.append("PHASE_CONTROL_NOT_READY")

    attempts = _attempts(consistency_report)
    attempts_m = {
        "exchange": artifact.get("exchange_api_call_attempted") is True,
        "submit": artifact.get("submit_attempted") is True,
        "cancel": artifact.get("cancel_attempted") is True,
        "flatten": artifact.get("flatten_attempted") is True,
    }
    attempts_p = _attempts(phase_control_report)

    if attempts["exchange"] or attempts_m["exchange"] or attempts_p["exchange"]:
        violations.append("EXCHANGE_API_ATTEMPT_DETECTED")
    if attempts["submit"] or attempts_m["submit"] or attempts_p["submit"]:
        violations.append("SUBMIT_ATTEMPT_DETECTED")
    if attempts["cancel"] or attempts_m["cancel"] or attempts_p["cancel"]:
        violations.append("CANCEL_ATTEMPT_DETECTED")
    if attempts["flatten"] or attempts_m["flatten"] or attempts_p["flatten"]:
        violations.append("FLATTEN_ATTEMPT_DETECTED")

    ok = len(violations) == 0

    if ok:
        status = "NEXT_DRY_RUN_NO_SUBMIT_SAFETY_EVIDENCE_VERIFIED"
        final_decision = "READY_FOR_NEXT_TESTNET_DRY_RUN_RESULT_REVIEW_SCORE"
        safety_flags = _flags(True)
    else:
        status = "NEXT_DRY_RUN_SAFETY_EVIDENCE_BLOCKED"
        final_decision = "BLOCK_NEXT_TESTNET_DRY_RUN_RESULT_REVIEW"
        safety_flags = _flags(False)

    return {
        "ok": ok,
        "task": "T483",
        "phase": "NEXT_TESTNET_DRY_RUN_RESULT_REVIEW",
        "safety_evidence_status": status,
        "evidence_summary": {
            "artifact_report_status": artifact.get("status"),
            "phase_control_final_decision": (phase_control_report or {}).get("final_decision"),
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
    parser = argparse.ArgumentParser(description="Verify next TESTNET_DRY_RUN no-submit safety evidence")
    parser.add_argument("--consistency-report", required=True)
    parser.add_argument("--materialization-report", required=True)
    parser.add_argument("--phase-control-report", required=True)
    parser.add_argument("--output")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    report = verify_safety_evidence(
        load_json(args.consistency_report),
        load_json(args.materialization_report),
        load_json(args.phase_control_report),
    )

    if args.output and not write_json(args.output, report):
        print("Failed to write output", file=sys.stderr)
        return 1
    if args.json or not args.output:
        print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
