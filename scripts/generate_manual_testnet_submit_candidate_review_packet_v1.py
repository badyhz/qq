#!/usr/bin/env python3
import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional


def load_json(path: str) -> Optional[Any]:
    if not path or not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def write_json(path: str, data: Dict[str, Any]) -> bool:
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, sort_keys=True, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def _is_testnet_url(url: Any) -> bool:
    if not isinstance(url, str):
        return False
    lower = url.lower()
    if "api.binance.com" in lower or "mainnet" in lower or "live" in lower:
        return False
    return "testnet" in lower or "demo" in lower


def generate_review(
    review_eligibility: Optional[Dict[str, Any]],
    candidate_selection: Optional[Dict[str, Any]],
    risk_concentration: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    blockers = []
    warnings = []
    reviewed_candidates: List[Dict[str, Any]] = []
    rejected_candidates: List[Dict[str, Any]] = []
    preferred_candidate = None

    if not isinstance(review_eligibility, dict):
        blockers.append("REVIEW_ELIGIBILITY_MISSING")
        review_eligibility = {}
    if not isinstance(candidate_selection, dict):
        blockers.append("CANDIDATE_SELECTION_MISSING")
        candidate_selection = {}

    e_verdict = str(review_eligibility.get("verdict", ""))
    if e_verdict not in ["PASS", "PARTIAL"]:
        blockers.append("REVIEW_ELIGIBILITY_NOT_PASS_OR_PARTIAL")

    if bool(review_eligibility.get("submit_allowed") is True):
        blockers.append("REVIEW_ELIGIBILITY_SUBMIT_ALLOWED_TRUE")

    candidates = candidate_selection.get("selected_candidates")
    if not isinstance(candidates, list):
        blockers.append("SELECTED_CANDIDATES_MALFORMED")
        candidates = []

    for c in candidates:
        if not isinstance(c, dict):
            rejected_candidates.append({"candidate": c, "reason": "MALFORMED_CANDIDATE"})
            continue
        env = str(c.get("env", "")).lower()
        symbol = c.get("symbol")
        side = c.get("side")
        qty = c.get("quantity")
        base_url = c.get("base_url")

        if env != "testnet":
            rejected_candidates.append({"candidate": c, "reason": "ENV_NOT_TESTNET"})
            continue
        if not _is_testnet_url(base_url):
            blockers.append("MAINNET_OR_LIVE_MARKER_DETECTED")
            rejected_candidates.append({"candidate": c, "reason": "BASE_URL_NOT_TESTNET"})
            continue
        if not symbol or side not in ["BUY", "SELL"] or qty in [None, "", 0, 0.0, "0"]:
            rejected_candidates.append({"candidate": c, "reason": "MISSING_REQUIRED_FIELDS"})
            continue

        reviewed_candidates.append(c)

    if len(reviewed_candidates) > 5:
        reviewed_candidates = reviewed_candidates[:5]
        warnings.append("CANDIDATE_COUNT_CAPPED_AT_FIVE")

    concentration_status = str((risk_concentration or {}).get("concentration_status", "")) if isinstance(risk_concentration, dict) else ""
    if concentration_status == "UNSAFE":
        blockers.append("RISK_CONCENTRATION_UNSAFE")
    elif concentration_status == "HIGH":
        warnings.append("HIGH_CONCENTRATION_WARNING")

    if reviewed_candidates:
        preferred_candidate = reviewed_candidates[0]

    if blockers:
        verdict = "FAIL"
        ok = False
    elif e_verdict == "PARTIAL" or concentration_status == "HIGH":
        verdict = "PARTIAL"
        ok = True
    elif preferred_candidate is not None and e_verdict == "PASS":
        verdict = "PASS"
        ok = True
    else:
        verdict = "FAIL"
        ok = False
        blockers.append("NO_SAFE_PREFERRED_CANDIDATE")

    return {
        "ok": ok,
        "verdict": verdict,
        "review_mode": "REVIEW_ONLY",
        "submit_allowed": False,
        "candidate_count": len(reviewed_candidates),
        "reviewed_candidates": reviewed_candidates,
        "preferred_candidate": preferred_candidate,
        "rejected_candidates": rejected_candidates,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "rationale": "manual_submit_review_candidate_quality",
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate manual testnet submit candidate review packet")
    parser.add_argument("--review-eligibility-json", required=True)
    parser.add_argument("--candidate-selection-json", required=True)
    parser.add_argument("--risk-concentration-json")
    parser.add_argument("--output-json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = generate_review(
        load_json(args.review_eligibility_json),
        load_json(args.candidate_selection_json),
        load_json(args.risk_concentration_json) if args.risk_concentration_json else None,
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
