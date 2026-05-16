#!/usr/bin/env python3
import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

PHASE = "submit_risk_delta_review"


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


def _to_float(value: Any) -> Optional[float]:
    try:
        return float(value)
    except Exception:
        return None


def _mainnet_like(url: Any) -> bool:
    if not isinstance(url, str):
        return False
    lower = url.lower()
    if "api.binance.com" in lower:
        return True
    if "mainnet" in lower or "live" in lower:
        return True
    if "binance" in lower and "testnet" not in lower:
        return True
    return False


def _add_delta(
    machine: List[Dict[str, Any]],
    human: List[str],
    field: str,
    before: Any,
    after: Any,
    severity: str,
    reason: str,
) -> None:
    if before == after:
        return
    machine.append(
        {
            "field": field,
            "from": before,
            "to": after,
            "severity": severity,
            "reason": reason,
        }
    )
    human.append(f"{field}: {before} -> {after} ({severity})")


def compare_payloads(dry_run_payload: Optional[Dict[str, Any]], intended_submit_payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    blocking_reasons: List[str] = []
    warnings: List[str] = []
    machine_deltas: List[Dict[str, Any]] = []
    human_deltas: List[str] = []

    if dry_run_payload is None:
        blocking_reasons.append("DRY_RUN_PAYLOAD_LOAD_FAILED")
    if intended_submit_payload is None:
        blocking_reasons.append("INTENDED_SUBMIT_PAYLOAD_LOAD_FAILED")

    if blocking_reasons:
        return {
            "ok": False,
            "verdict": "FAIL",
            "phase": PHASE,
            "human_readable_deltas": human_deltas,
            "machine_readable_deltas": machine_deltas,
            "blocking_reasons": sorted(set(blocking_reasons)),
            "warnings": warnings,
            "safe_partial": False,
        }

    _add_delta(
        machine_deltas,
        human_deltas,
        "symbol",
        dry_run_payload.get("symbol"),
        intended_submit_payload.get("symbol"),
        "dangerous",
        "symbol_changed",
    )
    _add_delta(
        machine_deltas,
        human_deltas,
        "side",
        dry_run_payload.get("side"),
        intended_submit_payload.get("side"),
        "dangerous",
        "side_changed",
    )

    _add_delta(
        machine_deltas,
        human_deltas,
        "quantity",
        dry_run_payload.get("quantity"),
        intended_submit_payload.get("quantity"),
        "dangerous",
        "quantity_changed",
    )

    before_entry = dry_run_payload.get("entry_price") or dry_run_payload.get("reference_price")
    after_entry = intended_submit_payload.get("entry_price") or intended_submit_payload.get("reference_price")
    _add_delta(machine_deltas, human_deltas, "entry_reference", before_entry, after_entry, "non_blocking", "entry_reference_changed")

    _add_delta(
        machine_deltas,
        human_deltas,
        "stop_loss",
        dry_run_payload.get("stop_loss"),
        intended_submit_payload.get("stop_loss"),
        "non_blocking",
        "stop_loss_changed",
    )
    _add_delta(
        machine_deltas,
        human_deltas,
        "take_profit",
        dry_run_payload.get("take_profit"),
        intended_submit_payload.get("take_profit"),
        "non_blocking",
        "take_profit_changed",
    )

    _add_delta(
        machine_deltas,
        human_deltas,
        "leverage",
        dry_run_payload.get("leverage"),
        intended_submit_payload.get("leverage"),
        "dangerous",
        "leverage_changed",
    )
    _add_delta(
        machine_deltas,
        human_deltas,
        "margin_mode",
        dry_run_payload.get("margin_mode"),
        intended_submit_payload.get("margin_mode"),
        "dangerous",
        "margin_mode_changed",
    )

    _add_delta(
        machine_deltas,
        human_deltas,
        "env",
        dry_run_payload.get("env"),
        intended_submit_payload.get("env"),
        "dangerous",
        "env_changed",
    )
    _add_delta(
        machine_deltas,
        human_deltas,
        "base_url",
        dry_run_payload.get("base_url"),
        intended_submit_payload.get("base_url"),
        "dangerous",
        "base_url_changed",
    )

    dangerous = [d for d in machine_deltas if d["severity"] == "dangerous"]

    if _mainnet_like(intended_submit_payload.get("base_url")):
        blocking_reasons.append("INTENDED_SUBMIT_BASE_URL_MAINNET_LIKE")

    if dangerous:
        for item in dangerous:
            if item["field"] == "symbol":
                blocking_reasons.append("SYMBOL_CHANGED")
            if item["field"] == "side":
                blocking_reasons.append("SIDE_CHANGED")
            if item["field"] == "quantity":
                blocking_reasons.append("QUANTITY_CHANGED")
            if item["field"] == "env":
                blocking_reasons.append("ENV_CHANGED")
            if item["field"] == "base_url":
                blocking_reasons.append("BASE_URL_CHANGED")

    has_non_blocking = any(d["severity"] == "non_blocking" for d in machine_deltas)

    if blocking_reasons:
        verdict = "FAIL"
        ok = False
        safe_partial = False
    elif has_non_blocking:
        verdict = "PARTIAL"
        ok = True
        safe_partial = True
        warnings.append("NON_BLOCKING_DELTA_PRESENT")
    else:
        verdict = "PASS"
        ok = True
        safe_partial = False

    return {
        "ok": ok,
        "verdict": verdict,
        "phase": PHASE,
        "human_readable_deltas": human_deltas,
        "machine_readable_deltas": machine_deltas,
        "blocking_reasons": sorted(set(blocking_reasons)),
        "warnings": warnings,
        "safe_partial": safe_partial,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate submit risk delta report")
    parser.add_argument("--inputs", nargs=2, metavar=("DRY_RUN_PAYLOAD", "INTENDED_SUBMIT_PAYLOAD"), required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = compare_payloads(load_json(args.inputs[0]), load_json(args.inputs[1]))

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
