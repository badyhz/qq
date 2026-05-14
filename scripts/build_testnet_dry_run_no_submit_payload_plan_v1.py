#!/usr/bin/env python3
import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional


REQUIRED_BLOCKED_ACTIONS = [
    "TESTNET_SUBMIT",
    "REAL_SUBMIT",
    "SUBMIT_ORDER",
    "CANCEL_ORDER",
    "FLATTEN_POSITION",
]

ALLOWED_ACTIONS = [
    "READ_REPORTS",
    "TESTNET_DRY_RUN_ONLY",
    "BUILD_TESTNET_DRY_RUN_NO_SUBMIT_PAYLOAD_PLAN",
]

BLOCKED_ACTIONS = list(REQUIRED_BLOCKED_ACTIONS)


def _safety_flags(testnet_dry_run_allowed: bool) -> Dict[str, Any]:
    return {
        "testnet_dry_run_allowed": testnet_dry_run_allowed,
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


def build_payload_plan(mode_packet: Optional[Dict[str, Any]], candidate_input: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    violations: List[str] = []
    mode_ready = bool(
        mode_packet
        and mode_packet.get("ok") is True
        and mode_packet.get("final_decision") == "READY_FOR_TESTNET_DRY_RUN_NO_SUBMIT_PAYLOAD_PLAN"
    )
    if not mode_ready:
        violations.append("MODE_PACKET_NOT_READY")

    candidate = candidate_input or {}

    if candidate.get("dry_run_only") is not True:
        violations.append("CANDIDATE_NOT_DRY_RUN_ONLY")

    symbol = str(candidate.get("symbol") or "").strip()
    side = str(candidate.get("side") or "").strip().upper()
    quantity = str(candidate.get("quantity") or "").strip()
    order_type = str(candidate.get("order_type") or "").strip()

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
        payload_plan_status = "NO_SUBMIT_PAYLOAD_PLAN_READY"
        final_decision = "READY_FOR_TESTNET_DRY_RUN_NO_SUBMIT_RUNNER_GUARD"
        safety_flags = _safety_flags(True)
        planned_payload = {
            "candidate_id": candidate.get("candidate_id"),
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "order_type": order_type,
            "dry_run_only": True,
            "submit_enabled": False,
            "cancel_enabled": False,
            "flatten_enabled": False,
            "exchange_api_calls_enabled": False,
            "artifact_only": True,
        }
    else:
        payload_plan_status = "PAYLOAD_PLAN_BLOCKED"
        final_decision = "BLOCK_TESTNET_DRY_RUN_ONLY_MODE"
        safety_flags = _safety_flags(False)
        planned_payload = None

    return {
        "ok": ok,
        "task": "T457",
        "phase": "TESTNET_DRY_RUN_ONLY_MODE",
        "payload_plan_status": payload_plan_status,
        "violations": violations,
        "candidate_summary": {
            "candidate_id": candidate.get("candidate_id"),
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "order_type": order_type,
            "dry_run_only": candidate.get("dry_run_only"),
        },
        "planned_payload": planned_payload,
        "safety_flags": safety_flags,
        "allowed_actions": list(ALLOWED_ACTIONS),
        "blocked_actions": list(BLOCKED_ACTIONS),
        "final_decision": final_decision,
        "notes": [],
    }


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(description="Build TESTNET_DRY_RUN no-submit payload plan")
    parser.add_argument("--mode-packet", required=True)
    parser.add_argument("--candidate-input", required=True)
    parser.add_argument("--output")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    mode_packet = load_json(args.mode_packet)
    candidate_input = load_json(args.candidate_input)
    report = build_payload_plan(mode_packet, candidate_input)

    if args.output and not write_json(args.output, report):
        print("Failed to write output", file=sys.stderr)
        return 1

    if args.json or not args.output:
        print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))

    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
