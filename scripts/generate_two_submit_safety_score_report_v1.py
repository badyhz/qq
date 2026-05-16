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


def generate_safety_score(
    first_final: Optional[Dict[str, Any]],
    second_evidence: Optional[Dict[str, Any]],
    second_incident: Optional[Dict[str, Any]],
    repeatability: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    blockers = []
    warnings = []

    if first_final is None:
        blockers.append("FIRST_FINAL_REPORT_MISSING")
    if second_evidence is None:
        blockers.append("SECOND_EVIDENCE_MISSING")
    if second_incident is None:
        blockers.append("SECOND_INCIDENT_MISSING")
    if repeatability is None:
        blockers.append("REPEATABILITY_REPORT_MISSING")

    if blockers:
        return {
            "ok": False,
            "verdict": "FAIL",
            "safety_score": 0,
            "score_components": {},
            "blockers": sorted(set(blockers)),
            "warnings": warnings,
            "decision": "STOP",
        }

    score = 100
    score_components = {
        "base": 100,
        "critical_override": 0,
        "high_cap": 40,
        "partial_evidence_penalty": 0,
        "repeatability_drift_penalty": 0,
        "missing_audit_linkage_penalty": 0,
    }

    incident_level = str(second_incident.get("incident_level", ""))
    if incident_level == "CRITICAL":
        score = 0
        blockers.append("CRITICAL_INCIDENT")
    elif incident_level == "HIGH":
        score = min(score, 40)
        blockers.append("HIGH_INCIDENT")

    if str(second_evidence.get("verdict", "")) != "PASS":
        score -= 25
        score_components["partial_evidence_penalty"] = 25

    repeatability_status = str(repeatability.get("repeatability_status", ""))
    if repeatability_status == "DRIFT_DETECTED":
        score -= 20
        score_components["repeatability_drift_penalty"] = 20

    audit_required = bool(first_final.get("audit_linkage_required") is True)
    audit_ok = bool(first_final.get("audit_linkage_ok") is True)
    if audit_required and not audit_ok:
        score -= 10
        score_components["missing_audit_linkage_penalty"] = 10
        warnings.append("MISSING_AUDIT_LINKAGE")

    if score < 0:
        score = 0

    if score < 60:
        blockers.append("SAFETY_SCORE_BELOW_60")

    if blockers:
        verdict = "FAIL"
        ok = False
        decision = "STOP"
    elif score >= 85 and not warnings:
        verdict = "PASS"
        ok = True
        decision = "ALLOW_THIRD_MANUAL_TESTNET_SUBMIT"
    elif 60 <= score <= 84 or warnings:
        verdict = "PARTIAL"
        ok = False
        if score >= 75:
            decision = "ALLOW_SMALL_BATCH_DRY_RUN_ONLY"
        else:
            decision = "REVIEW"
    else:
        verdict = "FAIL"
        ok = False
        decision = "STOP"

    if decision == "ALLOW_THIRD_MANUAL_TESTNET_SUBMIT":
        warnings.append("NO_AUTO_BATCH_LIVE_SUBMIT")
    if decision == "ALLOW_SMALL_BATCH_DRY_RUN_ONLY":
        warnings.append("NO_AUTO_BATCH_LIVE_SUBMIT")

    return {
        "ok": ok,
        "verdict": verdict,
        "safety_score": score,
        "score_components": score_components,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "decision": decision,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate two-submit safety score report")
    parser.add_argument("--first-final-report-json", required=True)
    parser.add_argument("--second-evidence-json", required=True)
    parser.add_argument("--second-incident-json", required=True)
    parser.add_argument("--repeatability-json", required=True)
    parser.add_argument("--output-json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = generate_safety_score(
        load_json(args.first_final_report_json),
        load_json(args.second_evidence_json),
        load_json(args.second_incident_json),
        load_json(args.repeatability_json),
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
