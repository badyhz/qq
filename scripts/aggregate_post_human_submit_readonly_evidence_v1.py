#!/usr/bin/env python3
import argparse
import json
import os
import sys
from typing import Any, Dict, Optional


def load_json(path: str) -> Optional[Dict[str, Any]]:
    if not path or not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def write_json(path: str, data: Dict[str, Any]) -> bool:
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, sort_keys=True, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def _has_unsafe_marker(data: Dict[str, Any]) -> bool:
    for k, v in data.items():
        if isinstance(v, str):
            lower = v.lower()
            if "mainnet" in lower or "live" in lower or "api.binance.com" in lower:
                return True
        elif isinstance(v, dict):
            if _has_unsafe_marker(v):
                return True
    return False


def aggregate_evidence(
    receipt_parser: Optional[Dict[str, Any]],
    protection_verification: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    blockers = []
    warnings = []

    payloads = {
        "receipt_parser": receipt_parser,
        "protection_verification": protection_verification,
    }
    for name, value in payloads.items():
        if not isinstance(value, dict):
            blockers.append(f"{name.upper()}_MISSING")

    if str((receipt_parser or {}).get("verdict", "")) != "PASS":
        blockers.append("RECEIPT_PARSER_NOT_PASS")
    if str((protection_verification or {}).get("verdict", "")) != "PASS":
        blockers.append("PROTECTION_VERIFICATION_NOT_PASS")

    env = str((receipt_parser or {}).get("env", "")).strip()
    if env.lower() != "testnet":
        blockers.append("ENV_NOT_TESTNET")

    if _has_unsafe_marker(receipt_parser or {}):
        blockers.append("RECEIPT_PARSER_HAS_UNSAFE_MARKER")
    if _has_unsafe_marker(protection_verification or {}):
        blockers.append("PROTECTION_VERIFICATION_HAS_UNSAFE_MARKER")

    submit_executed = bool((receipt_parser or {}).get("submit_executed", False))

    position_detected = bool((protection_verification or {}).get("position_detected", False))
    protective_orders_detected = bool((protection_verification or {}).get("protective_orders_detected", False))
    stop_market_detected = bool((protection_verification or {}).get("stop_market_detected", False))
    take_profit_market_detected = bool((protection_verification or {}).get("take_profit_market_detected", False))
    orphan_protection_detected = bool((protection_verification or {}).get("orphan_protection_detected", False))
    naked_position_detected = bool((protection_verification or {}).get("naked_position_detected", False))

    if orphan_protection_detected:
        blockers.append("ORPHAN_PROTECTION_DETECTED")
    if naked_position_detected:
        blockers.append("NAKED_POSITION_DETECTED")

    if not submit_executed:
        blockers.append("SUBMIT_EXECUTED_FALSE")

    if blockers:
        verdict = "FAIL"
        ok = False
    elif not (take_profit_market_detected and stop_market_detected):
        verdict = "PARTIAL"
        ok = False
    else:
        verdict = "PASS"
        ok = True

    return {
        "ok": ok,
        "verdict": verdict,
        "evidence_type": "POST_HUMAN_SUBMIT_READONLY_EVIDENCE",
        "readonly": True,
        "env": env,
        "symbol": str((receipt_parser or {}).get("symbol", "")),
        "side": str((receipt_parser or {}).get("side", "")),
        "quantity": str((receipt_parser or {}).get("quantity", "")),
        "submit_executed": submit_executed,
        "order_id_present": bool((receipt_parser or {}).get("order_id_present", False)),
        "position_detected": position_detected,
        "protective_orders_detected": protective_orders_detected,
        "stop_market_detected": stop_market_detected,
        "take_profit_market_detected": take_profit_market_detected,
        "orphan_protection_detected": orphan_protection_detected,
        "naked_position_detected": naked_position_detected,
        "submit_allowed": False,
        "cancel_allowed": False,
        "flatten_allowed": False,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "evidence_items": {
            "receipt_parser": receipt_parser or {},
            "protection_verification": protection_verification or {},
        },
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Aggregate post-human-submit readonly evidence")
    parser.add_argument("--receipt-parser-json", required=True)
    parser.add_argument("--protection-verification-json", required=True)
    parser.add_argument("--output-json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = aggregate_evidence(
        load_json(args.receipt_parser_json),
        load_json(args.protection_verification_json),
    )

    if args.output_json and not write_json(args.output_json, report):
        print("failed_to_write_output", file=sys.stderr)
        return 1
    if args.json:
        if args.pretty:
            print(json.dumps(report, sort_keys=True, indent=2, ensure_ascii=False))
        else:
            print(json.dumps(report, sort_keys=True, ensure_ascii=False))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
