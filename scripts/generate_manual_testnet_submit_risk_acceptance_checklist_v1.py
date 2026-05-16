#!/usr/bin/env python3
import argparse
import json
import os
import sys
from typing import Any, Dict, Optional

REQUIRED_HUMAN_CHECKS = [
    "confirm env=testnet",
    "confirm symbol/side/quantity",
    "confirm protection SL/TP plan",
    "confirm dry-run result PASS",
    "confirm no naked/orphan protection",
    "confirm no mainnet/live marker",
]


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


def generate_checklist(
    candidate_review: Optional[Dict[str, Any]],
    result_stability: Optional[Dict[str, Any]],
    three_submit_consistency: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    blockers = []
    warnings = []

    if not isinstance(candidate_review, dict):
        blockers.append("CANDIDATE_REVIEW_MISSING")
        candidate_review = {}
    if not isinstance(result_stability, dict):
        blockers.append("RESULT_STABILITY_MISSING")
        result_stability = {}

    c_verdict = str(candidate_review.get("verdict", ""))
    s_verdict = str(result_stability.get("verdict", ""))

    if bool(candidate_review.get("submit_allowed") is True):
        blockers.append("CANDIDATE_REVIEW_SUBMIT_ALLOWED_TRUE")

    if isinstance(three_submit_consistency, dict) and str(three_submit_consistency.get("verdict", "")) == "FAIL":
        blockers.append("THREE_SUBMIT_CONSISTENCY_FAIL")

    if c_verdict == "FAIL" or s_verdict == "FAIL":
        blockers.append("INPUT_VERDICT_FAIL")

    automatic_checks = {
        "candidate_review_pass": c_verdict == "PASS",
        "result_stability_pass": s_verdict == "PASS",
        "no_blockers": len(blockers) == 0,
        "submit_allowed_false": True,
        "max_submit_count_zero": True,
    }

    if blockers:
        verdict = "FAIL"
        ok = False
        checklist_status = "BLOCKED"
    elif c_verdict == "PASS" and s_verdict == "PASS":
        verdict = "PASS"
        ok = True
        checklist_status = "READY_FOR_HUMAN_REVIEW"
    else:
        verdict = "PARTIAL"
        ok = True
        checklist_status = "NEEDS_REVIEW"

    return {
        "ok": ok,
        "verdict": verdict,
        "checklist_status": checklist_status,
        "submit_allowed": False,
        "max_submit_count": 0,
        "required_human_checks": REQUIRED_HUMAN_CHECKS,
        "automatic_checks": automatic_checks,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "acceptance_notes": "review-only packet; no submit command generated",
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate manual testnet submit risk acceptance checklist")
    parser.add_argument("--candidate-review-json", required=True)
    parser.add_argument("--result-stability-json", required=True)
    parser.add_argument("--three-submit-consistency-json")
    parser.add_argument("--output-json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = generate_checklist(
        load_json(args.candidate_review_json),
        load_json(args.result_stability_json),
        load_json(args.three_submit_consistency_json) if args.three_submit_consistency_json else None,
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
