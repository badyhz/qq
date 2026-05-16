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


def _has_unsafe_marker(data: Any) -> bool:
    if isinstance(data, str):
        lower = data.lower()
        if "mainnet" in lower or "live" in lower or "api.binance.com" in lower or "fapi.binance.com" in lower:
            return True
    elif isinstance(data, dict):
        for k, v in data.items():
            if _has_unsafe_marker(v):
                return True
    elif isinstance(data, list):
        for item in data:
            if _has_unsafe_marker(item):
                return True
    return False


def parse_receipt(
    verification_eligibility: Optional[Dict[str, Any]],
    execution_receipt: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    blockers = []
    warnings = []

    if not isinstance(verification_eligibility, dict):
        blockers.append("VERIFICATION_ELIGIBILITY_MISSING")
    if not isinstance(execution_receipt, dict):
        blockers.append("EXECUTION_RECEIPT_MISSING")

    if str((verification_eligibility or {}).get("verdict", "")) != "PASS":
        blockers.append("VERIFICATION_ELIGIBILITY_NOT_PASS")

    if _has_unsafe_marker(execution_receipt or {}):
        blockers.append("RECEIPT_HAS_UNSAFE_MARKER")
    if _has_unsafe_marker(verification_eligibility or {}):
        blockers.append("ELIGIBILITY_HAS_UNSAFE_MARKER")

    env = str((execution_receipt or {}).get("env", "")).strip()
    if env.lower() != "testnet":
        blockers.append("ENV_NOT_TESTNET")

    submit_attempted = bool((execution_receipt or {}).get("submit_attempted", False))
    submit_executed = bool((execution_receipt or {}).get("submit_executed", False))
    order_id_present = bool((execution_receipt or {}).get("order_id") is not None and len(str((execution_receipt or {}).get("order_id", "")).strip()) > 0)
    client_order_id_present = bool((execution_receipt or {}).get("client_order_id") is not None and len(str((execution_receipt or {}).get("client_order_id", "")).strip()) > 0)

    symbol = str((execution_receipt or {}).get("symbol", "")).strip()
    side = str((execution_receipt or {}).get("side", "")).strip()
    quantity = str((execution_receipt or {}).get("quantity", "")).strip()

    receipt_status = "UNPARSED"
    if blockers:
        verdict = "FAIL"
        ok = False
        receipt_status = "REJECTED"
    elif submit_attempted and submit_executed and (order_id_present or client_order_id_present):
        verdict = "PASS"
        ok = True
        receipt_status = "ACCEPTED"
    elif submit_attempted and not (submit_executed and (order_id_present or client_order_id_present)):
        verdict = "PARTIAL"
        ok = False
        receipt_status = "AMBIGUOUS"
    else:
        verdict = "PARTIAL"
        ok = False
        receipt_status = "INCOMPLETE"

    return {
        "ok": ok,
        "verdict": verdict,
        "receipt_status": receipt_status,
        "env": env,
        "symbol": symbol,
        "side": side,
        "quantity": quantity,
        "submit_attempted": submit_attempted,
        "submit_executed": submit_executed,
        "order_id_present": order_id_present,
        "client_order_id_present": client_order_id_present,
        "submit_allowed": False,
        "cancel_allowed": False,
        "flatten_allowed": False,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "parsed_receipt": execution_receipt or {},
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Parse post-human-submit local execution receipt")
    parser.add_argument("--verification-eligibility-json", required=True)
    parser.add_argument("--execution-receipt-json", required=True)
    parser.add_argument("--output-json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = parse_receipt(
        load_json(args.verification_eligibility_json),
        load_json(args.execution_receipt_json),
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
