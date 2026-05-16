#!/usr/bin/env python3
import argparse
import json
import os
import sys
from typing import Any, Dict, Optional

PHASE = "FIRST_TESTNET_SUBMIT_REVIEW"


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


def generate_final_report(
    phase_control: Optional[Dict[str, Any]],
    evidence: Optional[Dict[str, Any]],
    incident: Optional[Dict[str, Any]],
    rollback_recommendation: Optional[Dict[str, Any]],
    audit_manifest: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    blockers = []
    warnings = []

    if phase_control is None:
        blockers.append("PHASE_CONTROL_INPUT_MISSING")
    if evidence is None:
        blockers.append("EVIDENCE_INPUT_MISSING")
    if incident is None:
        blockers.append("INCIDENT_INPUT_MISSING")
    if rollback_recommendation is None:
        blockers.append("ROLLBACK_RECOMMENDATION_INPUT_MISSING")
    if audit_manifest is None:
        blockers.append("AUDIT_MANIFEST_INPUT_MISSING")

    if blockers:
        decision = "HOLD"
        verdict = "FAIL"
        can_continue = False
        can_submit_again = False
        max_next_submit_count = 0
        return {
            "ok": False,
            "verdict": verdict,
            "phase": PHASE,
            "decision": decision,
            "can_continue": can_continue,
            "can_submit_again": can_submit_again,
            "max_next_submit_count": max_next_submit_count,
            "blockers": sorted(set(blockers)),
            "warnings": warnings,
            "required_next_actions": ["FIX_INPUT_ARTIFACTS"],
            "next_task_recommendation": "REBUILD_REVIEW_ARTIFACTS",
        }

    phase_verdict = str(phase_control.get("verdict", ""))
    evidence_verdict = str(evidence.get("verdict", ""))
    incident_verdict = str(incident.get("verdict", ""))
    incident_level = str(incident.get("incident_level", ""))
    rollback_rec = str(rollback_recommendation.get("recommendation", ""))
    audit_verdict = str(audit_manifest.get("verdict", ""))

    if audit_verdict == "FAIL":
        blockers.append("AUDIT_MANIFEST_FAILED")
    if incident_level == "CRITICAL":
        blockers.append("CRITICAL_INCIDENT_DETECTED")

    if rollback_rec == "MANUAL_CONFIRM_FLATTEN_REQUIRED":
        decision = "REQUIRE_ROLLBACK_REVIEW"
        verdict = "FAIL"
        can_continue = False
        required_next_actions = ["MANUAL_FLATTEN_REVIEW", "RISK_OWNER_SIGNOFF"]
        next_task = "ROLLBACK_REVIEW_GATE"
    elif incident_level == "CRITICAL":
        decision = "STOP"
        verdict = "FAIL"
        can_continue = False
        required_next_actions = ["STOP_SUBMIT_FLOW", "MANUAL_INCIDENT_REVIEW"]
        next_task = "INCIDENT_RESPONSE"
    elif audit_verdict == "FAIL":
        decision = "STOP"
        verdict = "FAIL"
        can_continue = False
        required_next_actions = ["FIX_AUDIT_CHAIN", "REGENERATE_MANIFEST"]
        next_task = "AUDIT_CHAIN_REPAIR"
    elif (
        phase_verdict == "PASS"
        and evidence_verdict == "PASS"
        and incident_verdict == "PASS"
        and incident_level == "NONE"
        and audit_verdict == "PASS"
    ):
        decision = "ALLOW_NEXT_TESTNET_SUBMIT"
        verdict = "PASS"
        can_continue = True
        required_next_actions = ["LIMIT_NEXT_SUBMIT_TO_SINGLE_ORDER", "KEEP_MANUAL_TOKEN_GATE"]
        next_task = "SECOND_TESTNET_SUBMIT_SMALL_BATCH_VALIDATION"
    elif (
        phase_verdict == "PARTIAL"
        or evidence_verdict == "PARTIAL"
        or incident_verdict == "PARTIAL"
        or audit_verdict == "PARTIAL"
    ):
        decision = "REVIEW"
        verdict = "PARTIAL"
        can_continue = False
        required_next_actions = ["MANUAL_REVIEW", "COLLECT_MORE_EVIDENCE"]
        next_task = "RESOLVE_PARTIAL_FINDINGS"
    else:
        decision = "REVIEW"
        verdict = "PARTIAL"
        can_continue = False
        required_next_actions = ["MANUAL_REVIEW"]
        next_task = "RECHECK_PHASE_ARTIFACTS"

    can_submit_again = decision == "ALLOW_NEXT_TESTNET_SUBMIT"
    max_next_submit_count = 1 if can_submit_again else 0

    if not can_submit_again:
        warnings.append("REPEATED_SUBMIT_NOT_ALLOWED")

    return {
        "ok": verdict == "PASS",
        "verdict": verdict,
        "phase": PHASE,
        "decision": decision,
        "can_continue": can_continue,
        "can_submit_again": can_submit_again,
        "max_next_submit_count": max_next_submit_count,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "required_next_actions": required_next_actions,
        "next_task_recommendation": next_task,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate first testnet submit final phase control report")
    parser.add_argument("--phase-control-json", required=True)
    parser.add_argument("--evidence-json", required=True)
    parser.add_argument("--incident-json", required=True)
    parser.add_argument("--rollback-recommendation-json", required=True)
    parser.add_argument("--audit-manifest-json", required=True)
    parser.add_argument("--output-json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = generate_final_report(
        load_json(args.phase_control_json),
        load_json(args.evidence_json),
        load_json(args.incident_json),
        load_json(args.rollback_recommendation_json),
        load_json(args.audit_manifest_json),
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
