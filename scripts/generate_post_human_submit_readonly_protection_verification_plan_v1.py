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


def _has_unsafe_marker(text: Any) -> bool:
    if not isinstance(text, str):
        return False
    lower = text.lower()
    return "mainnet" in lower or "live" in lower or "api.binance.com" in lower


def generate_plan(
    receipt_parser: Optional[Dict[str, Any]],
    single_submit_packet: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    blockers = []
    warnings = []

    if not isinstance(receipt_parser, dict):
        blockers.append("RECEIPT_PARSER_MISSING")

    if str((receipt_parser or {}).get("verdict", "")) == "FAIL":
        blockers.append("RECEIPT_PARSER_FAILED")

    if _has_unsafe_marker(str(receipt_parser)):
        blockers.append("RECEIPT_PARSER_HAS_UNSAFE_MARKER")

    env = str((receipt_parser or {}).get("env", "")).strip()
    symbol = str((receipt_parser or {}).get("symbol", "")).strip()
    side = str((receipt_parser or {}).get("side", "")).strip()
    quantity = str((receipt_parser or {}).get("quantity", "")).strip()

    if blockers:
        verdict = "FAIL"
        ok = False
    elif str((receipt_parser or {}).get("verdict", "")) == "PARTIAL":
        verdict = "PARTIAL"
        ok = False
    else:
        verdict = "PASS"
        ok = True

    return {
        "ok": ok,
        "verdict": verdict,
        "plan_type": "POST_HUMAN_SUBMIT_PROTECTION_READONLY_CHECK",
        "readonly": True,
        "env": env,
        "symbol": symbol,
        "side": side,
        "quantity": quantity,
        "submit_allowed": False,
        "cancel_allowed": False,
        "flatten_allowed": False,
        "readonly_checks": [
            "CHECK_POSITION_RISK",
            "CHECK_OPEN_ALGO_ORDERS",
            "VERIFY_STOP_MARKET_EXISTS",
            "VERIFY_TAKE_PROFIT_MARKET_EXISTS",
            "VERIFY_REDUCE_ONLY_PROTECTION",
            "VERIFY_NO_ORPHAN_PROTECTION",
            "VERIFY_NO_NAKED_POSITION",
        ],
        "forbidden_actions": [
            "SUBMIT",
            "CANCEL",
            "FLATTEN",
            "LIVE",
            "MAINNET",
            "REPEAT_SUBMIT",
        ],
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate post-human-submit readonly protection verification plan")
    parser.add_argument("--receipt-parser-json", required=True)
    parser.add_argument("--single-submit-packet-json")
    parser.add_argument("--output-json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = generate_plan(
        load_json(args.receipt_parser_json),
        load_json(args.single_submit_packet_json) if args.single_submit_packet_json else None,
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
