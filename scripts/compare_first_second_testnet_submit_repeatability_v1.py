#!/usr/bin/env python3
import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional


UNSAFE_TYPES = {"WRONG_ENV", "NAKED_POSITION", "ORPHAN_PROTECTION"}


def load_json(path: str) -> Optional[Dict[str, Any]]:
    if not path:
        return None
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


def compare_repeatability(
    first_evidence: Optional[Dict[str, Any]],
    second_evidence: Optional[Dict[str, Any]],
    first_incident: Optional[Dict[str, Any]] = None,
    second_incident: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    blockers: List[str] = []
    warnings: List[str] = []
    drift_items: List[Dict[str, Any]] = []

    if first_evidence is None:
        blockers.append("FIRST_EVIDENCE_MISSING")
    if second_evidence is None:
        blockers.append("SECOND_EVIDENCE_MISSING")

    if blockers:
        return {
            "ok": False,
            "verdict": "FAIL",
            "repeatability_status": "INCOMPLETE",
            "compared_fields": [],
            "drift_items": drift_items,
            "blockers": sorted(set(blockers)),
            "warnings": warnings,
            "recommendation": "COLLECT_MISSING_EVIDENCE",
        }

    compared_fields = [
        "env",
        "symbol",
        "side",
        "quantity",
        "protective_orders_detected",
        "stop_market_detected",
        "take_profit_market_detected",
        "naked_position_detected",
        "orphan_protection_detected",
    ]

    for field in compared_fields:
        before = first_evidence.get(field)
        after = second_evidence.get(field)
        if before != after:
            severity = "unsafe" if field in ["env", "naked_position_detected", "orphan_protection_detected"] else "warning"
            drift_items.append({"field": field, "first": before, "second": after, "severity": severity})

    first_verdict = str(first_evidence.get("verdict", ""))
    second_verdict = str(second_evidence.get("verdict", ""))

    env_consistent = str(first_evidence.get("env", "")).lower() == str(second_evidence.get("env", "")).lower() == "testnet"

    unsafe_found = False
    if not env_consistent:
        unsafe_found = True
        blockers.append("ENV_INCONSISTENT_OR_NOT_TESTNET")

    if bool(second_evidence.get("naked_position_detected") is True):
        unsafe_found = True
        blockers.append("SECOND_EVIDENCE_NAKED_POSITION")
    if bool(second_evidence.get("orphan_protection_detected") is True):
        unsafe_found = True
        blockers.append("SECOND_EVIDENCE_ORPHAN_PROTECTION")

    incident_high_or_critical = False
    for incident in [first_incident, second_incident]:
        level = str((incident or {}).get("incident_level", ""))
        if level in ["HIGH", "CRITICAL"]:
            incident_high_or_critical = True
            unsafe_found = True
            blockers.append("HIGH_OR_CRITICAL_INCIDENT_DETECTED")

    protective_consistent = (
        bool(first_evidence.get("protective_orders_detected") is True)
        and bool(second_evidence.get("protective_orders_detected") is True)
        and bool(first_evidence.get("stop_market_detected") is True)
        and bool(second_evidence.get("stop_market_detected") is True)
        and bool(first_evidence.get("take_profit_market_detected") is True)
        and bool(second_evidence.get("take_profit_market_detected") is True)
    )

    if unsafe_found:
        verdict = "FAIL"
        ok = False
        status = "UNSAFE"
        recommendation = "STOP_AND_MANUAL_REVIEW"
    elif first_verdict == "PASS" and second_verdict == "PASS" and env_consistent and protective_consistent and not drift_items:
        verdict = "PASS"
        ok = True
        status = "REPEATABLE"
        recommendation = "CONTINUE_MANUAL_GATED_FLOW"
    elif first_verdict == "PASS" and second_verdict in ["PASS", "PARTIAL"]:
        if second_verdict != "PASS" or not protective_consistent:
            verdict = "PARTIAL"
            ok = True
            status = "INCOMPLETE"
            recommendation = "COLLECT_MORE_EVIDENCE"
        else:
            verdict = "PARTIAL"
            ok = True
            status = "DRIFT_DETECTED"
            recommendation = "MANUAL_REVIEW_DRIFT"
            warnings.append("NON_UNSAFE_DRIFT_DETECTED")
    else:
        verdict = "PARTIAL"
        ok = True
        status = "INCOMPLETE"
        recommendation = "REVIEW_EVIDENCE_CHAIN"

    if any(item["field"] == "symbol" for item in drift_items):
        warnings.append("SYMBOL_DRIFT_DETECTED")

    return {
        "ok": ok,
        "verdict": verdict,
        "repeatability_status": status,
        "compared_fields": compared_fields,
        "drift_items": drift_items,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "recommendation": recommendation,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Compare first and second testnet submit repeatability")
    parser.add_argument("--first-evidence-json", required=True)
    parser.add_argument("--second-evidence-json", required=True)
    parser.add_argument("--first-incident-json")
    parser.add_argument("--second-incident-json")
    parser.add_argument("--output-json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = compare_repeatability(
        load_json(args.first_evidence_json),
        load_json(args.second_evidence_json),
        load_json(args.first_incident_json) if args.first_incident_json else None,
        load_json(args.second_incident_json) if args.second_incident_json else None,
    )

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
