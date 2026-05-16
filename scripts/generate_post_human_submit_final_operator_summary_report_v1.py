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


def generate_operator_summary(
    final_session_health_score: Optional[Dict[str, Any]],
    readonly_evidence: Optional[Dict[str, Any]],
    incident_review_phase: Optional[Dict[str, Any]],
    audit_manifest: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    blockers = []
    warnings = []
    summary_items = {}
    operator_next_actions = []

    payloads = [final_session_health_score, readonly_evidence, incident_review_phase, audit_manifest]

    if not isinstance(final_session_health_score, dict):
        blockers.append("FINAL_SESSION_HEALTH_SCORE_MISSING")
    if not isinstance(readonly_evidence, dict):
        blockers.append("READONLY_EVIDENCE_MISSING")
    if not isinstance(incident_review_phase, dict):
        blockers.append("INCIDENT_REVIEW_PHASE_MISSING")

    health_verdict = str((final_session_health_score or {}).get("verdict", ""))
    health_decision = str((final_session_health_score or {}).get("decision", ""))
    health_score = int((final_session_health_score or {}).get("health_score", 0))

    summary_items = {
        "submit_executed": bool((readonly_evidence or {}).get("submit_executed", False)),
        "env": str((readonly_evidence or {}).get("env", "")),
        "symbol": str((readonly_evidence or {}).get("symbol", "")),
        "side": str((readonly_evidence or {}).get("side", "")),
        "quantity": str((readonly_evidence or {}).get("quantity", "")),
        "position_detected": bool((readonly_evidence or {}).get("position_detected", False)),
        "stop_market_detected": bool((readonly_evidence or {}).get("stop_market_detected", False)),
        "take_profit_market_detected": bool((readonly_evidence or {}).get("take_profit_market_detected", False)),
        "naked_position_detected": bool((readonly_evidence or {}).get("naked_position_detected", False)),
        "orphan_protection_detected": bool((readonly_evidence or {}).get("orphan_protection_detected", False)),
        "incident_level": str((final_session_health_score or {}).get("incident_level", "UNKNOWN")),
        "audit_manifest_status": str((audit_manifest or {}).get("verdict", "UNKNOWN")),
        "final_health_score": health_score,
        "final_health_decision": health_decision,
    }

    if blockers:
        verdict = "FAIL"
        ok = False
        session_status = "STOPPED"
    elif health_verdict == "PASS" and health_decision == "HEALTHY_SESSION_CLOSED":
        verdict = "PASS"
        ok = True
        session_status = "CLOSED_HEALTHY"
        operator_next_actions = ["SESSION_ARCHIVE_READY"]
    elif health_decision == "MONITOR":
        verdict = "PARTIAL"
        ok = False
        session_status = "MONITOR"
        operator_next_actions = ["CONTINUE_MONITORING"]
    elif health_decision == "REVIEW_REQUIRED":
        verdict = "PARTIAL"
        ok = False
        session_status = "REVIEW_REQUIRED"
        operator_next_actions = ["INITIATE_HUMAN_REVIEW"]
    elif health_decision == "ROLLBACK_REVIEW_REQUIRED":
        verdict = "FAIL"
        ok = False
        session_status = "ROLLBACK_REVIEW_REQUIRED"
        operator_next_actions = ["INITIATE_HUMAN_ROLLBACK_REVIEW"]
    else:
        verdict = "FAIL"
        ok = False
        session_status = "STOPPED"
        operator_next_actions = ["STOP_AND_RESOLVE_BLOCKERS"]

    return {
        "ok": ok,
        "verdict": verdict,
        "report_type": "POST_HUMAN_SUBMIT_FINAL_OPERATOR_SUMMARY",
        "session_status": session_status,
        "readonly": True,
        "submit_allowed": False,
        "cancel_allowed": False,
        "flatten_allowed": False,
        "summary_items": summary_items,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "operator_next_actions": operator_next_actions,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate post-human-submit final operator summary report")
    parser.add_argument("--final-session-health-score-json", required=True)
    parser.add_argument("--readonly-evidence-json", required=True)
    parser.add_argument("--incident-review-phase-json", required=True)
    parser.add_argument("--audit-manifest-json")
    parser.add_argument("--output-json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = generate_operator_summary(
        load_json(args.final_session_health_score_json),
        load_json(args.readonly_evidence_json),
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
