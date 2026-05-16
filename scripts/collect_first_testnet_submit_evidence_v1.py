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


def _get_bool(report: Dict[str, Any], *paths: str) -> Optional[bool]:
    for path in paths:
        cur: Any = report
        ok = True
        for key in path.split("."):
            if isinstance(cur, dict) and key in cur:
                cur = cur[key]
            else:
                ok = False
                break
        if ok and isinstance(cur, bool):
            return cur
    return None


def _get_any(report: Dict[str, Any], *paths: str) -> Any:
    for path in paths:
        cur: Any = report
        ok = True
        for key in path.split("."):
            if isinstance(cur, dict) and key in cur:
                cur = cur[key]
            else:
                ok = False
                break
        if ok:
            return cur
    return None


def collect_evidence(submit_result: Optional[Dict[str, Any]], post_submit_verification: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    blockers = []
    warnings = []

    if submit_result is None:
        blockers.append("SUBMIT_RESULT_MALFORMED_OR_MISSING")
    if post_submit_verification is None:
        blockers.append("POST_SUBMIT_VERIFICATION_MALFORMED_OR_MISSING")

    if blockers:
        return {
            "ok": False,
            "verdict": "FAIL",
            "submit_attempted": False,
            "submit_executed": False,
            "submit_order_id_present": False,
            "env": None,
            "symbol": None,
            "side": None,
            "quantity": None,
            "position_detected": False,
            "protective_orders_detected": False,
            "stop_market_detected": False,
            "take_profit_market_detected": False,
            "orphan_protection_detected": False,
            "naked_position_detected": False,
            "evidence_items": [],
            "blockers": sorted(set(blockers)),
            "warnings": warnings,
            "next_actions": ["FIX_INPUT_ARTIFACTS"],
        }

    submit_attempted = bool(submit_result.get("submit_attempted") is True)
    submit_executed = bool(submit_result.get("submit_executed") is True)

    env = _get_any(submit_result, "request_plan.env", "env")
    symbol = _get_any(submit_result, "request_plan.symbol", "symbol")
    side = _get_any(submit_result, "request_plan.side", "side")
    quantity = _get_any(submit_result, "request_plan.quantity", "quantity")

    submit_order_id_present = bool(
        _get_any(submit_result, "submit_result.orderId", "submit_result.order_id", "submit_order_id", "order_id")
    )

    position_detected_val = _get_bool(post_submit_verification, "readonly_checks.has_position_snapshot", "position_detected")
    protective_detected_val = _get_bool(
        post_submit_verification,
        "readonly_checks.has_protection_snapshot",
        "protective_orders_detected",
        "protection_status.present",
    )
    stop_market_val = _get_bool(post_submit_verification, "readonly_checks.stop_market_detected", "stop_market_detected")
    tp_market_val = _get_bool(post_submit_verification, "readonly_checks.take_profit_market_detected", "take_profit_market_detected")
    orphan_val = _get_bool(post_submit_verification, "orphan_protection_detected")
    naked_val = _get_bool(post_submit_verification, "naked_position_detected")

    position_detected = bool(position_detected_val is True)
    protective_orders_detected = bool(protective_detected_val is True)
    stop_market_detected = bool(stop_market_val is True)
    take_profit_market_detected = bool(tp_market_val is True)
    orphan_protection_detected = bool(orphan_val is True)
    naked_position_detected = bool(naked_val is True)

    if env is None:
        warnings.append("ENV_MISSING")
    if symbol is None:
        warnings.append("SYMBOL_MISSING")
    if side is None:
        warnings.append("SIDE_MISSING")
    if quantity is None:
        warnings.append("QUANTITY_MISSING")
    if stop_market_val is None:
        warnings.append("STOP_MARKET_EVIDENCE_MISSING")
    if tp_market_val is None:
        warnings.append("TAKE_PROFIT_MARKET_EVIDENCE_MISSING")
    if orphan_val is None:
        warnings.append("ORPHAN_PROTECTION_EVIDENCE_AMBIGUOUS")
    if naked_val is None:
        warnings.append("NAKED_POSITION_EVIDENCE_AMBIGUOUS")

    if str(env).lower() != "testnet":
        blockers.append("WRONG_ENV")
    if not submit_executed:
        blockers.append("SUBMIT_NOT_EXECUTED")
    if not submit_order_id_present:
        blockers.append("SUBMIT_ORDER_ID_MISSING")
    if naked_position_detected:
        blockers.append("NAKED_POSITION_DETECTED")
    if orphan_protection_detected:
        blockers.append("ORPHAN_PROTECTION_DETECTED")

    pass_requirements = [
        str(env).lower() == "testnet",
        submit_executed,
        submit_order_id_present,
        position_detected,
        protective_orders_detected,
        stop_market_detected,
        take_profit_market_detected,
        orphan_protection_detected is False,
        naked_position_detected is False,
    ]

    if all(pass_requirements):
        verdict = "PASS"
        ok = True
    elif blockers:
        verdict = "FAIL"
        ok = False
    else:
        verdict = "PARTIAL"
        ok = True

    evidence_items = [
        {"name": "submit_executed", "value": submit_executed},
        {"name": "submit_order_id_present", "value": submit_order_id_present},
        {"name": "env", "value": env},
        {"name": "position_detected", "value": position_detected_val},
        {"name": "protective_orders_detected", "value": protective_detected_val},
        {"name": "stop_market_detected", "value": stop_market_val},
        {"name": "take_profit_market_detected", "value": tp_market_val},
        {"name": "orphan_protection_detected", "value": orphan_val},
        {"name": "naked_position_detected", "value": naked_val},
    ]

    if verdict == "PASS":
        next_actions = ["CONTINUE_READONLY_MONITORING"]
    elif verdict == "PARTIAL":
        next_actions = ["COLLECT_MISSING_EVIDENCE", "MANUAL_REVIEW"]
    else:
        next_actions = ["MANUAL_REVIEW_REQUIRED", "GENERATE_ROLLBACK_RECOMMENDATION"]

    return {
        "ok": ok,
        "verdict": verdict,
        "submit_attempted": submit_attempted,
        "submit_executed": submit_executed,
        "submit_order_id_present": submit_order_id_present,
        "env": env,
        "symbol": symbol,
        "side": side,
        "quantity": quantity,
        "position_detected": position_detected,
        "protective_orders_detected": protective_orders_detected,
        "stop_market_detected": stop_market_detected,
        "take_profit_market_detected": take_profit_market_detected,
        "orphan_protection_detected": orphan_protection_detected,
        "naked_position_detected": naked_position_detected,
        "evidence_items": evidence_items,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "next_actions": next_actions,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Collect first testnet submit evidence")
    parser.add_argument("--submit-result-json", required=True)
    parser.add_argument("--post-submit-verification-json", required=True)
    parser.add_argument("--output-json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = collect_evidence(load_json(args.submit_result_json), load_json(args.post_submit_verification_json))

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
