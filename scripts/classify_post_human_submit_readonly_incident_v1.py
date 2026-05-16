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


def classify_incident(
    readonly_evidence: Optional[Dict[str, Any]],
    verification_phase: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    blockers = []
    warnings = []
    incident_types = []

    if not isinstance(readonly_evidence, dict):
        blockers.append("READONLY_EVIDENCE_MISSING")
    if not isinstance(verification_phase, dict):
        blockers.append("VERIFICATION_PHASE_MISSING")

    incident_level = "NONE"

    if not blockers:
        env = str((readonly_evidence or {}).get("env", "")).strip().lower()
        if env != "testnet":
            incident_types.append("WRONG_ENV")
            incident_level = "CRITICAL"

        if _has_unsafe_marker(readonly_evidence or {}):
            incident_types.append("MAINNET_OR_LIVE_MARKER")
            incident_level = "CRITICAL"
        if _has_unsafe_marker(verification_phase or {}):
            incident_types.append("MAINNET_OR_LIVE_MARKER")
            incident_level = "CRITICAL"

        submit_executed = bool((readonly_evidence or {}).get("submit_executed", False))
        if not submit_executed and env == "testnet":
            incident_types.append("SUBMIT_NOT_EXECUTED")
            incident_level = "MEDIUM"

        position_detected = bool((readonly_evidence or {}).get("position_detected", False))
        if submit_executed and not position_detected and env == "testnet":
            incident_types.append("POSITION_NOT_DETECTED")
            if incident_level not in ("HIGH", "CRITICAL"):
                incident_level = "MEDIUM"

        protective_orders_detected = bool((readonly_evidence or {}).get("protective_orders_detected", False))
        stop_market_detected = bool((readonly_evidence or {}).get("stop_market_detected", False))
        take_profit_market_detected = bool((readonly_evidence or {}).get("take_profit_market_detected", False))

        if not protective_orders_detected and submit_executed:
            incident_types.append("MISSING_PROTECTIVE_ORDERS")
            if incident_level not in ("CRITICAL"):
                incident_level = "HIGH"

        if not stop_market_detected and submit_executed:
            incident_types.append("MISSING_STOP_MARKET")
            if incident_level not in ("CRITICAL"):
                incident_level = "HIGH"

        if not take_profit_market_detected and submit_executed:
            incident_types.append("MISSING_TAKE_PROFIT_MARKET")
            if incident_level not in ("CRITICAL"):
                incident_level = "HIGH"

        naked_position_detected = bool((readonly_evidence or {}).get("naked_position_detected", False))
        orphan_protection_detected = bool((readonly_evidence or {}).get("orphan_protection_detected", False))

        if naked_position_detected:
            incident_types.append("NAKED_POSITION")
            incident_level = "CRITICAL"
        if orphan_protection_detected:
            incident_types.append("ORPHAN_PROTECTION")
            incident_level = "CRITICAL"

        if not incident_types and incident_level == "NONE":
            ok = True
            verdict = "PASS"
        elif incident_level in ("LOW", "MEDIUM"):
            ok = False
            verdict = "PARTIAL"
        else:
            ok = False
            verdict = "FAIL"
    else:
        incident_types.append("UNKNOWN_STATE")
        incident_level = "CRITICAL"
        ok = False
        verdict = "FAIL"

    return {
        "ok": ok,
        "verdict": verdict,
        "incident_level": incident_level,
        "incident_types": incident_types,
        "readonly": True,
        "submit_allowed": False,
        "cancel_allowed": False,
        "flatten_allowed": False,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "evidence_refs": {
            "readonly_evidence": readonly_evidence or {},
            "verification_phase": verification_phase or {},
        },
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Classify post-human-submit readonly incident")
    parser.add_argument("--readonly-evidence-json", required=True)
    parser.add_argument("--verification-phase-json", required=True)
    parser.add_argument("--output-json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = classify_incident(
        load_json(args.readonly_evidence_json),
        load_json(args.verification_phase_json),
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
