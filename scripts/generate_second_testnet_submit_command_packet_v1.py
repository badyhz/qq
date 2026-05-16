#!/usr/bin/env python3
import argparse
import json
import os
import sys
from typing import Any, Dict, Optional


def load_json(path: str) -> Optional[Dict[str, Any]]:
    if not os.path.exists(path):
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


def _is_testnet_url(url: Any) -> bool:
    if not isinstance(url, str):
        return False
    lower = url.lower()
    if "api.binance.com" in lower:
        return False
    if "mainnet" in lower or "live" in lower:
        return False
    if "testnet" in lower or "demo" in lower:
        return True
    return False


def generate_command_packet(eligibility: Optional[Dict[str, Any]], candidate: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    blockers = []
    warnings = []

    if eligibility is None:
        blockers.append("ELIGIBILITY_INPUT_MALFORMED_OR_MISSING")
    if candidate is None:
        blockers.append("CANDIDATE_INPUT_MALFORMED_OR_MISSING")

    if not (eligibility and eligibility.get("verdict") == "PASS" and eligibility.get("eligible_for_second_submit") is True):
        blockers.append("ELIGIBILITY_NOT_PASS")

    if (eligibility or {}).get("max_submit_count") != 1:
        blockers.append("ELIGIBILITY_MAX_SUBMIT_COUNT_NOT_ONE")

    env = str((candidate or {}).get("env", "")).lower()
    symbol = (candidate or {}).get("symbol")
    side = (candidate or {}).get("side")
    quantity = (candidate or {}).get("quantity")
    base_url = (candidate or {}).get("base_url")

    if env != "testnet":
        blockers.append("CANDIDATE_ENV_NOT_TESTNET")
    if not symbol:
        blockers.append("CANDIDATE_SYMBOL_MISSING")
    if side not in ["BUY", "SELL"]:
        blockers.append("CANDIDATE_SIDE_INVALID")
    if quantity in [None, "", 0, 0.0, "0"]:
        blockers.append("CANDIDATE_QUANTITY_INVALID")
    if not _is_testnet_url(base_url):
        blockers.append("CANDIDATE_BASE_URL_NOT_TESTNET")

    dry_run_command = (
        "python3 scripts/run_testnet_submit_execution_wrapper_v1.py "
        "--inputs <command_packet.json> <token_gate.json> <payload.json> <invariants.json> <phase_report.json> "
        "--env testnet --output <second_submit_result.json> --json"
    )
    submit_template = (
        "python3 scripts/run_testnet_submit_execution_wrapper_v1.py "
        "--inputs <command_packet.json> <token_gate.json> <payload.json> <invariants.json> <phase_report.json> "
        "--allow-testnet-submit --confirm-token <TOKEN> --env testnet "
        "--output <second_submit_result.json> --json"
    )

    if blockers:
        verdict = "FAIL"
        ok = False
    else:
        verdict = "PASS"
        ok = True

    return {
        "ok": ok,
        "verdict": verdict,
        "env": env,
        "symbol": symbol,
        "side": side,
        "quantity": quantity,
        "command_preview": dry_run_command,
        "dry_run_command": dry_run_command,
        "submit_command_template": submit_template,
        "required_flags": ["--allow-testnet-submit", "--confirm-token", "--env testnet"],
        "required_confirmation_token_source": "MANUAL_CONFIRMATION_TOKEN_GATE",
        "blockers": sorted(set(blockers)),
        "warnings": warnings,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate second testnet submit command packet")
    parser.add_argument("--eligibility-json", required=True)
    parser.add_argument("--candidate-json", required=True)
    parser.add_argument("--output-json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = generate_command_packet(load_json(args.eligibility_json), load_json(args.candidate_json))

    if args.output_json:
        if not write_json(args.output_json, report):
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
