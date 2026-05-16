#!/usr/bin/env python3
import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional

INCIDENT_LEVELS = ["NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"]


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


def classify_incident(evidence: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    blockers: List[str] = []
    warnings: List[str] = []
    incident_types: List[str] = []

    if evidence is None:
        return {
            "ok": False,
            "verdict": "FAIL",
            "incident_level": "MEDIUM",
            "incident_types": ["UNKNOWN_STATE"],
            "required_action": "MANUAL_REVIEW",
            "blockers": ["EVIDENCE_MALFORMED_OR_MISSING"],
            "warnings": [],
            "evidence_refs": {},
        }

    env = str(evidence.get("env", "")).lower()
    submit_executed = bool(evidence.get("submit_executed") is True)
    position_detected = bool(evidence.get("position_detected") is True)
    stop_detected = bool(evidence.get("stop_market_detected") is True)
    tp_detected = bool(evidence.get("take_profit_market_detected") is True)
    naked = bool(evidence.get("naked_position_detected") is True)
    orphan = bool(evidence.get("orphan_protection_detected") is True)

    symbol = evidence.get("symbol")
    side = evidence.get("side")

    if env != "testnet":
        incident_types.append("WRONG_ENV")
    if not submit_executed:
        incident_types.append("SUBMIT_NOT_EXECUTED")
    if submit_executed and not position_detected:
        incident_types.append("NO_POSITION_AFTER_SUBMIT")
    if submit_executed and not stop_detected:
        incident_types.append("MISSING_STOP_MARKET")
    if submit_executed and not tp_detected:
        incident_types.append("MISSING_TAKE_PROFIT_MARKET")
    if naked:
        incident_types.append("NAKED_POSITION")
    if orphan:
        incident_types.append("ORPHAN_PROTECTION")
    if evidence.get("quantity") in [None, "", "0", 0, 0.0]:
        incident_types.append("SIZE_MISMATCH")
    if not symbol:
        incident_types.append("SYMBOL_MISMATCH")
    if side not in ["BUY", "SELL"]:
        incident_types.append("SIDE_MISMATCH")

    text = json.dumps(evidence, sort_keys=True, ensure_ascii=False).lower()
    if "mainnet" in text or "api.binance.com" in text or "live" in text:
        incident_types.append("WRONG_ENV")

    if evidence.get("verdict") not in ["PASS", "PARTIAL", "FAIL"]:
        incident_types.append("UNKNOWN_STATE")

    if not incident_types and evidence.get("warnings"):
        incident_level = "LOW"
        warnings.append("NON_BLOCKING_WARNINGS_PRESENT")
    elif any(x in incident_types for x in ["WRONG_ENV", "NAKED_POSITION"]):
        incident_level = "CRITICAL"
    elif any(x in incident_types for x in ["MISSING_STOP_MARKET", "MISSING_TAKE_PROFIT_MARKET"]):
        incident_level = "HIGH"
    elif any(x in incident_types for x in ["NO_POSITION_AFTER_SUBMIT", "UNKNOWN_STATE"]):
        incident_level = "MEDIUM"
    elif incident_types:
        incident_level = "LOW"
    else:
        incident_level = "NONE"

    if incident_level == "NONE":
        verdict = "PASS"
        ok = True
        required_action = "NONE"
    elif incident_level == "LOW":
        verdict = "PARTIAL"
        ok = False
        required_action = "MONITOR"
    elif incident_level == "MEDIUM":
        verdict = "PARTIAL"
        ok = False
        required_action = "MANUAL_REVIEW"
    elif incident_level == "HIGH":
        verdict = "FAIL"
        ok = False
        required_action = "SAFE_FLATTEN_DRY_RUN"
    else:
        verdict = "FAIL"
        ok = False
        required_action = "SAFE_FLATTEN_CONFIRM_REQUIRED"

    if incident_level in ["CRITICAL", "HIGH"]:
        blockers.append("SAFETY_INCIDENT_DETECTED")

    return {
        "ok": ok,
        "verdict": verdict,
        "incident_level": incident_level,
        "incident_types": sorted(set(incident_types)),
        "required_action": required_action,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "evidence_refs": {
            "env": evidence.get("env"),
            "symbol": evidence.get("symbol"),
            "side": evidence.get("side"),
            "submit_executed": evidence.get("submit_executed"),
        },
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Classify first testnet submit safety incident")
    parser.add_argument("--evidence-json", required=True)
    parser.add_argument("--output-json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = classify_incident(load_json(args.evidence_json))

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
