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


def generate_rollback_eligibility(
    incident: Optional[Dict[str, Any]],
    verification_phase: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    blockers = []
    warnings = []

    if not isinstance(incident, dict):
        blockers.append("INCIDENT_MISSING")
    if not isinstance(verification_phase, dict):
        blockers.append("VERIFICATION_PHASE_MISSING")

    incident_level = str((incident or {}).get("incident_level", "NONE"))
    verification_decision = str((verification_phase or {}).get("decision", ""))

    eligible_for_rollback_review = False
    required_action = "NONE"

    if not blockers:
        if incident_level == "NONE" and verification_decision == "VERIFIED_ONE_SHOT_TESTNET_SUBMIT":
            eligible_for_rollback_review = False
            required_action = "NONE"
        elif incident_level in ("LOW", "MEDIUM"):
            eligible_for_rollback_review = True
            required_action = "REVIEW"
        elif incident_level in ("HIGH", "CRITICAL"):
            eligible_for_rollback_review = True
            required_action = "HUMAN_ROLLBACK_DECISION_REQUIRED"

    if any(bool((v or {}).get("submit_allowed") is True) for v in [incident, verification_phase]):
        blockers.append("SUBMIT_ALLOWED_TRUE_NOT_PERMITTED")
    if any(bool((v or {}).get("cancel_allowed") is True) for v in [incident, verification_phase]):
        blockers.append("CANCEL_ALLOWED_TRUE_NOT_PERMITTED")
    if any(bool((v or {}).get("flatten_allowed") is True) for v in [incident, verification_phase]):
        blockers.append("FLATTEN_ALLOWED_TRUE_NOT_PERMITTED")

    if blockers:
        verdict = "FAIL"
        ok = False
    elif incident_level in ("LOW", "MEDIUM"):
        verdict = "PARTIAL"
        ok = False
    elif incident_level in ("HIGH", "CRITICAL"):
        verdict = "FAIL"
        ok = False
    else:
        verdict = "PASS"
        ok = True

    return {
        "ok": ok,
        "verdict": verdict,
        "rollback_review_mode": "REVIEW_ONLY",
        "eligible_for_rollback_review": eligible_for_rollback_review,
        "readonly": True,
        "submit_allowed": False,
        "cancel_allowed": False,
        "flatten_allowed": False,
        "required_action": required_action,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "inherited_constraints": [
            "READONLY_ONLY",
            "NO_SUBMIT",
            "NO_CANCEL",
            "NO_FLATTEN",
            "NO_AUTO_ACTIONS",
        ],
        "next_actions": (
            ["NO_ACTION_REQUIRED"]
            if required_action == "NONE"
            else ["INITIATE_HUMAN_ROLLBACK_REVIEW"]
        ),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate post-human-submit rollback review eligibility packet")
    parser.add_argument("--incident-json", required=True)
    parser.add_argument("--verification-phase-json", required=True)
    parser.add_argument("--output-json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = generate_rollback_eligibility(
        load_json(args.incident_json),
        load_json(args.verification_phase_json),
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
