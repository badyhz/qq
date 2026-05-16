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


def generate_eligibility(second_phase: Optional[Dict[str, Any]], two_submit_score: Optional[Dict[str, Any]] = None, repeatability: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    blockers = []
    warnings = []

    if second_phase is None:
        blockers.append("SECOND_PHASE_CONTROL_MALFORMED_OR_MISSING")

    decision = str((second_phase or {}).get("decision", ""))
    can_submit_again = bool((second_phase or {}).get("can_submit_again") is True)
    max_next = (second_phase or {}).get("max_next_submit_count")

    if decision != "ALLOW_THIRD_MANUAL_TESTNET_SUBMIT":
        blockers.append("SECOND_PHASE_DECISION_NOT_ALLOW_THIRD_MANUAL_TESTNET_SUBMIT")
    if not can_submit_again:
        blockers.append("SECOND_PHASE_CAN_SUBMIT_AGAIN_FALSE")
    if max_next != 1:
        blockers.append("SECOND_PHASE_MAX_NEXT_SUBMIT_COUNT_NOT_ONE")

    if two_submit_score is None:
        warnings.append("TWO_SUBMIT_SAFETY_SCORE_NOT_PROVIDED")
    elif str(two_submit_score.get("verdict", "")) != "PASS":
        blockers.append("TWO_SUBMIT_SAFETY_SCORE_NOT_PASS")

    if repeatability is None:
        warnings.append("REPEATABILITY_REPORT_NOT_PROVIDED")
    elif str(repeatability.get("verdict", "")) != "PASS":
        blockers.append("REPEATABILITY_REPORT_NOT_PASS")

    inherited_constraints = {
        "manual_token_gate_required": True,
        "default_dry_run": True,
        "single_submit_only": True,
        "no_auto_repeat_submit": True,
    }

    if blockers:
        verdict = "FAIL"
        ok = False
        eligible = False
    elif warnings:
        verdict = "PARTIAL"
        ok = False
        eligible = False
    else:
        verdict = "PASS"
        ok = True
        eligible = True

    return {
        "ok": ok,
        "verdict": verdict,
        "eligible_for_third_manual_submit": eligible,
        "max_submit_count": 1 if eligible else 0,
        "required_manual_confirmation": True,
        "inherited_constraints": inherited_constraints,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "next_actions": (
            ["BUILD_THIRD_MANUAL_SUBMIT_COMMAND_PACKET", "REQUIRE_FRESH_CONFIRM_TOKEN"]
            if eligible
            else ["MANUAL_REVIEW_REQUIRED", "DO_NOT_SUBMIT"]
        ),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate third manual testnet submit eligibility packet")
    parser.add_argument("--second-phase-control-json", required=True)
    parser.add_argument("--two-submit-safety-score-json")
    parser.add_argument("--repeatability-json")
    parser.add_argument("--output-json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = generate_eligibility(
        load_json(args.second_phase_control_json),
        load_json(args.two_submit_safety_score_json) if args.two_submit_safety_score_json else None,
        load_json(args.repeatability_json) if args.repeatability_json else None,
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
