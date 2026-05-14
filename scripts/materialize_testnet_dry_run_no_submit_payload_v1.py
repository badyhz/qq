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
    "MATERIALIZE_PAYLOAD_ARTIFACT",
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


def _block_ok(report: Optional[Dict[str, Any]]) -> bool:
    if not report:
        return False
    s = report.get("safety_flags") or {}
    return (
        s.get("exchange_api_calls_allowed", False) is False
        and s.get("testnet_submit_allowed") is False
        and s.get("real_submit_allowed") is False
        and s.get("submit_order_allowed", False) is False
        and s.get("cancel_order_allowed", False) is False
        and s.get("flatten_position_allowed", False) is False
        and s.get("submit_attempted") is False
        and s.get("cancel_attempted") is False
        and s.get("flatten_attempted") is False
    )


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


def materialize_payload(execution_packet: Optional[Dict[str, Any]], payload_plan: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    violations: List[str] = []

    if not (execution_packet and execution_packet.get("ok") is True and execution_packet.get("final_decision") == "READY_FOR_TESTNET_DRY_RUN_NO_SUBMIT_PAYLOAD_MATERIALIZATION"):
        violations.append("EXECUTION_PACKET_NOT_READY")

    if not (payload_plan and payload_plan.get("ok") is True and payload_plan.get("payload_plan_status") == "NO_SUBMIT_PAYLOAD_PLAN_READY"):
        violations.append("PAYLOAD_PLAN_NOT_READY")

    planned = (payload_plan or {}).get("planned_payload")
    if not isinstance(planned, dict):
        violations.append("PLANNED_PAYLOAD_MISSING")

    if not (_block_ok(execution_packet) and _block_ok(payload_plan)):
        violations.append("SUBMIT_CANCEL_FLATTEN_BLOCK_NOT_CONFIRMED")

    ok = len(violations) == 0

    materialized_payload = None
    payload_digest = None
    source_candidate_id = None

    if ok:
        materialized_payload = dict(planned)
        materialized_payload.update(
            {
                "dry_run_only": True,
                "artifact_only": True,
                "exchange_api_call_attempted": False,
                "submit_attempted": False,
                "cancel_attempted": False,
                "flatten_attempted": False,
            }
        )
        payload_digest = _digest(materialized_payload)
        source_candidate_id = (payload_plan or {}).get("candidate_summary", {}).get("candidate_id")
        status = "NO_SUBMIT_PAYLOAD_MATERIALIZED"
        final_decision = "READY_FOR_TESTNET_DRY_RUN_ONLY_EXECUTION_RESULT_REPORT"
        safety_flags = _flags(True)
    else:
        status = "PAYLOAD_MATERIALIZATION_BLOCKED"
        final_decision = "BLOCK_TESTNET_DRY_RUN_ONLY_EXECUTION"
        safety_flags = _flags(False)

    return {
        "ok": ok,
        "task": "T462",
        "phase": "TESTNET_DRY_RUN_ONLY_EXECUTION",
        "materialization_status": status,
        "violations": violations,
        "materialized_payload": materialized_payload,
        "payload_digest": payload_digest,
        "source_candidate_id": source_candidate_id,
        "safety_flags": safety_flags,
        "allowed_actions": list(ALLOWED_ACTIONS),
        "blocked_actions": list(REQUIRED_BLOCKED_ACTIONS),
        "final_decision": final_decision,
        "notes": [],
    }


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    p = argparse.ArgumentParser(description="Materialize TESTNET_DRY_RUN no-submit payload")
    p.add_argument("--execution-packet", required=True)
    p.add_argument("--payload-plan", required=True)
    p.add_argument("--output")
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)

    ep = load_json(a.execution_packet)
    pp = load_json(a.payload_plan)
    report = materialize_payload(ep, pp)

    if a.output and not write_json(a.output, report):
        print("Failed to write output", file=sys.stderr)
        return 1
    if a.json or not a.output:
        print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
