#!/usr/bin/env python3
import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional

PHASE = "verify_testnet_submit_payload_invariants"
ALLOWED_ORDER_TYPES = {"MARKET", "LIMIT", "STOP_MARKET", "TAKE_PROFIT_MARKET"}


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


def _check_base_url(url: str) -> bool:
    lower = url.lower()
    if not lower:
        return True
    if "api.binance.com" in lower:
        return False
    if "mainnet" in lower or "live" in lower:
        return False
    if "binance" in lower and "testnet" not in lower:
        return False
    return True


def _to_float(value: Any) -> Optional[float]:
    try:
        return float(value)
    except Exception:
        return None


def verify_invariants(payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    blockers: List[str] = []
    warnings: List[str] = []

    if payload is None:
        blockers.append("PAYLOAD_LOAD_FAILED")
        result = {
            "ok": False,
            "verdict": "FAIL",
            "phase": PHASE,
            "invariant_checks": checks,
            "blocking_reasons": blockers,
            "warnings": warnings,
        }
        return result

    env = str(payload.get("env", "")).lower()
    env_ok = env == "testnet"
    checks.append({"name": "env_is_testnet", "pass": env_ok, "value": env})
    if not env_ok:
        blockers.append("ENV_NOT_TESTNET")

    dry_run_ref = payload.get("dry_run_artifact") or payload.get("dry_run_artifact_path") or payload.get("dry_run_linked")
    dry_run_ok = bool(dry_run_ref)
    checks.append({"name": "dry_run_artifact_linked", "pass": dry_run_ok})
    if not dry_run_ok:
        blockers.append("DRY_RUN_ARTIFACT_MISSING")

    symbol = str(payload.get("symbol", ""))
    symbol_ok = bool(symbol)
    checks.append({"name": "symbol_exists", "pass": symbol_ok, "value": symbol})
    if not symbol_ok:
        blockers.append("SYMBOL_MISSING")

    side = str(payload.get("side", ""))
    side_ok = side in {"BUY", "SELL"}
    checks.append({"name": "side_valid", "pass": side_ok, "value": side})
    if not side_ok:
        blockers.append("SIDE_INVALID")

    qty = _to_float(payload.get("quantity"))
    qty_ok = qty is not None and qty > 0
    checks.append({"name": "quantity_positive", "pass": qty_ok, "value": payload.get("quantity")})
    if not qty_ok:
        blockers.append("QUANTITY_INVALID")

    order_type = str(payload.get("order_type", ""))
    order_type_ok = order_type in ALLOWED_ORDER_TYPES
    checks.append({"name": "order_type_allowed", "pass": order_type_ok, "value": order_type})
    if not order_type_ok:
        blockers.append("ORDER_TYPE_INVALID")

    reduce_only = bool(payload.get("reduceOnly", False))
    intent = str(payload.get("intent", "ENTRY")).upper()
    reduce_only_ok = not (intent == "ENTRY" and order_type == "MARKET" and reduce_only)
    checks.append({"name": "reduce_only_entry_market_rule", "pass": reduce_only_ok, "value": reduce_only})
    if not reduce_only_ok:
        blockers.append("REDUCE_ONLY_NOT_ALLOWED_FOR_ENTRY_MARKET")

    expect_protective = bool(payload.get("expect_protective_orders", False))
    protective_orders = payload.get("protective_orders")
    stop_loss = payload.get("stop_loss")
    take_profit = payload.get("take_profit")
    protective_present = bool(protective_orders or stop_loss or take_profit)
    protective_ok = (not expect_protective) or protective_present
    checks.append({"name": "protective_config_present_if_expected", "pass": protective_ok})
    if not protective_ok:
        blockers.append("PROTECTIVE_CONFIG_MISSING")
    if protective_present and not expect_protective:
        warnings.append("PROTECTIVE_CONFIG_PRESENT_WITHOUT_EXPECTATION")

    trigger_ok = True
    if isinstance(stop_loss, dict):
        sl_type = stop_loss.get("type")
        sl_price = _to_float(stop_loss.get("stopPrice"))
        if sl_type == "STOP_MARKET" and (sl_price is None or sl_price <= 0):
            trigger_ok = False
        direction = stop_loss.get("trigger_direction")
        if direction is not None:
            if side == "BUY" and direction != "BELOW":
                trigger_ok = False
            if side == "SELL" and direction != "ABOVE":
                trigger_ok = False

    if isinstance(take_profit, dict):
        tp_type = take_profit.get("type")
        tp_price = _to_float(take_profit.get("stopPrice"))
        if tp_type == "TAKE_PROFIT_MARKET" and (tp_price is None or tp_price <= 0):
            trigger_ok = False
        direction = take_profit.get("trigger_direction")
        if direction is not None:
            if side == "BUY" and direction != "ABOVE":
                trigger_ok = False
            if side == "SELL" and direction != "BELOW":
                trigger_ok = False

    checks.append({"name": "protective_trigger_direction_sanity", "pass": trigger_ok})
    if not trigger_ok:
        blockers.append("PROTECTIVE_TRIGGER_DIRECTION_INVALID")

    base_url = str(payload.get("base_url", ""))
    endpoint = str(payload.get("endpoint", ""))
    base_url_ok = _check_base_url(base_url)
    endpoint_ok = _check_base_url(endpoint)
    checks.append({"name": "no_live_base_url", "pass": base_url_ok, "value": base_url})
    checks.append({"name": "no_mainnet_endpoint", "pass": endpoint_ok, "value": endpoint})
    if not base_url_ok:
        blockers.append("LIVE_BASE_URL_DETECTED")
    if not endpoint_ok:
        blockers.append("MAINNET_ENDPOINT_DETECTED")

    if not blockers and not warnings:
        verdict = "PASS"
        ok = True
    elif not blockers:
        verdict = "PARTIAL"
        ok = True
    else:
        verdict = "FAIL"
        ok = False

    return {
        "ok": ok,
        "verdict": verdict,
        "phase": PHASE,
        "invariant_checks": checks,
        "blocking_reasons": sorted(set(blockers)),
        "warnings": warnings,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Verify testnet submit payload invariants offline")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = verify_invariants(load_json(args.input))
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
