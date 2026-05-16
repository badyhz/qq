#!/usr/bin/env python3
import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional


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


def compare_consistency(
    first_evidence: Optional[Dict[str, Any]],
    second_evidence: Optional[Dict[str, Any]],
    third_evidence: Optional[Dict[str, Any]],
    first_incident: Optional[Dict[str, Any]] = None,
    second_incident: Optional[Dict[str, Any]] = None,
    third_incident: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    blockers: List[str] = []
    warnings: List[str] = []
    drift_items: List[Dict[str, Any]] = []

    evidences = [first_evidence, second_evidence, third_evidence]
    names = ["first", "second", "third"]

    for name, ev in zip(names, evidences):
        if ev is None:
            blockers.append(f"{name.upper()}_EVIDENCE_MISSING")

    if blockers:
        return {
            "ok": False,
            "verdict": "FAIL",
            "consistency_status": "UNSAFE",
            "compared_fields": [],
            "drift_items": drift_items,
            "blockers": sorted(set(blockers)),
            "warnings": warnings,
            "recommendation": "STOP_AND_REBUILD_EVIDENCE_CHAIN",
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

    base = first_evidence
    for idx, ev in enumerate([second_evidence, third_evidence], start=2):
        for field in compared_fields:
            if base.get(field) != ev.get(field):
                severity = "unsafe" if field in ["env", "naked_position_detected", "orphan_protection_detected"] else "warning"
                drift_items.append(
                    {
                        "field": field,
                        "first": base.get(field),
                        "other": ev.get(field),
                        "other_label": "second" if idx == 2 else "third",
                        "severity": severity,
                    }
                )

    unsafe = False
    for ev in evidences:
        if str(ev.get("env", "")).lower() != "testnet":
            blockers.append("WRONG_ENV_DETECTED")
            unsafe = True
        if bool(ev.get("naked_position_detected") is True):
            blockers.append("NAKED_POSITION_DETECTED")
            unsafe = True
        if bool(ev.get("orphan_protection_detected") is True):
            blockers.append("ORPHAN_PROTECTION_DETECTED")
            unsafe = True

    incidents = [first_incident, second_incident, third_incident]
    for incident in incidents:
        level = str((incident or {}).get("incident_level", ""))
        if level in ["HIGH", "CRITICAL"]:
            blockers.append("HIGH_OR_CRITICAL_INCIDENT_DETECTED")
            unsafe = True

    verdicts = [str(ev.get("verdict", "")) for ev in evidences]
    all_pass = all(v == "PASS" for v in verdicts)
    any_partial = any(v == "PARTIAL" for v in verdicts)

    protective_consistent = all(bool(ev.get("protective_orders_detected") is True) for ev in evidences)
    stop_consistent = all(bool(ev.get("stop_market_detected") is True) for ev in evidences)
    tp_consistent = all(bool(ev.get("take_profit_market_detected") is True) for ev in evidences)

    if unsafe:
        verdict = "FAIL"
        ok = False
        status = "UNSAFE"
        recommendation = "STOP_AND_MANUAL_REVIEW"
    elif all_pass and protective_consistent and stop_consistent and tp_consistent and not drift_items:
        verdict = "PASS"
        ok = True
        status = "CONSISTENT"
        recommendation = "CONTINUE_MANUAL_GATED_SUBMIT_FLOW"
    elif any_partial and not unsafe:
        verdict = "PARTIAL"
        ok = True
        status = "INCOMPLETE"
        recommendation = "COLLECT_MISSING_EVIDENCE"
    else:
        verdict = "PARTIAL"
        ok = True
        status = "DRIFT_DETECTED"
        recommendation = "MANUAL_REVIEW_DRIFT_BEFORE_NEXT_STEP"

    if any(item.get("field") in ["symbol", "side"] for item in drift_items):
        warnings.append("SYMBOL_OR_SIDE_DRIFT_DETECTED")

    return {
        "ok": ok,
        "verdict": verdict,
        "consistency_status": status,
        "compared_fields": compared_fields,
        "drift_items": drift_items,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "recommendation": recommendation,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Compare three testnet submit consistency")
    parser.add_argument("--first-evidence-json", required=True)
    parser.add_argument("--second-evidence-json", required=True)
    parser.add_argument("--third-evidence-json", required=True)
    parser.add_argument("--first-incident-json")
    parser.add_argument("--second-incident-json")
    parser.add_argument("--third-incident-json")
    parser.add_argument("--output-json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = compare_consistency(
        load_json(args.first_evidence_json),
        load_json(args.second_evidence_json),
        load_json(args.third_evidence_json),
        load_json(args.first_incident_json) if args.first_incident_json else None,
        load_json(args.second_incident_json) if args.second_incident_json else None,
        load_json(args.third_incident_json) if args.third_incident_json else None,
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
