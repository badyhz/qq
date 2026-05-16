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


def generate_health_score(
    readonly_evidence: Optional[Dict[str, Any]],
    verification_phase: Optional[Dict[str, Any]],
    incident: Optional[Dict[str, Any]],
    incident_review_phase: Optional[Dict[str, Any]],
    audit_manifest: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    blockers = []
    warnings = []

    payloads = [readonly_evidence, verification_phase, incident, incident_review_phase, audit_manifest]

    if not isinstance(readonly_evidence, dict):
        blockers.append("READONLY_EVIDENCE_MISSING")
    if not isinstance(verification_phase, dict):
        blockers.append("VERIFICATION_PHASE_MISSING")
    if not isinstance(incident, dict):
        blockers.append("INCIDENT_MISSING")
    if not isinstance(incident_review_phase, dict):
        blockers.append("INCIDENT_REVIEW_PHASE_MISSING")

    incident_level = str((incident or {}).get("incident_level", "NONE"))

    score = 100
    score_components = {
        "base_score": 100,
        "incident_penalty": 0,
        "evidence_penalty": 0,
        "audit_penalty": 0,
        "verification_penalty": 0,
    }

    if incident_level == "CRITICAL":
        score = 0
        score_components["incident_penalty"] = 100
    elif incident_level == "HIGH":
        score = min(score, 40)
        score_components["incident_penalty"] = 60
    elif incident_level == "MEDIUM":
        score = min(score, 70)
        score_components["incident_penalty"] = 30
    elif incident_level == "LOW":
        score = min(score, 85)
        score_components["incident_penalty"] = 15

    evidence_verdict = str((readonly_evidence or {}).get("verdict", ""))
    if evidence_verdict == "PARTIAL":
        score -= 20
        score_components["evidence_penalty"] = 20
    elif evidence_verdict == "FAIL":
        score = min(score, 50)
        score_components["evidence_penalty"] = 50

    audit_verdict = str((audit_manifest or {}).get("verdict", ""))
    if audit_verdict == "PARTIAL":
        score -= 10
        score_components["audit_penalty"] = 10
    elif audit_verdict == "FAIL":
        score = min(score, 50)
        score_components["audit_penalty"] = 50

    verification_verdict = str((verification_phase or {}).get("verdict", ""))
    if verification_verdict == "FAIL":
        score = min(score, 50)
        score_components["verification_penalty"] = 50

    score = max(0, score)

    if blockers:
        verdict = "FAIL"
        ok = False
        decision = "STOP"
    elif score >= 85 and incident_level == "NONE" and audit_verdict == "PASS":
        verdict = "PASS"
        ok = True
        decision = "HEALTHY_SESSION_CLOSED"
    elif score >= 60:
        verdict = "PARTIAL"
        ok = False
        if incident_level in ("LOW", "MEDIUM"):
            decision = "REVIEW_REQUIRED"
        else:
            decision = "MONITOR"
    else:
        verdict = "FAIL"
        ok = False
        if incident_level in ("HIGH", "CRITICAL"):
            decision = "ROLLBACK_REVIEW_REQUIRED"
        else:
            decision = "STOP"

    return {
        "ok": ok,
        "verdict": verdict,
        "health_score": score,
        "score_components": score_components,
        "readonly": True,
        "submit_allowed": False,
        "cancel_allowed": False,
        "flatten_allowed": False,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "decision": decision,
        "incident_level": incident_level,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate post-human-submit final session health score")
    parser.add_argument("--readonly-evidence-json", required=True)
    parser.add_argument("--verification-phase-json", required=True)
    parser.add_argument("--incident-json", required=True)
    parser.add_argument("--incident-review-phase-json", required=True)
    parser.add_argument("--audit-manifest-json")
    parser.add_argument("--output-json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = generate_health_score(
        load_json(args.readonly_evidence_json),
        load_json(args.verification_phase_json),
        load_json(args.incident_json),
        load_json(args.incident_review_phase_json),
        load_json(args.audit_manifest_json) if args.audit_manifest_json else None,
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
