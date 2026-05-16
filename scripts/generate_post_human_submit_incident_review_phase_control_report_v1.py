#!/usr/bin/env python3
import argparse
import json
import os
import sys
from typing import Any, Dict, Optional


PHASE = "POST_HUMAN_SUBMIT_INCIDENT_REVIEW"


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


def generate_phase_report(
    incident: Optional[Dict[str, Any]],
    rollback_eligibility: Optional[Dict[str, Any]],
    operator_checklist: Optional[Dict[str, Any]],
    safe_flatten_dry_run_review: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    warnings = []
    blockers = []

    payloads = [incident, rollback_eligibility, operator_checklist, safe_flatten_dry_run_review]
    if not isinstance(incident, dict):
        blockers.append("INCIDENT_MISSING")
    if not isinstance(rollback_eligibility, dict):
        blockers.append("ROLLBACK_ELIGIBILITY_MISSING")
    if not isinstance(operator_checklist, dict):
        blockers.append("OPERATOR_CHECKLIST_MISSING")

    verdicts = [str((v or {}).get("verdict", "")) for v in [incident, rollback_eligibility, operator_checklist, safe_flatten_dry_run_review]]

    incident_level = str((incident or {}).get("incident_level", "NONE"))
    checklist_status = str((operator_checklist or {}).get("checklist_status", "BLOCKED"))

    for data in payloads:
        if data and _has_unsafe_marker(data):
            blockers.append("UNSAFE_MARKER_DETECTED")

    if any(bool((v or {}).get("submit_allowed") is True) for v in payloads):
        blockers.append("SUBMIT_ALLOWED_TRUE_NOT_PERMITTED")
    if any(bool((v or {}).get("cancel_allowed") is True) for v in payloads):
        blockers.append("CANCEL_ALLOWED_TRUE_NOT_PERMITTED")
    if any(bool((v or {}).get("flatten_allowed") is True) for v in payloads):
        blockers.append("FLATTEN_ALLOWED_TRUE_NOT_PERMITTED")

    max_submit_count = 0

    if blockers:
        verdict = "FAIL"
        decision = "STOP"
        ok = False
        can_continue = False
    elif incident_level in ("HIGH", "CRITICAL"):
        verdict = "FAIL"
        decision = "REQUIRE_HUMAN_ROLLBACK_REVIEW"
        ok = False
        can_continue = False
    elif incident_level == "MEDIUM" or any(v == "PARTIAL" for v in verdicts) or checklist_status == "ROLLBACK_REVIEW_REQUIRED":
        verdict = "PARTIAL"
        decision = "REVIEW"
        ok = False
        can_continue = False
    elif incident_level == "LOW":
        verdict = "PASS"
        decision = "MONITOR_ONLY"
        ok = True
        can_continue = False
    else:
        verdict = "PASS"
        decision = "VERIFIED_SAFE_NO_ACTION"
        ok = True
        can_continue = False

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
        "max_submit_count": max_submit_count,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "required_next_actions": (
            ["VERIFICATION_COMPLETE_NO_ACTION"]
            if decision == "VERIFIED_SAFE_NO_ACTION"
            else ["MONITOR_ONLY_CONTINUE"]
            if decision == "MONITOR_ONLY"
            else ["INITIATE_HUMAN_ROLLBACK_REVIEW"]
            if decision == "REQUIRE_HUMAN_ROLLBACK_REVIEW"
            else ["RESOLVE_INCIDENT_REVIEW_GAPS"]
        ),
        "next_task_recommendation": (
            "archive_post_human_submit_artifacts"
            if decision == "VERIFIED_SAFE_NO_ACTION"
            else "human_rollback_review_and_decision"
            if decision == "REQUIRE_HUMAN_ROLLBACK_REVIEW"
            else "post_human_submit_incident_review_continue"
        ),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate post-human-submit incident review phase control report")
    parser.add_argument("--incident-json", required=True)
    parser.add_argument("--rollback-eligibility-json", required=True)
    parser.add_argument("--operator-checklist-json", required=True)
    parser.add_argument("--safe-flatten-dry-run-review-json")
    parser.add_argument("--output-json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = generate_phase_report(
        load_json(args.incident_json),
        load_json(args.rollback_eligibility_json),
        load_json(args.operator_checklist_json),
        load_json(args.safe_flatten_dry_run_review_json) if args.safe_flatten_dry_run_review_json else None,
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
