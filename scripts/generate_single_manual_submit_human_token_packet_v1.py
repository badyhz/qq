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


def generate_token_packet(preflight: Optional[Dict[str, Any]], packet: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    blockers = []
    warnings = []

    if not isinstance(preflight, dict):
        blockers.append("PREFLIGHT_INVARIANT_REPORT_MISSING")
        preflight = {}
    if not isinstance(packet, dict):
        blockers.append("SINGLE_SUBMIT_PACKET_MISSING")
        packet = {}

    if str(preflight.get("verdict", "")) != "PASS":
        blockers.append("PREFLIGHT_NOT_PASS")
    if str(packet.get("verdict", "")) != "PASS":
        blockers.append("SINGLE_SUBMIT_PACKET_NOT_PASS")

    env = str(packet.get("env", ""))
    symbol = str(packet.get("symbol", ""))
    side = str(packet.get("side", ""))
    quantity = str(packet.get("quantity", ""))

    if not all([env, symbol, side, quantity]):
        blockers.append("TOKEN_SCOPE_FIELDS_MISSING")

    token_phrase_template = f"CONFIRM_TESTNET_SUBMIT:{env}:{symbol}:{side}:{quantity}:COUNT_1"

    if blockers:
        verdict = "FAIL"
        ok = False
    else:
        verdict = "PASS"
        ok = True

    return {
        "ok": ok,
        "verdict": verdict,
        "token_required": True,
        "token_scope": {
            "env": env,
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "max_submit_count": 1,
        },
        "token_phrase_template": token_phrase_template,
        "token_validation_rules": {
            "exact_match_required": True,
            "case_sensitive": True,
            "must_include_env_symbol_side_quantity_count": True,
            "max_submit_count": 1,
        },
        "submit_allowed": False,
        "max_submit_count": 1,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate single manual submit human token packet")
    parser.add_argument("--preflight-invariant-json", required=True)
    parser.add_argument("--single-submit-packet-json", required=True)
    parser.add_argument("--output-json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = generate_token_packet(
        load_json(args.preflight_invariant_json),
        load_json(args.single_submit_packet_json),
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
