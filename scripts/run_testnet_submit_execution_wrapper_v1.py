#!/usr/bin/env python3
import argparse
import json
import os
import sys
from typing import Any, Callable, Dict, Optional

SubmitFunc = Callable[[Dict[str, Any]], Dict[str, Any]]


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
        return False
    lower = url.lower()
    if "api.binance.com" in lower:
        return False
    if "mainnet" in lower or "live" in lower:
        return False
    if "testnet" in lower or "demo" in lower:
        return True
    return False


def default_submit_func(_: Dict[str, Any]) -> Dict[str, Any]:
    return {"transport": "stub", "status": "simulated_submit", "network_called": False}


def execute_wrapper(
    command_packet: Optional[Dict[str, Any]],
    token_gate: Optional[Dict[str, Any]],
    payload: Optional[Dict[str, Any]],
    invariant_report: Optional[Dict[str, Any]],
    phase_report: Optional[Dict[str, Any]],
    allow_testnet_submit: bool = False,
    confirm_token: Optional[str] = None,
    env: str = "testnet",
    submit_func: Optional[SubmitFunc] = None,
) -> Dict[str, Any]:
    blockers = []
    warnings = []
    submit_attempted = False
    submit_executed = False

    if command_packet is None:
        blockers.append("COMMAND_PACKET_LOAD_FAILED")
    if token_gate is None:
        blockers.append("TOKEN_GATE_LOAD_FAILED")
    if payload is None:
        blockers.append("PAYLOAD_LOAD_FAILED")
    if invariant_report is None:
        blockers.append("INVARIANT_REPORT_LOAD_FAILED")
    if phase_report is None:
        blockers.append("PHASE_REPORT_LOAD_FAILED")

    request_plan = {
        "symbol": (payload or {}).get("symbol"),
        "side": (payload or {}).get("side"),
        "quantity": (payload or {}).get("quantity"),
        "order_type": (payload or {}).get("order_type"),
        "env": env,
        "base_url": (payload or {}).get("base_url"),
        "mode": "dry_run" if not allow_testnet_submit else "submit_requested",
    }

    if not allow_testnet_submit:
        warnings.append("DEFAULT_DRY_RUN_MODE")
        return {
            "ok": True,
            "verdict": "DRY_RUN",
            "submit_attempted": False,
            "submit_executed": False,
            "request_plan": request_plan,
            "blocking_reasons": blockers,
            "warnings": warnings,
        }

    submit_attempted = True

    expected_token = str((token_gate or {}).get("confirmation_token", ""))
    if not expected_token:
        blockers.append("EXPECTED_CONFIRM_TOKEN_MISSING")
    if confirm_token != expected_token:
        blockers.append("CONFIRM_TOKEN_MISMATCH")

    if env.lower() != "testnet":
        blockers.append("ENV_NOT_TESTNET")

    payload_env = str((payload or {}).get("env", "")).lower()
    if payload_env != "testnet":
        blockers.append("PAYLOAD_ENV_NOT_TESTNET")

    base_url = (payload or {}).get("base_url")
    if not _is_testnet_url(base_url):
        blockers.append("BASE_URL_NOT_TESTNET")

    if str((invariant_report or {}).get("verdict", "")) != "PASS":
        blockers.append("INVARIANT_REPORT_NOT_PASS")

    if str((phase_report or {}).get("verdict", "")) != "PASS":
        blockers.append("PHASE_REPORT_NOT_PASS")

    if blockers:
        return {
            "ok": False,
            "verdict": "BLOCKED",
            "submit_attempted": submit_attempted,
            "submit_executed": False,
            "request_plan": request_plan,
            "blocking_reasons": sorted(set(blockers)),
            "warnings": warnings,
        }

    try:
        fn = submit_func or default_submit_func
        submit_result = fn(payload or {})
        submit_executed = True
        return {
            "ok": True,
            "verdict": "SUBMITTED",
            "submit_attempted": submit_attempted,
            "submit_executed": submit_executed,
            "request_plan": request_plan,
            "submit_result": submit_result,
            "blocking_reasons": [],
            "warnings": warnings,
        }
    except Exception as exc:  # pragma: no cover
        return {
            "ok": False,
            "verdict": "FAIL",
            "submit_attempted": submit_attempted,
            "submit_executed": False,
            "request_plan": request_plan,
            "blocking_reasons": [f"SUBMIT_EXECUTION_ERROR:{exc.__class__.__name__}"],
            "warnings": warnings,
        }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Run testnet submit execution wrapper")
    parser.add_argument("--inputs", nargs=5, metavar=("COMMAND_PACKET", "TOKEN_GATE", "PAYLOAD", "INVARIANT_REPORT", "PHASE_REPORT"), required=True)
    parser.add_argument("--allow-testnet-submit", action="store_true")
    parser.add_argument("--confirm-token")
    parser.add_argument("--env", default="testnet")
    parser.add_argument("--output", required=True)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = execute_wrapper(
        load_json(args.inputs[0]),
        load_json(args.inputs[1]),
        load_json(args.inputs[2]),
        load_json(args.inputs[3]),
        load_json(args.inputs[4]),
        allow_testnet_submit=args.allow_testnet_submit,
        confirm_token=args.confirm_token,
        env=args.env,
    )

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
