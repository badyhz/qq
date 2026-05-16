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
    repeat_phase: Optional[Dict[str, Any]],
    result_stability: Optional[Dict[str, Any]] = None,
    plan_comparator: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    blockers = []
    warnings = []

    if repeat_phase is None:
        blockers.append("REPEAT_PHASE_MALFORMED_OR_MISSING")
        repeat_phase = {}

    decision = str(repeat_phase.get("decision", ""))
    submit_allowed_in = bool(repeat_phase.get("submit_allowed") is True)
    max_submit_count_in = int(repeat_phase.get("max_submit_count", -1))

    if decision not in ["ALLOW_ANOTHER_SMALL_BATCH_DRY_RUN", "ALLOW_MANUAL_TESTNET_SUBMIT_REVIEW_ONLY"]:
        blockers.append("REPEAT_PHASE_DECISION_NOT_ALLOWED_FOR_REVIEW")
    if submit_allowed_in:
        blockers.append("REPEAT_PHASE_SUBMIT_ALLOWED_TRUE")
    if max_submit_count_in != 0:
        blockers.append("REPEAT_PHASE_MAX_SUBMIT_COUNT_NOT_ZERO")

    if result_stability is not None:
        rs_v = str(result_stability.get("verdict", ""))
        if rs_v == "FAIL":
            blockers.append("RESULT_STABILITY_FAIL")
        elif rs_v == "PARTIAL":
            warnings.append("RESULT_STABILITY_PARTIAL")

    if plan_comparator is not None:
        pc_v = str(plan_comparator.get("verdict", ""))
        if pc_v == "FAIL":
            blockers.append("PLAN_COMPARATOR_FAIL")
        elif pc_v == "PARTIAL":
            warnings.append("PLAN_COMPARATOR_PARTIAL")

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

    inherited_constraints = {
        "review_mode": "REVIEW_ONLY",
        "submit_allowed": False,
        "max_submit_count": 0,
        "no_submit_commands": True,
        "no_exchange_write_calls": True,
    }

    return {
        "ok": ok,
        "verdict": verdict,
        "eligible_for_manual_submit_review": eligible,
        "review_mode": "REVIEW_ONLY",
        "submit_allowed": False,
        "max_submit_count": 0,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "inherited_constraints": inherited_constraints,
        "next_actions": (
            ["BUILD_MANUAL_REVIEW_CANDIDATE_PACKET"]
            if eligible
            else ["REVIEW_STABILITY_AND_PLAN_GAPS"]
        ),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate manual testnet submit review eligibility packet")
    parser.add_argument("--repeat-small-batch-phase-json", required=True)
    parser.add_argument("--result-stability-json")
    parser.add_argument("--plan-comparator-json")
    parser.add_argument("--output-json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = generate_packet(
        load_json(args.repeat_small_batch_phase_json),
        load_json(args.result_stability_json) if args.result_stability_json else None,
        load_json(args.plan_comparator_json) if args.plan_comparator_json else None,
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
