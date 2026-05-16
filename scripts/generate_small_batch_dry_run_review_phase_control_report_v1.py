#!/usr/bin/env python3
import argparse
import json
import os
import sys
from typing import Any, Dict, Optional

PHASE = "SMALL_BATCH_DRY_RUN_REVIEW"


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


def generate_report(selection: Optional[Dict[str, Any]], execution: Optional[Dict[str, Any]], aggregate: Optional[Dict[str, Any]], concentration: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    blockers = []
    warnings = []

    if selection is None:
        blockers.append("CANDIDATE_SELECTION_MISSING")
    if execution is None:
        blockers.append("EXECUTION_PLAN_MISSING")
    if aggregate is None:
        blockers.append("RESULT_AGGREGATE_MISSING")
    if concentration is None:
        blockers.append("RISK_CONCENTRATION_MISSING")

    verdicts = [
        str((selection or {}).get("verdict", "")),
        str((execution or {}).get("verdict", "")),
        str((aggregate or {}).get("verdict", "")),
        str((concentration or {}).get("verdict", "")),
    ]

    concentration_status = str((concentration or {}).get("concentration_status", ""))

    if any(v == "FAIL" for v in verdicts) or blockers:
        verdict = "FAIL"
        decision = "STOP"
        can_continue = False
        max_dry = 0
    elif any(v == "PARTIAL" for v in verdicts):
        verdict = "PARTIAL"
        decision = "REVIEW"
        can_continue = False
        max_dry = 0
    elif concentration_status in ["LOW", "MEDIUM"]:
        verdict = "PASS"
        decision = "ALLOW_REPEAT_SMALL_BATCH_DRY_RUN"
        can_continue = True
        max_dry = min(5, int((selection or {}).get("max_dry_run_candidates", 0) or 0))
        if max_dry <= 0:
            max_dry = 5
    elif concentration_status == "HIGH":
        verdict = "PARTIAL"
        decision = "REVIEW"
        can_continue = False
        max_dry = 0
    else:
        verdict = "PARTIAL"
        decision = "REVIEW"
        can_continue = False
        max_dry = 0

    submit_allowed = False
    max_submit_count = 0

    # dead decision: never emitted by default
    if decision == "ALLOW_ONE_MORE_MANUAL_TESTNET_SUBMIT":
        blockers.append("DEAD_DECISION_SHOULD_NOT_BE_EMITTED")
        verdict = "FAIL"
        decision = "STOP"
        can_continue = False
        max_dry = 0

    if verdict == "PASS":
        required_next = ["RUN_NEXT_SMALL_BATCH_DRY_RUN_ONLY", "KEEP_SUBMIT_DISABLED"]
        next_task = "SMALL_BATCH_DRY_RUN_REPEAT_VALIDATION"
    elif verdict == "PARTIAL":
        required_next = ["MANUAL_REVIEW_CONCENTRATION_OR_PARTIALS", "ADJUST_BATCH_INPUTS"]
        next_task = "SMALL_BATCH_DRY_RUN_REVIEW_REMEDIATION"
    else:
        required_next = ["STOP_BATCH", "FIX_BLOCKERS"]
        next_task = "SMALL_BATCH_DRY_RUN_STOP_REMEDIATION"

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
        "required_next_actions": required_next,
        "next_task_recommendation": next_task,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate small batch dry-run review phase control report")
    parser.add_argument("--candidate-selection-json", required=True)
    parser.add_argument("--execution-plan-json", required=True)
    parser.add_argument("--result-aggregate-json", required=True)
    parser.add_argument("--risk-concentration-json", required=True)
    parser.add_argument("--output-json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = generate_report(
        load_json(args.candidate_selection_json),
        load_json(args.execution_plan_json),
        load_json(args.result_aggregate_json),
        load_json(args.risk_concentration_json),
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
