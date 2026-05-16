#!/usr/bin/env python3
import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional

PHASE = "final_pre_testnet_submit_control"
FORBIDDEN_NEXT_ACTIONS = [
    "EXCHANGE_API_CALL",
    "TESTNET_SUBMIT",
    "REAL_SUBMIT",
    "SUBMIT_ORDER",
    "CANCEL_ORDER",
    "FLATTEN_POSITION",
]


def load_json(path: str) -> Optional[Dict[str, Any]]:
    if not os.path.exists(path):
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


def generate_phase_control(t491: Optional[Dict[str, Any]], t492: Optional[Dict[str, Any]], t493: Optional[Dict[str, Any]], t494: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    blockers: List[str] = []
    warnings: List[str] = []

    if t491 is None:
        blockers.append("T491_LOAD_FAILED")
    if t492 is None:
        blockers.append("T492_LOAD_FAILED")
    if t493 is None:
        blockers.append("T493_LOAD_FAILED")
    if t494 is None:
        blockers.append("T494_LOAD_FAILED")

    v491 = str((t491 or {}).get("verdict", ""))
    v492 = str((t492 or {}).get("verdict", ""))
    v493 = str((t493 or {}).get("verdict", ""))
    v494 = str((t494 or {}).get("verdict", ""))
    safe_partial_493 = bool((t493 or {}).get("safe_partial", False))

    pass_491 = v491 == "PASS"
    pass_492 = v492 == "PASS"
    pass_493 = v493 == "PASS" or (v493 == "PARTIAL" and safe_partial_493)
    pass_494 = v494 == "GO"

    if not pass_491:
        blockers.append("T491_NOT_PASS")
    if not pass_492:
        blockers.append("T492_NOT_PASS")
    if not pass_493:
        blockers.append("T493_NOT_SAFE")
    if not pass_494:
        blockers.append("T494_NOT_GO")

    if v493 == "PARTIAL" and safe_partial_493:
        warnings.append("T493_SAFE_PARTIAL_ACCEPTED_WITH_HUMAN_REVIEW")

    if pass_491 and pass_492 and pass_493 and pass_494:
        verdict = "PASS"
        ok = True
        allowed_next_phase = "TESTNET_SUBMIT_READINESS_REVIEW"
    else:
        hard_fail = (not pass_491) or (not pass_492) or (v494 == "NO_GO") or (v493 == "FAIL")
        if hard_fail:
            verdict = "FAIL"
        else:
            verdict = "PARTIAL"
        ok = False
        allowed_next_phase = "HUMAN_REVIEW_REQUIRED"

    component_verdicts = {
        "T491": v491,
        "T492": v492,
        "T493": v493,
        "T494": v494,
    }

    return {
        "ok": ok,
        "verdict": verdict,
        "phase": PHASE,
        "component_verdicts": component_verdicts,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "allowed_next_phase": allowed_next_phase,
        "forbidden_next_actions": FORBIDDEN_NEXT_ACTIONS,
        "required_human_decision": "APPROVE_OR_REJECT_TESTNET_SUBMIT_READINESS_REVIEW_ENTRY",
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate final pre-submit phase control report")
    parser.add_argument("--inputs", nargs=4, metavar=("T491", "T492", "T493", "T494"), required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = generate_phase_control(
        load_json(args.inputs[0]),
        load_json(args.inputs[1]),
        load_json(args.inputs[2]),
        load_json(args.inputs[3]),
    )

    if not write_json(args.output, report):
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
