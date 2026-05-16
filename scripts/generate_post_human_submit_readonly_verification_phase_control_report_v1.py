#!/usr/bin/env python3
import argparse
import json
import os
import sys
from typing import Any, Dict, Optional


PHASE = "POST_HUMAN_SUBMIT_READONLY_VERIFICATION"


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


def generate_phase_report(
    verification_eligibility: Optional[Dict[str, Any]],
    receipt_parser: Optional[Dict[str, Any]],
    protection_plan: Optional[Dict[str, Any]],
    readonly_evidence: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    warnings = []
    blockers = []

    payloads = {
        "verification_eligibility": verification_eligibility,
        "receipt_parser": receipt_parser,
        "protection_plan": protection_plan,
        "readonly_evidence": readonly_evidence,
    }
    for name, value in payloads.items():
        if not isinstance(value, dict):
            blockers.append(f"{name.upper()}_MISSING")

    verdicts = [str((v or {}).get("verdict", "")) for v in payloads.values()]

    naked_detected = bool((readonly_evidence or {}).get("naked_position_detected", False))
    orphan_detected = bool((readonly_evidence or {}).get("orphan_protection_detected", False))

    if naked_detected:
        blockers.append("NAKED_POSITION_DETECTED")
    if orphan_detected:
        blockers.append("ORPHAN_PROTECTION_DETECTED")

    if any(bool((v or {}).get("submit_allowed") is True) for v in payloads.values()):
        blockers.append("SUBMIT_ALLOWED_TRUE_NOT_PERMITTED")
    if any(bool((v or {}).get("cancel_allowed") is True) for v in payloads.values()):
        blockers.append("CANCEL_ALLOWED_TRUE_NOT_PERMITTED")
    if any(bool((v or {}).get("flatten_allowed") is True) for v in payloads.values()):
        blockers.append("FLATTEN_ALLOWED_TRUE_NOT_PERMITTED")

    max_submit_count = 0

    if blockers or any(v == "FAIL" for v in verdicts):
        verdict = "FAIL"
        if naked_detected or orphan_detected:
            decision = "REQUIRE_ROLLBACK_REVIEW"
        else:
            decision = "STOP"
        ok = False
        can_continue = False
    elif any(v == "PARTIAL" for v in verdicts):
        verdict = "PARTIAL"
        decision = "REVIEW"
        ok = False
        can_continue = False
    else:
        verdict = "PASS"
        decision = "VERIFIED_ONE_SHOT_TESTNET_SUBMIT"
        ok = True
        can_continue = True

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
            ["REVIEW_COMPLETE", "ARCHIVE_ARTIFACTS"]
            if decision == "VERIFIED_ONE_SHOT_TESTNET_SUBMIT"
            else ["IMMEDIATE_ROLLBACK_REVIEW"]
            if decision == "REQUIRE_ROLLBACK_REVIEW"
            else ["RESOLVE_FINAL_VERIFICATION_GAPS"]
        ),
        "next_task_recommendation": (
            "one_shot_testnet_submit_archive"
            if decision == "VERIFIED_ONE_SHOT_TESTNET_SUBMIT"
            else "rollback_review_and_actions"
            if decision == "REQUIRE_ROLLBACK_REVIEW"
            else "post_human_submit_readonly_verification_review"
        ),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate post-human-submit readonly verification phase control report")
    parser.add_argument("--verification-eligibility-json", required=True)
    parser.add_argument("--receipt-parser-json", required=True)
    parser.add_argument("--protection-plan-json", required=True)
    parser.add_argument("--readonly-evidence-json", required=True)
    parser.add_argument("--output-json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = generate_phase_report(
        load_json(args.verification_eligibility_json),
        load_json(args.receipt_parser_json),
        load_json(args.protection_plan_json),
        load_json(args.readonly_evidence_json),
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
