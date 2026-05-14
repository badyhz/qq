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


def build_payload_plan(candidate_artifact: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    violations: List[str] = []

    ready = bool(
        candidate_artifact
        and candidate_artifact.get("ok") is True
        and candidate_artifact.get("candidate_artifact_status") == "NEXT_DRY_RUN_CANDIDATE_INPUT_READY"
    )
    if not ready:
        violations.append("CANDIDATE_ARTIFACT_NOT_READY")

    candidate_input = (candidate_artifact or {}).get("candidate_input") or {}

    if candidate_input.get("dry_run_only") is not True:
        violations.append("CANDIDATE_NOT_DRY_RUN_ONLY")
    if candidate_input.get("artifact_only") is not True:
        violations.append("CANDIDATE_NOT_ARTIFACT_ONLY")

    symbol = str(candidate_input.get("symbol") or "").strip()
    side = str(candidate_input.get("side") or "").strip().upper()
    quantity = str(candidate_input.get("quantity") or "").strip()
    order_type = str(candidate_input.get("order_type") or "").strip()

    if not symbol:
        violations.append("SYMBOL_MISSING")
    if side not in ["BUY", "SELL"]:
        violations.append("INVALID_SIDE")
    if not quantity:
        violations.append("QUANTITY_MISSING")
    if not order_type:
        violations.append("ORDER_TYPE_MISSING")

    ok = len(violations) == 0

    if ok:
        payload_plan_status = "NEXT_NO_SUBMIT_PAYLOAD_PLAN_READY"
        planned_payload = dict(candidate_input)
        planned_payload.update(
            {
                "payload_plan_version": "v1",
                "submit_enabled": False,
                "cancel_enabled": False,
                "flatten_enabled": False,
                "exchange_api_calls_enabled": False,
            }
        )
        final_decision = "READY_FOR_NEXT_ARTIFACT_ONLY_MATERIALIZATION_REPORT"
        safety_flags = _safety_flags(True)
    else:
        payload_plan_status = "NEXT_PAYLOAD_PLAN_BLOCKED"
        planned_payload = None
        final_decision = "BLOCK_NEXT_TESTNET_DRY_RUN_ONLY_ITERATION"
        safety_flags = _safety_flags(False)

    return {
        "ok": ok,
        "task": "T478",
        "phase": "NEXT_TESTNET_DRY_RUN_ONLY_ITERATION",
        "payload_plan_status": payload_plan_status,
        "violations": violations,
        "candidate_summary": {
            "candidate_id": candidate_input.get("candidate_id"),
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "order_type": order_type,
            "dry_run_only": candidate_input.get("dry_run_only"),
            "artifact_only": candidate_input.get("artifact_only"),
        },
        "planned_payload": planned_payload,
        "safety_flags": safety_flags,
        "allowed_actions": list(ALLOWED_ACTIONS),
        "blocked_actions": list(REQUIRED_BLOCKED_ACTIONS),
        "final_decision": final_decision,
        "notes": [],
    }


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    parser = argparse.ArgumentParser(description="Build next TESTNET_DRY_RUN no-submit payload plan")
    parser.add_argument("--candidate-artifact", required=True)
    parser.add_argument("--output")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    report = build_payload_plan(load_json(args.candidate_artifact))

    if args.output and not write_json(args.output, report):
        print("Failed to write output", file=sys.stderr)
        return 1
    if args.json or not args.output:
        print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))

    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
