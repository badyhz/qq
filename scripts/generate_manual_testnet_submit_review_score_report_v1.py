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


def generate_score(
    review_eligibility: Optional[Dict[str, Any]],
    candidate_review: Optional[Dict[str, Any]],
    checklist: Optional[Dict[str, Any]],
    result_stability: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    blockers = []
    warnings = []

    inputs = {
        "review_eligibility": review_eligibility,
        "candidate_review": candidate_review,
        "risk_acceptance_checklist": checklist,
        "result_stability": result_stability,
    }

    for name, payload in inputs.items():
        if not isinstance(payload, dict):
            blockers.append(f"{name.upper()}_MISSING")

    if blockers:
        return {
            "ok": False,
            "verdict": "FAIL",
            "review_score": 0,
            "score_components": {},
            "decision": "BLOCK",
            "submit_allowed": False,
            "max_submit_count": 0,
            "blockers": sorted(set(blockers)),
            "warnings": warnings,
            "rationale": "missing required input",
        }

    score = 100
    score_components = {
        "base": 100,
        "partial_penalty": 0,
        "high_concentration_penalty": 0,
        "stability_drift_penalty": 0,
        "missing_preferred_candidate_cap": None,
        "fail_input_cap": None,
    }

    verdicts = [
        str(review_eligibility.get("verdict", "")),
        str(candidate_review.get("verdict", "")),
        str(checklist.get("verdict", "")),
        str(result_stability.get("verdict", "")),
    ]

    if any(v == "FAIL" for v in verdicts):
        score = min(score, 40)
        score_components["fail_input_cap"] = 40

    if any(v == "PARTIAL" for v in verdicts):
        score -= 20
        score_components["partial_penalty"] = 20

    c_warnings = candidate_review.get("warnings") if isinstance(candidate_review.get("warnings"), list) else []
    if any("HIGH_CONCENTRATION" in str(w) for w in c_warnings):
        score -= 15
        score_components["high_concentration_penalty"] = 15

    s_warnings = result_stability.get("warnings") if isinstance(result_stability.get("warnings"), list) else []
    if any("DRIFT" in str(w) for w in s_warnings):
        score -= 15
        score_components["stability_drift_penalty"] = 15

    preferred = candidate_review.get("preferred_candidate")
    if not isinstance(preferred, dict) or not preferred:
        score = min(score, 50)
        score_components["missing_preferred_candidate_cap"] = 50

    if score < 0:
        score = 0

    if bool(review_eligibility.get("submit_allowed") is True) or bool(candidate_review.get("submit_allowed") is True):
        blockers.append("SUBMIT_ALLOWED_TRUE_NOT_PERMITTED")

    if blockers:
        verdict = "FAIL"
        decision = "BLOCK"
        ok = False
    elif score >= 85:
        verdict = "PASS"
        decision = "READY_FOR_SINGLE_MANUAL_SUBMIT_PACKET"
        ok = True
    elif score >= 60:
        verdict = "PARTIAL"
        decision = "REVIEW_MORE_DRY_RUN"
        ok = False
    else:
        verdict = "FAIL"
        decision = "BLOCK"
        ok = False

    return {
        "ok": ok,
        "verdict": verdict,
        "review_score": score,
        "score_components": score_components,
        "decision": decision,
        "submit_allowed": False,
        "max_submit_count": 0,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "rationale": "manual-submit review-only scoring",
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate manual testnet submit review score report")
    parser.add_argument("--review-eligibility-json", required=True)
    parser.add_argument("--candidate-review-json", required=True)
    parser.add_argument("--risk-acceptance-checklist-json", required=True)
    parser.add_argument("--result-stability-json", required=True)
    parser.add_argument("--output-json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = generate_score(
        load_json(args.review_eligibility_json),
        load_json(args.candidate_review_json),
        load_json(args.risk_acceptance_checklist_json),
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
