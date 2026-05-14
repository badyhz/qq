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

ALLOWED_ACTIONS_PASS = [
    "READ_REPORTS",
    "TESTNET_DRY_RUN_ONLY",
    "MATERIALIZE_PAYLOAD_ARTIFACT",
    "GENERATE_TESTNET_DRY_RUN_ONLY_EXECUTION_PHASE_CONTROL_REPORT",
]
ALLOWED_ACTIONS_BLOCKED = [
    "READ_REPORTS",
    "MATERIALIZE_PAYLOAD_ARTIFACT",
    "GENERATE_TESTNET_DRY_RUN_ONLY_EXECUTION_PHASE_CONTROL_REPORT",
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


def _safe(report: Optional[Dict[str, Any]]) -> bool:
    if not report:
        return False
    s = report.get("safety_flags") or {}
    if s.get("exchange_api_calls_allowed", False) is not False:
        return False
    if s.get("testnet_submit_allowed") is not False:
        return False
    if s.get("real_submit_allowed") is not False:
        return False
    if s.get("submit_order_allowed", False) is not False:
        return False
    if s.get("cancel_order_allowed", False) is not False:
        return False
    if s.get("flatten_position_allowed", False) is not False:
        return False
    if s.get("submit_attempted") is not False:
        return False
    if s.get("cancel_attempted") is not False:
        return False
    if s.get("flatten_attempted") is not False:
        return False

    allowed = report.get("allowed_actions") or []
    blocked = report.get("blocked_actions") or []
    for x in REQUIRED_BLOCKED_ACTIONS:
        if x in allowed:
            return False
        if x not in blocked:
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


def generate_phase_control_report(
    execution_packet: Optional[Dict[str, Any]],
    materialized_payload: Optional[Dict[str, Any]],
    execution_result_report: Optional[Dict[str, Any]],
    artifact_verification_report: Optional[Dict[str, Any]],
    execution_packet_path: str,
    materialized_payload_path: str,
    execution_result_report_path: str,
    artifact_verification_report_path: str,
) -> Dict[str, Any]:
    blockers: List[str] = []

    t461_ok = bool(execution_packet and execution_packet.get("final_decision") == "READY_FOR_TESTNET_DRY_RUN_NO_SUBMIT_PAYLOAD_MATERIALIZATION")
    t462_ok = bool(materialized_payload and materialized_payload.get("final_decision") == "READY_FOR_TESTNET_DRY_RUN_ONLY_EXECUTION_RESULT_REPORT")
    t463_ok = bool(execution_result_report and execution_result_report.get("final_decision") == "READY_FOR_TESTNET_DRY_RUN_ONLY_ARTIFACT_VERIFICATION")
    t464_ok = bool(artifact_verification_report and artifact_verification_report.get("final_decision") == "READY_FOR_TESTNET_DRY_RUN_ONLY_EXECUTION_PHASE_CONTROL")

    if not t461_ok:
        blockers.append("T461_EXECUTION_PACKET_NOT_READY")
    if not t462_ok:
        blockers.append("T462_PAYLOAD_MATERIALIZATION_NOT_READY")
    if not t463_ok:
        blockers.append("T463_EXECUTION_RESULT_NOT_READY")
    if not t464_ok:
        blockers.append("T464_ARTIFACT_VERIFICATION_NOT_READY")

    safe = _safe(execution_packet) and _safe(materialized_payload) and _safe(execution_result_report) and _safe(artifact_verification_report)
    if not safe:
        blockers.append("SUBMIT_CANCEL_FLATTEN_BLOCK_NOT_CONFIRMED")

    ok = len(blockers) == 0

    if ok:
        phase_completion_status = "COMPLETED_TESTNET_DRY_RUN_ONLY_EXECUTION"
        next_phase = "TESTNET_DRY_RUN_RESULT_REVIEW"
        final_decision = "READY_FOR_TESTNET_DRY_RUN_RESULT_REVIEW"
        safety_flags = _flags(True)
        allowed_actions = list(ALLOWED_ACTIONS_PASS)
    else:
        phase_completion_status = "BLOCKED"
        next_phase = "TESTNET_DRY_RUN_ONLY_EXECUTION"
        final_decision = "CONTINUE_TESTNET_DRY_RUN_ONLY_EXECUTION"
        safety_flags = _flags(False)
        allowed_actions = list(ALLOWED_ACTIONS_BLOCKED)

    return {
        "ok": ok,
        "task": "T465",
        "phase": "TESTNET_DRY_RUN_ONLY_EXECUTION",
        "source_reports": {
            "execution_packet": execution_packet_path,
            "materialized_payload": materialized_payload_path,
            "execution_result_report": execution_result_report_path,
            "artifact_verification_report": artifact_verification_report_path,
        },
        "phase_completion_status": phase_completion_status,
        "current_phase": "TESTNET_DRY_RUN_ONLY_EXECUTION",
        "next_phase": next_phase,
        "component_statuses": {
            "t461": t461_ok,
            "t462": t462_ok,
            "t463": t463_ok,
            "t464": t464_ok,
            "submit_cancel_flatten_block_confirmed": safe,
        },
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
    p = argparse.ArgumentParser(description="Generate TESTNET_DRY_RUN_ONLY execution phase control report")
    p.add_argument("--execution-packet", required=True)
    p.add_argument("--materialized-payload", required=True)
    p.add_argument("--execution-result-report", required=True)
    p.add_argument("--artifact-verification-report", required=True)
    p.add_argument("--output")
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)

    t461 = load_json(a.execution_packet)
    t462 = load_json(a.materialized_payload)
    t463 = load_json(a.execution_result_report)
    t464 = load_json(a.artifact_verification_report)
    report = generate_phase_control_report(t461, t462, t463, t464, a.execution_packet, a.materialized_payload, a.execution_result_report, a.artifact_verification_report)

    if a.output and not write_json(a.output, report):
        print("Failed to write output", file=sys.stderr)
        return 1
    if a.json or not a.output:
        print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
