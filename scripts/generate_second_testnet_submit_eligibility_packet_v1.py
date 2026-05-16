#!/usr/bin/env python3
import argparse
import json
import os
import sys
from typing import Any, Dict, Optional


def load_json(path: str) -> Optional[Dict[str, Any]]:
    if not path:
        return None
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


def generate_eligibility(first_final: Optional[Dict[str, Any]], first_audit: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    blockers = []
    warnings = []

    if first_final is None:
        blockers.append("FIRST_FINAL_REPORT_MALFORMED_OR_MISSING")

    decision = str((first_final or {}).get("decision", ""))
    can_submit_again = bool((first_final or {}).get("can_submit_again") is True)
    max_next = (first_final or {}).get("max_next_submit_count")

    if decision != "ALLOW_NEXT_TESTNET_SUBMIT":
        blockers.append("FIRST_FINAL_DECISION_NOT_ALLOW_NEXT_TESTNET_SUBMIT")
    if not can_submit_again:
        blockers.append("FIRST_FINAL_CAN_SUBMIT_AGAIN_FALSE")
    if max_next != 1:
        blockers.append("FIRST_FINAL_MAX_NEXT_SUBMIT_COUNT_NOT_ONE")

    inherited_constraints = {
        "manual_token_gated": True,
        "default_dry_run": True,
        "max_single_submit_per_phase": 1,
        "no_auto_loop": True,
    }

    if first_audit is not None:
        audit_verdict = str(first_audit.get("verdict", ""))
        if audit_verdict == "PARTIAL":
            warnings.append("INHERITED_AUDIT_PARTIAL_WARNING")
        elif audit_verdict == "FAIL":
            blockers.append("FIRST_AUDIT_MANIFEST_FAIL")

    if not blockers and not warnings:
        verdict = "PASS"
        ok = True
        eligible = True
    elif not blockers:
        verdict = "PARTIAL"
        ok = False
        eligible = False
    else:
        verdict = "FAIL"
        ok = False
        eligible = False

    if verdict == "PASS":
        next_actions = ["BUILD_SECOND_SUBMIT_COMMAND_PACKET", "REQUIRE_MANUAL_CONFIRMATION_TOKEN"]
    elif verdict == "PARTIAL":
        next_actions = ["REVIEW_INHERITED_WARNINGS", "MANUAL_SIGNOFF_REQUIRED"]
    else:
        next_actions = ["STOP_SECOND_SUBMIT", "FIX_FIRST_PHASE_BLOCKERS"]

    return {
        "ok": ok,
        "verdict": verdict,
        "eligible_for_second_submit": eligible,
        "max_submit_count": 1 if eligible else 0,
        "required_manual_confirmation": True,
        "inherited_constraints": inherited_constraints,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "next_actions": next_actions,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate second testnet submit eligibility packet")
    parser.add_argument("--first-final-phase-report-json", required=True)
    parser.add_argument("--first-audit-manifest-json")
    parser.add_argument("--output-json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = generate_eligibility(
        load_json(args.first_final_phase_report_json),
        load_json(args.first_audit_manifest_json) if args.first_audit_manifest_json else None,
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
