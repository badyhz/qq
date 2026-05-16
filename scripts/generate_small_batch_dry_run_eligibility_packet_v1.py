#!/usr/bin/env python3
import argparse
import json
import os
import sys
from typing import Any, Dict, Optional


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


def generate_eligibility(three_consistency: Optional[Dict[str, Any]], third_evidence: Optional[Dict[str, Any]], third_incident: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    blockers = []
    warnings = []

    if three_consistency is None:
        blockers.append("THREE_SUBMIT_CONSISTENCY_MISSING")
    if third_evidence is None:
        blockers.append("THIRD_EVIDENCE_MISSING")
    if third_incident is None:
        blockers.append("THIRD_INCIDENT_MISSING")

    c_verdict = str((three_consistency or {}).get("verdict", ""))
    e_verdict = str((third_evidence or {}).get("verdict", ""))
    i_verdict = str((third_incident or {}).get("verdict", ""))
    i_level = str((third_incident or {}).get("incident_level", ""))

    if c_verdict == "FAIL":
        blockers.append("THREE_SUBMIT_CONSISTENCY_FAIL")
    if c_verdict == "PARTIAL":
        warnings.append("THREE_SUBMIT_CONSISTENCY_PARTIAL")

    if e_verdict != "PASS":
        blockers.append("THIRD_EVIDENCE_NOT_PASS")

    if not (i_verdict == "PASS" or i_level == "NONE"):
        blockers.append("THIRD_INCIDENT_NOT_SAFE")

    if blockers:
        verdict = "FAIL"
        ok = False
        eligible = False
        max_candidates = 0
    elif warnings:
        verdict = "PARTIAL"
        ok = False
        eligible = False
        max_candidates = 0
    else:
        verdict = "PASS"
        ok = True
        eligible = True
        max_candidates = 5

    if max_candidates > 5:
        max_candidates = 5

    return {
        "ok": ok,
        "verdict": verdict,
        "eligible_for_small_batch_dry_run": eligible,
        "batch_mode": "DRY_RUN_ONLY",
        "max_dry_run_candidates": max_candidates,
        "submit_allowed": False,
        "inherited_constraints": {
            "manual_submit_still_required": True,
            "no_auto_submit": True,
            "no_exchange_write_calls": True,
        },
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "next_actions": (
            ["START_SMALL_BATCH_DRY_RUN_CANDIDATE_GENERATION"]
            if eligible
            else ["REVIEW_AND_FIX_BLOCKERS"]
        ),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate small batch dry-run eligibility packet")
    parser.add_argument("--three-submit-consistency-json", required=True)
    parser.add_argument("--third-evidence-json", required=True)
    parser.add_argument("--third-incident-json", required=True)
    parser.add_argument("--output-json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = generate_eligibility(
        load_json(args.three_submit_consistency_json),
        load_json(args.third_evidence_json),
        load_json(args.third_incident_json),
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
