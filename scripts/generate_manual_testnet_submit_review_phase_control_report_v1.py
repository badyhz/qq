#!/usr/bin/env python3
import argparse
import json
import os
import sys
from typing import Any, Dict, Optional

PHASE = "MANUAL_TESTNET_SUBMIT_REVIEW_ONLY"


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


def generate_report(
    review_eligibility: Optional[Dict[str, Any]],
    candidate_review: Optional[Dict[str, Any]],
    checklist: Optional[Dict[str, Any]],
    review_score: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    blockers = []
    warnings = []

    payloads = [review_eligibility, candidate_review, checklist, review_score]
    if any(not isinstance(p, dict) for p in payloads):
        blockers.append("REQUIRED_INPUT_MISSING_OR_MALFORMED")

    verdicts = [
        str((review_eligibility or {}).get("verdict", "")),
        str((candidate_review or {}).get("verdict", "")),
        str((checklist or {}).get("verdict", "")),
        str((review_score or {}).get("verdict", "")),
    ]
    score_decision = str((review_score or {}).get("decision", ""))

    if bool((review_eligibility or {}).get("submit_allowed") is True) or bool((candidate_review or {}).get("submit_allowed") is True):
        blockers.append("SUBMIT_ALLOWED_TRUE_NOT_PERMITTED")

    if blockers or any(v == "FAIL" for v in verdicts):
        verdict = "FAIL"
        decision = "STOP"
        can_continue = False
    elif all(v == "PASS" for v in verdicts) and score_decision == "READY_FOR_SINGLE_MANUAL_SUBMIT_PACKET":
        verdict = "PASS"
        decision = "ALLOW_SINGLE_MANUAL_SUBMIT_PACKET_GENERATION"
        can_continue = True
    elif any(v == "PARTIAL" for v in verdicts):
        verdict = "PARTIAL"
        if score_decision == "REVIEW_MORE_DRY_RUN":
            decision = "REPEAT_SMALL_BATCH_DRY_RUN"
        else:
            decision = "REVIEW"
        can_continue = False
    else:
        verdict = "PARTIAL"
        decision = "REVIEW"
        can_continue = False

    return {
        "ok": verdict == "PASS",
        "verdict": verdict,
        "phase": PHASE,
        "decision": decision,
        "can_continue": can_continue,
        "submit_allowed": False,
        "max_submit_count": 0,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "required_next_actions": (
            ["GENERATE_SINGLE_MANUAL_SUBMIT_PACKET_REVIEW"]
            if decision == "ALLOW_SINGLE_MANUAL_SUBMIT_PACKET_GENERATION"
            else ["CONTINUE_REVIEW_ONLY_FLOW"]
        ),
        "next_task_recommendation": (
            "single_manual_submit_packet_generation_review"
            if decision == "ALLOW_SINGLE_MANUAL_SUBMIT_PACKET_GENERATION"
            else "manual_review_or_repeat_dry_run"
        ),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate manual testnet submit review phase control report")
    parser.add_argument("--review-eligibility-json", required=True)
    parser.add_argument("--candidate-review-json", required=True)
    parser.add_argument("--risk-acceptance-checklist-json", required=True)
    parser.add_argument("--review-score-json", required=True)
    parser.add_argument("--output-json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = generate_report(
        load_json(args.review_eligibility_json),
        load_json(args.candidate_review_json),
        load_json(args.risk_acceptance_checklist_json),
        load_json(args.review_score_json),
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
