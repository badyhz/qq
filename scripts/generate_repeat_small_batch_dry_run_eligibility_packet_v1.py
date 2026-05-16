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


def generate_packet(
    small_batch_review_phase: Optional[Dict[str, Any]],
    previous_risk_concentration: Optional[Dict[str, Any]] = None,
    previous_result_aggregate: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    blockers = []
    warnings = []

    if small_batch_review_phase is None:
        blockers.append("SMALL_BATCH_REVIEW_PHASE_MISSING")
        small_batch_review_phase = {}

    decision = str(small_batch_review_phase.get("decision", ""))
    submit_allowed_in = bool(small_batch_review_phase.get("submit_allowed") is True)
    max_submit_count_in = int(small_batch_review_phase.get("max_submit_count", -1))
    max_dry = int(small_batch_review_phase.get("max_dry_run_candidates", 0) or 0)

    if decision != "ALLOW_REPEAT_SMALL_BATCH_DRY_RUN":
        blockers.append("REVIEW_PHASE_DECISION_NOT_ALLOW_REPEAT_SMALL_BATCH_DRY_RUN")
    if submit_allowed_in:
        blockers.append("REVIEW_PHASE_SUBMIT_ALLOWED_TRUE")
    if max_submit_count_in != 0:
        blockers.append("REVIEW_PHASE_MAX_SUBMIT_COUNT_NOT_ZERO")
    if max_dry <= 0:
        blockers.append("REVIEW_PHASE_MAX_DRY_RUN_CANDIDATES_INVALID")
    if max_dry > 5:
        blockers.append("REVIEW_PHASE_MAX_DRY_RUN_CANDIDATES_EXCEEDS_FIVE")

    if previous_result_aggregate is not None:
        prv = str(previous_result_aggregate.get("verdict", ""))
        if prv == "FAIL":
            blockers.append("PREVIOUS_RESULT_AGGREGATE_FAIL")
        elif prv == "PARTIAL":
            warnings.append("PREVIOUS_RESULT_AGGREGATE_PARTIAL")

    if previous_risk_concentration is not None:
        prv = str(previous_risk_concentration.get("verdict", ""))
        if prv == "FAIL":
            blockers.append("PREVIOUS_RISK_CONCENTRATION_FAIL")
        elif prv == "PARTIAL":
            warnings.append("PREVIOUS_RISK_CONCENTRATION_PARTIAL")

    inherited_constraints = {
        "batch_mode": "DRY_RUN_ONLY",
        "submit_allowed": False,
        "max_submit_count": 0,
        "max_dry_run_candidates_cap": 5,
        "no_exchange_write_calls": True,
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
        "eligible_for_repeat_dry_run": eligible,
        "batch_mode": "DRY_RUN_ONLY",
        "submit_allowed": False,
        "max_dry_run_candidates": min(max(max_dry, 0), 5) if eligible else 0,
        "inherited_constraints": inherited_constraints,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "next_actions": (
            ["REFRESH_CANDIDATES_FOR_REPEAT_DRY_RUN", "GENERATE_REPEAT_EXECUTION_PLAN"]
            if eligible
            else ["REVIEW_AND_FIX_REPEAT_DRY_RUN_BLOCKERS"]
        ),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate repeat small batch dry-run eligibility packet")
    parser.add_argument("--small-batch-review-phase-json", required=True)
    parser.add_argument("--previous-risk-concentration-json")
    parser.add_argument("--previous-result-aggregate-json")
    parser.add_argument("--output-json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = generate_packet(
        load_json(args.small_batch_review_phase_json),
        load_json(args.previous_risk_concentration_json) if args.previous_risk_concentration_json else None,
        load_json(args.previous_result_aggregate_json) if args.previous_result_aggregate_json else None,
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
