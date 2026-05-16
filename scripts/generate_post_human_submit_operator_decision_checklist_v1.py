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


def generate_operator_checklist(
    incident: Optional[Dict[str, Any]],
    rollback_eligibility: Optional[Dict[str, Any]],
    safe_flatten_dry_run_review: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    blockers = []
    warnings = []

    if not isinstance(incident, dict):
        blockers.append("INCIDENT_MISSING")
    if not isinstance(rollback_eligibility, dict):
        blockers.append("ROLLBACK_ELIGIBILITY_MISSING")

    incident_level = str((incident or {}).get("incident_level", "NONE"))

    checklist_status = "BLOCKED"
    required_human_checks = []

    if not blockers:
        if incident_level == "NONE":
            checklist_status = "NO_ACTION_REQUIRED"
        elif incident_level == "LOW":
            checklist_status = "MONITOR"
        elif incident_level in ("MEDIUM", "HIGH", "CRITICAL"):
            checklist_status = "ROLLBACK_REVIEW_REQUIRED"
            required_human_checks = [
                "verify env=testnet",
                "verify current position manually",
                "verify protective SL/TP state",
                "verify naked/orphan status",
                "verify safe_flatten dry-run before any confirm",
                "verify no mainnet/live marker",
                "verify no repeated submit",
            ]

    if any(bool((v or {}).get("submit_allowed") is True) for v in [incident, rollback_eligibility, safe_flatten_dry_run_review]):
        blockers.append("SUBMIT_ALLOWED_TRUE_NOT_PERMITTED")
    if any(bool((v or {}).get("cancel_allowed") is True) for v in [incident, rollback_eligibility, safe_flatten_dry_run_review]):
        blockers.append("CANCEL_ALLOWED_TRUE_NOT_PERMITTED")
    if any(bool((v or {}).get("flatten_allowed") is True) for v in [incident, rollback_eligibility, safe_flatten_dry_run_review]):
        blockers.append("FLATTEN_ALLOWED_TRUE_NOT_PERMITTED")

    if blockers:
        verdict = "FAIL"
        ok = False
    elif checklist_status in ("NO_ACTION_REQUIRED", "MONITOR"):
        verdict = "PASS"
        ok = True
    elif checklist_status in ("REVIEW", "ROLLBACK_REVIEW_REQUIRED"):
        verdict = "PARTIAL"
        ok = False
    else:
        verdict = "FAIL"
        ok = False

    return {
        "ok": ok,
        "verdict": verdict,
        "checklist_type": "POST_HUMAN_SUBMIT_OPERATOR_DECISION",
        "checklist_status": checklist_status,
        "readonly": True,
        "submit_allowed": False,
        "cancel_allowed": False,
        "flatten_allowed": False,
        "required_human_checks": required_human_checks,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "operator_notes": "all actions remain disabled; human decision required before any action",
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate post-human-submit operator decision checklist")
    parser.add_argument("--incident-json", required=True)
    parser.add_argument("--rollback-eligibility-json", required=True)
    parser.add_argument("--safe-flatten-dry-run-review-json")
    parser.add_argument("--output-json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = generate_operator_checklist(
        load_json(args.incident_json),
        load_json(args.rollback_eligibility_json),
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
