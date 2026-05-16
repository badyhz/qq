#!/usr/bin/env python3
import argparse
import json
import os
import sys
from typing import Any, Dict, Optional

PHASE = "REPEAT_SMALL_BATCH_DRY_RUN_REVIEW"


def load_json(path: str) -> Optional[Dict[str, Any]]:
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


def generate_report(
    repeat_eligibility: Optional[Dict[str, Any]],
    candidate_refresh: Optional[Dict[str, Any]],
    plan_comparator: Optional[Dict[str, Any]],
    result_stability: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    blockers = []
    warnings = []

    if repeat_eligibility is None:
        blockers.append("REPEAT_ELIGIBILITY_MISSING")
    if candidate_refresh is None:
        blockers.append("CANDIDATE_REFRESH_MISSING")
    if plan_comparator is None:
        blockers.append("PLAN_COMPARATOR_MISSING")
    if result_stability is None:
        blockers.append("RESULT_STABILITY_MISSING")

    verdicts = [
        str((repeat_eligibility or {}).get("verdict", "")),
        str((candidate_refresh or {}).get("verdict", "")),
        str((plan_comparator or {}).get("verdict", "")),
        str((result_stability or {}).get("verdict", "")),
    ]

    if blockers or any(v == "FAIL" for v in verdicts):
        verdict = "FAIL"
        decision = "STOP"
        can_continue = False
        max_dry = 0
    elif all(v == "PASS" for v in verdicts):
        verdict = "PASS"
        decision = "ALLOW_ANOTHER_SMALL_BATCH_DRY_RUN"
        can_continue = True
        max_dry = min(5, int((repeat_eligibility or {}).get("max_dry_run_candidates", 0) or 0))
        if max_dry <= 0:
            max_dry = 5
    else:
        verdict = "PARTIAL"
        decision = "REVIEW"
        can_continue = False
        max_dry = 0

    # keep unreachable by default; only review packet concept
    if decision == "ALLOW_MANUAL_TESTNET_SUBMIT_REVIEW_ONLY":
        warnings.append("MANUAL_SUBMIT_REVIEW_ONLY_DECISION_EMITTED")

    submit_allowed = False
    max_submit_count = 0

    if verdict == "PASS":
        required_next_actions = ["RUN_ANOTHER_SMALL_BATCH_DRY_RUN_ONLY", "KEEP_SUBMIT_DISABLED"]
        next_task = "REPEAT_SMALL_BATCH_DRY_RUN_EXECUTION"
    elif verdict == "PARTIAL":
        required_next_actions = ["REVIEW_PARTIAL_FINDINGS", "COLLECT_MORE_DRY_RUN_EVIDENCE"]
        next_task = "REPEAT_SMALL_BATCH_DRY_RUN_REVIEW_REMEDIATION"
    else:
        required_next_actions = ["STOP_AND_REVIEW_BLOCKERS", "DO_NOT_SUBMIT"]
        next_task = "REPEAT_SMALL_BATCH_DRY_RUN_STOP_REMEDIATION"

    return {
        "ok": verdict == "PASS",
        "verdict": verdict,
        "phase": PHASE,
        "decision": decision,
        "can_continue": can_continue,
        "submit_allowed": submit_allowed,
        "max_submit_count": max_submit_count,
        "max_dry_run_candidates": max_dry,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "required_next_actions": required_next_actions,
        "next_task_recommendation": next_task,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate repeat small batch dry-run phase control report")
    parser.add_argument("--repeat-eligibility-json", required=True)
    parser.add_argument("--candidate-refresh-json", required=True)
    parser.add_argument("--plan-comparator-json", required=True)
    parser.add_argument("--result-stability-json", required=True)
    parser.add_argument("--output-json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = generate_report(
        load_json(args.repeat_eligibility_json),
        load_json(args.candidate_refresh_json),
        load_json(args.plan_comparator_json),
        load_json(args.result_stability_json),
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
