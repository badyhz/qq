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


def generate_gate(
    manual_review_phase: Optional[Dict[str, Any]],
    review_score: Optional[Dict[str, Any]] = None,
    checklist: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    blockers = []
    warnings = []

    if not isinstance(manual_review_phase, dict):
        blockers.append("MANUAL_REVIEW_PHASE_MISSING_OR_MALFORMED")
        manual_review_phase = {}

    if str(manual_review_phase.get("decision", "")) != "ALLOW_SINGLE_MANUAL_SUBMIT_PACKET_GENERATION":
        blockers.append("MANUAL_REVIEW_PHASE_DECISION_NOT_ALLOWED")
    if bool(manual_review_phase.get("submit_allowed") is True):
        blockers.append("MANUAL_REVIEW_PHASE_SUBMIT_ALLOWED_TRUE")
    if int(manual_review_phase.get("max_submit_count", -1)) != 0:
        blockers.append("MANUAL_REVIEW_PHASE_MAX_SUBMIT_COUNT_NOT_ZERO")

    if review_score is None:
        warnings.append("REVIEW_SCORE_MISSING_OPTIONAL")
    else:
        rsv = str(review_score.get("verdict", ""))
        if rsv == "FAIL":
            blockers.append("REVIEW_SCORE_FAIL")
        elif rsv != "PASS":
            warnings.append("REVIEW_SCORE_NOT_PASS")

    if checklist is not None:
        ckv = str(checklist.get("verdict", ""))
        if ckv == "FAIL":
            blockers.append("RISK_ACCEPTANCE_CHECKLIST_FAIL")
        elif ckv != "PASS":
            warnings.append("RISK_ACCEPTANCE_CHECKLIST_NOT_PASS")

    if blockers:
        verdict = "FAIL"
        ok = False
        eligible = False
        max_submit_count = 0
    elif warnings:
        verdict = "PARTIAL"
        ok = True
        eligible = False
        max_submit_count = 0
    else:
        verdict = "PASS"
        ok = True
        eligible = True
        max_submit_count = 1

    return {
        "ok": ok,
        "verdict": verdict,
        "eligible_for_packet_generation": eligible,
        "packet_mode": "SINGLE_MANUAL_TESTNET_SUBMIT_PACKET",
        "submit_allowed": False,
        "max_submit_count": max_submit_count,
        "required_manual_confirmation": True,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "inherited_constraints": {
            "review_only": True,
            "submit_allowed": False,
            "manual_token_gate_required": True,
            "env_must_be_testnet": True,
        },
        "next_actions": (
            ["GENERATE_SINGLE_MANUAL_SUBMIT_PACKET"]
            if eligible
            else ["RESOLVE_REVIEW_WARNINGS_OR_BLOCKERS"]
        ),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate single manual testnet submit packet eligibility gate")
    parser.add_argument("--manual-review-phase-json", required=True)
    parser.add_argument("--review-score-json")
    parser.add_argument("--risk-acceptance-checklist-json")
    parser.add_argument("--output-json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = generate_gate(
        load_json(args.manual_review_phase_json),
        load_json(args.review_score_json) if args.review_score_json else None,
        load_json(args.risk_acceptance_checklist_json) if args.risk_acceptance_checklist_json else None,
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
