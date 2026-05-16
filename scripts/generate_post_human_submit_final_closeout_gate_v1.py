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


def generate_closeout_gate(
    final_session_health_score: Optional[Dict[str, Any]],
    operator_summary: Optional[Dict[str, Any]],
    audit_manifest: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    blockers = []
    warnings = []
    closeout_notes = []

    payloads = [final_session_health_score, operator_summary, audit_manifest]

    if not isinstance(final_session_health_score, dict):
        blockers.append("FINAL_SESSION_HEALTH_SCORE_MISSING")
    if not isinstance(operator_summary, dict):
        blockers.append("OPERATOR_SUMMARY_MISSING")

    health_verdict = str((final_session_health_score or {}).get("verdict", ""))
    health_decision = str((final_session_health_score or {}).get("decision", ""))
    operator_verdict = str((operator_summary or {}).get("verdict", ""))
    operator_status = str((operator_summary or {}).get("session_status", ""))
    audit_verdict = str((audit_manifest or {}).get("verdict", "")) if audit_manifest else "UNKNOWN"

    if blockers:
        verdict = "FAIL"
        ok = False
        closeout_status = "BLOCKED"
        next_allowed_phase = "NONE"
    elif (
        health_verdict == "PASS"
        and operator_verdict == "PASS"
        and (audit_verdict == "PASS" or audit_verdict == "UNKNOWN")
        and health_decision == "HEALTHY_SESSION_CLOSED"
        and operator_status == "CLOSED_HEALTHY"
    ):
        verdict = "PASS"
        ok = True
        closeout_status = "CLOSED"
        next_allowed_phase = "NONE"
        closeout_notes = ["SESSION_CLOSED_HEALTHY_NO_FURTHER_ACTION"]
    elif operator_status == "MONITOR" or health_decision == "MONITOR":
        verdict = "PARTIAL"
        ok = False
        closeout_status = "MONITOR"
        next_allowed_phase = "MONITORING_REVIEW"
        closeout_notes = ["CONTINUE_MONITORING_BEFORE_FINAL_CLOSEOUT"]
    elif operator_status == "REVIEW_REQUIRED" or health_decision == "REVIEW_REQUIRED":
        verdict = "PARTIAL"
        ok = False
        closeout_status = "REVIEW"
        next_allowed_phase = "HUMAN_REVIEW"
        closeout_notes = ["HUMAN_REVIEW_REQUIRED_BEFORE_FINAL_CLOSEOUT"]
    elif operator_status == "ROLLBACK_REVIEW_REQUIRED" or health_decision == "ROLLBACK_REVIEW_REQUIRED":
        verdict = "FAIL"
        ok = False
        closeout_status = "ROLLBACK_REVIEW"
        next_allowed_phase = "HUMAN_ROLLBACK_REVIEW"
        closeout_notes = ["HUMAN_ROLLBACK_REVIEW_REQUIRED"]
    else:
        verdict = "FAIL"
        ok = False
        closeout_status = "BLOCKED"
        next_allowed_phase = "NONE"
        closeout_notes = ["SESSION_CANNOT_BE_CLOSED_DUE_TO_BLOCKERS"]

    return {
        "ok": ok,
        "verdict": verdict,
        "gate_type": "POST_HUMAN_SUBMIT_FINAL_CLOSEOUT",
        "closeout_status": closeout_status,
        "readonly": True,
        "submit_allowed": False,
        "cancel_allowed": False,
        "flatten_allowed": False,
        "max_submit_count": 0,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "closeout_notes": closeout_notes,
        "next_allowed_phase": next_allowed_phase,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate post-human-submit final closeout gate")
    parser.add_argument("--final-session-health-score-json", required=True)
    parser.add_argument("--operator-summary-json", required=True)
    parser.add_argument("--audit-manifest-json")
    parser.add_argument("--output-json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = generate_closeout_gate(
        load_json(args.final_session_health_score_json),
        load_json(args.operator_summary_json),
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
