#!/usr/bin/env python3
import argparse
import json
import os
import sys
from typing import Any, Dict, Optional

PHASE = "SMALL_BATCH_DRY_RUN_ENTRY"


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


def generate_phase_control(eligibility: Optional[Dict[str, Any]], consistency: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    blockers = []
    warnings = []

    if eligibility is None:
        blockers.append("SMALL_BATCH_ELIGIBILITY_MISSING")
    if consistency is None:
        blockers.append("THREE_SUBMIT_CONSISTENCY_MISSING")

    e_verdict = str((eligibility or {}).get("verdict", ""))
    c_verdict = str((consistency or {}).get("verdict", ""))

    if blockers or e_verdict == "FAIL" or c_verdict == "FAIL":
        verdict = "FAIL"
        decision = "STOP"
        can_continue = False
        max_dry = 0
    elif e_verdict == "PASS" and c_verdict == "PASS":
        verdict = "PASS"
        decision = "ALLOW_SMALL_BATCH_DRY_RUN_ONLY"
        can_continue = True
        max_dry = min(5, int((eligibility or {}).get("max_dry_run_candidates", 0) or 0))
        if max_dry <= 0:
            max_dry = 5
    else:
        verdict = "PARTIAL"
        decision = "REVIEW"
        can_continue = False
        max_dry = 0

    submit_allowed = False
    max_submit_count = 0

    if max_dry > 5:
        max_dry = 5

    if verdict == "PASS":
        required_next = ["RUN_SMALL_BATCH_DRY_RUN_ONLY", "KEEP_MANUAL_SUBMIT_GATES"]
        next_task = "SMALL_BATCH_DRY_RUN_CANDIDATE_PIPELINE"
    elif verdict == "PARTIAL":
        required_next = ["REVIEW_PARTIAL_FINDINGS", "COLLECT_MISSING_ARTIFACTS"]
        next_task = "SMALL_BATCH_DRY_RUN_REVIEW_REMEDIATION"
    else:
        required_next = ["STOP_AND_MANUAL_REVIEW", "FIX_BLOCKERS"]
        next_task = "SMALL_BATCH_ENTRY_BLOCKER_REMEDIATION"

    return {
        "ok": verdict == "PASS",
        "verdict": verdict,
        "phase": PHASE,
        "decision": decision,
        "can_continue": can_continue,
        "submit_allowed": submit_allowed,
        "max_dry_run_candidates": max_dry,
        "max_submit_count": max_submit_count,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "required_next_actions": required_next,
        "next_task_recommendation": next_task,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate small batch dry-run phase control report")
    parser.add_argument("--small-batch-eligibility-json", required=True)
    parser.add_argument("--three-submit-consistency-json", required=True)
    parser.add_argument("--output-json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = generate_phase_control(load_json(args.small_batch_eligibility_json), load_json(args.three_submit_consistency_json))

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
