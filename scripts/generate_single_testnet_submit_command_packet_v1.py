#!/usr/bin/env python3
import argparse
import json
import os
import sys
from typing import Any, Dict, Optional

PHASE = "single_testnet_submit_command_packet"
FORBIDDEN_ACTIONS = [
    "REAL_SUBMIT",
    "MAINNET_SUBMIT",
    "CANCEL_ORDER",
    "FLATTEN_POSITION",
]


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
            json.dump(data, f, sort_keys=True, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def _is_testnet_url(url: Any) -> bool:
    if not isinstance(url, str):
        return True
    lower = url.lower()
    if "api.binance.com" in lower:
        return False
    if "mainnet" in lower or "live" in lower:
        return False
    if "binance" in lower and "testnet" not in lower and "demo" not in lower:
        return False
    return True


def generate_command_packet(phase_report: Optional[Dict[str, Any]], payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    blocking_reasons = []
    warnings = ["NO_COMMAND_EXECUTION_IN_THIS_SCRIPT"]

    if phase_report is None:
        blocking_reasons.append("PHASE_REPORT_LOAD_FAILED")
    if payload is None:
        blocking_reasons.append("PAYLOAD_LOAD_FAILED")

    phase_ok = bool(phase_report and phase_report.get("verdict") == "PASS")
    if not phase_ok:
        blocking_reasons.append("FINAL_PRE_SUBMIT_PHASE_NOT_PASS")

    env = str((payload or {}).get("env", "")).lower()
    if env != "testnet":
        blocking_reasons.append("PAYLOAD_ENV_NOT_TESTNET")

    base_url = (payload or {}).get("base_url")
    if not _is_testnet_url(base_url):
        blocking_reasons.append("PAYLOAD_BASE_URL_NOT_TESTNET")

    symbol = str((payload or {}).get("symbol", ""))
    side = str((payload or {}).get("side", ""))

    required_flags = ["--allow-testnet-submit", "--confirm-token", "--env testnet"]
    required_confirmation_token = "FROM_T497_CONFIRMATION_TOKEN"

    dry_run_cmd = (
        "python3 scripts/run_testnet_submit_execution_wrapper_v1.py "
        "--inputs <command_packet.json> <token_gate.json> <payload.json> <invariants.json> <phase_report.json> "
        "--env testnet --output <submit_result.json> --json"
    )
    submit_cmd = (
        "python3 scripts/run_testnet_submit_execution_wrapper_v1.py "
        "--inputs <command_packet.json> <token_gate.json> <payload.json> <invariants.json> <phase_report.json> "
        "--allow-testnet-submit --confirm-token <TOKEN> --env testnet "
        "--output <submit_result.json> --json"
    )

    if not blocking_reasons:
        verdict = "PASS"
        ok = True
    elif phase_ok:
        verdict = "PARTIAL"
        ok = False
    else:
        verdict = "FAIL"
        ok = False

    return {
        "ok": ok,
        "verdict": verdict,
        "phase": PHASE,
        "submit_mode_default": "dry_run",
        "command_templates": [
            {"name": "dry_run_first", "command": dry_run_cmd},
            {"name": "gated_testnet_submit", "command": submit_cmd},
        ],
        "required_flags": required_flags,
        "required_confirmation_token": required_confirmation_token,
        "payload_summary": {"symbol": symbol, "side": side, "env": env},
        "forbidden_actions": FORBIDDEN_ACTIONS,
        "warnings": warnings,
        "blocking_reasons": sorted(set(blocking_reasons)),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate single testnet submit command packet")
    parser.add_argument("--inputs", nargs=2, metavar=("PHASE_REPORT", "PAYLOAD"), required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = generate_command_packet(load_json(args.inputs[0]), load_json(args.inputs[1]))
    if not write_json(args.output, report):
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
