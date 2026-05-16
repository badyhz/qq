#!/usr/bin/env python3
import argparse
import json
import os
import sys
from typing import Any, Dict, Optional


PHASE = "POST_HUMAN_SUBMIT_FINAL_CLOSEOUT"


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


def generate_final_phase_report(
    audit_manifest: Optional[Dict[str, Any]],
    final_session_health_score: Optional[Dict[str, Any]],
    operator_summary: Optional[Dict[str, Any]],
    final_closeout_gate: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    blockers = []
    warnings = []
    required_next_actions = []
    next_task_recommendation = ""

    payloads = [audit_manifest, final_session_health_score, operator_summary, final_closeout_gate]

    if not isinstance(final_session_health_score, dict):
        blockers.append("FINAL_SESSION_HEALTH_SCORE_MISSING")
    if not isinstance(operator_summary, dict):
        blockers.append("OPERATOR_SUMMARY_MISSING")
    if not isinstance(final_closeout_gate, dict):
        blockers.append("FINAL_CLOSEOUT_GATE_MISSING")

    health_verdict = str((final_session_health_score or {}).get("verdict", ""))
    health_decision = str((final_session_health_score or {}).get("decision", ""))
    operator_verdict = str((operator_summary or {}).get("verdict", ""))
    closeout_status = str((final_closeout_gate or {}).get("closeout_status", ""))
    audit_verdict = str((audit_manifest or {}).get("verdict", "")) if audit_manifest else "UNKNOWN"

    all_pass = health_verdict == "PASS" and operator_verdict == "PASS" and (audit_verdict == "PASS" or audit_verdict == "UNKNOWN")
    any_partial = health_verdict == "PARTIAL" or operator_verdict == "PARTIAL"
    any_fail = health_verdict == "FAIL" or operator_verdict == "FAIL" or (audit_verdict == "FAIL")

    if blockers:
        verdict = "FAIL"
        ok = False
        decision = "STOP"
        can_continue = False
        required_next_actions = ["RESOLVE_MISSING_ARTIFACTS"]
        next_task_recommendation = "resolve_missing_artifacts_and_retry"
    elif all_pass and closeout_status == "CLOSED":
        verdict = "PASS"
        ok = True
        decision = "CLOSED"
        can_continue = False
        required_next_actions = ["SESSION_ARCHIVE_COMPLETE"]
        next_task_recommendation = "archive_session_artifacts"
    elif any_partial and closeout_status == "MONITOR":
        verdict = "PARTIAL"
        ok = False
        decision = "MONITOR"
        can_continue = False
        required_next_actions = ["CONTINUE_MONITORING"]
        next_task_recommendation = "continue_monitoring_before_final_close"
    elif any_partial and closeout_status == "REVIEW":
        verdict = "PARTIAL"
        ok = False
        decision = "REVIEW"
        can_continue = False
        required_next_actions = ["INITIATE_HUMAN_REVIEW"]
        next_task_recommendation = "human_review_required"
    elif closeout_status == "ROLLBACK_REVIEW" or health_decision == "ROLLBACK_REVIEW_REQUIRED":
        verdict = "FAIL"
        ok = False
        decision = "REQUIRE_HUMAN_ROLLBACK_REVIEW"
        can_continue = False
        required_next_actions = ["INITIATE_HUMAN_ROLLBACK_REVIEW"]
        next_task_recommendation = "human_rollback_review_required"
    elif any_fail:
        verdict = "FAIL"
        ok = False
        decision = "STOP"
        can_continue = False
        required_next_actions = ["RESOLVE_BLOCKERS_AND_RETRY"]
        next_task_recommendation = "resolve_blockers_before_closeout_attempt"
    else:
        verdict = "FAIL"
        ok = False
        decision = "STOP"
        can_continue = False
        required_next_actions = ["UNHANDLED_STATE_REQUIRES_HUMAN_INTERVENTION"]
        next_task_recommendation = "human_intervention_required"

    return {
        "ok": ok,
        "verdict": verdict,
        "phase": PHASE,
        "decision": decision,
        "can_continue": can_continue,
        "readonly": True,
        "submit_allowed": False,
        "cancel_allowed": False,
        "flatten_allowed": False,
        "max_submit_count": 0,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "required_next_actions": required_next_actions,
        "next_task_recommendation": next_task_recommendation,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate post-human-submit final phase control report")
    parser.add_argument("--audit-manifest-json")
    parser.add_argument("--final-session-health-score-json", required=True)
    parser.add_argument("--operator-summary-json", required=True)
    parser.add_argument("--final-closeout-gate-json", required=True)
    parser.add_argument("--output-json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = generate_final_phase_report(
        load_json(args.audit_manifest_json) if args.audit_manifest_json else None,
        load_json(args.final_session_health_score_json),
        load_json(args.operator_summary_json),
        load_json(args.final_closeout_gate_json),
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
