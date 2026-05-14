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
    "GENERATE_NEXT_DRY_RUN_ARTIFACT",
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


def materialize_artifact_report(payload_plan: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    violations: List[str] = []

    ready = bool(
        payload_plan
        and payload_plan.get("ok") is True
        and payload_plan.get("payload_plan_status") == "NEXT_NO_SUBMIT_PAYLOAD_PLAN_READY"
    )
    if not ready:
        violations.append("PAYLOAD_PLAN_NOT_READY")

    planned_payload = (payload_plan or {}).get("planned_payload")
    if not isinstance(planned_payload, dict):
        violations.append("PLANNED_PAYLOAD_MISSING")
    else:
        if planned_payload.get("submit_enabled") is not False:
            violations.append("SUBMIT_ENABLED")
        if planned_payload.get("cancel_enabled") is not False:
            violations.append("CANCEL_ENABLED")
        if planned_payload.get("flatten_enabled") is not False:
            violations.append("FLATTEN_ENABLED")
        if planned_payload.get("exchange_api_calls_enabled") is not False:
            violations.append("EXCHANGE_API_CALLS_ENABLED")

    ok = len(violations) == 0

    if ok:
        materialized_payload = dict(planned_payload)
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
        artifact_report = {
            "status": "NEXT_ARTIFACT_ONLY_NO_SUBMIT_MATERIALIZED",
            "exchange_api_call_attempted": False,
            "submit_attempted": False,
            "cancel_attempted": False,
            "flatten_attempted": False,
        }
        materialization_status = "NEXT_ARTIFACT_ONLY_MATERIALIZATION_REPORTED"
        final_decision = "READY_FOR_NEXT_DRY_RUN_ONLY_ITERATION_PHASE_CONTROL"
        safety_flags = _safety_flags(True)
    else:
        materialized_payload = None
        payload_digest = None
        artifact_report = None
        materialization_status = "NEXT_ARTIFACT_MATERIALIZATION_BLOCKED"
        final_decision = "BLOCK_NEXT_TESTNET_DRY_RUN_ONLY_ITERATION"
        safety_flags = _safety_flags(False)

    return {
        "ok": ok,
        "task": "T479",
        "phase": "NEXT_TESTNET_DRY_RUN_ONLY_ITERATION",
        "materialization_status": materialization_status,
        "violations": violations,
        "materialized_payload": materialized_payload,
        "payload_digest": payload_digest,
        "artifact_report": artifact_report,
        "safety_flags": safety_flags,
        "allowed_actions": list(ALLOWED_ACTIONS),
        "blocked_actions": list(REQUIRED_BLOCKED_ACTIONS),
        "final_decision": final_decision,
        "notes": [],
    }


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    parser = argparse.ArgumentParser(description="Materialize next TESTNET_DRY_RUN artifact report")
    parser.add_argument("--payload-plan", required=True)
    parser.add_argument("--output")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    report = materialize_artifact_report(load_json(args.payload_plan))

    if args.output and not write_json(args.output, report):
        print("Failed to write output", file=sys.stderr)
        return 1
    if args.json or not args.output:
        print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))

    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
