#!/usr/bin/env python3
import argparse
import json
import os
import sys
from typing import Any, Dict, Optional

PHASE = "SECOND_TESTNET_SUBMIT_REVIEW"


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


def generate_phase_report(
    eligibility: Optional[Dict[str, Any]],
    command_packet: Optional[Dict[str, Any]],
    repeatability: Optional[Dict[str, Any]],
    safety_score: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    blockers = []
    warnings = []

    if eligibility is None:
        blockers.append("ELIGIBILITY_INPUT_MISSING")
    if command_packet is None:
        blockers.append("COMMAND_PACKET_INPUT_MISSING")
    if repeatability is None:
        blockers.append("REPEATABILITY_INPUT_MISSING")
    if safety_score is None:
        blockers.append("SAFETY_SCORE_INPUT_MISSING")

    if blockers:
        return {
            "ok": False,
            "verdict": "FAIL",
            "phase": PHASE,
            "decision": "STOP",
            "can_continue": False,
            "can_submit_again": False,
            "max_next_submit_count": 0,
            "blockers": sorted(set(blockers)),
            "warnings": warnings,
            "required_next_actions": ["FIX_INPUT_ARTIFACTS"],
            "next_task_recommendation": "REBUILD_SECOND_SUBMIT_REVIEW_CHAIN",
        }

    ev = str(eligibility.get("verdict", ""))
    cv = str(command_packet.get("verdict", ""))
    rv = str(repeatability.get("verdict", ""))
    sv = str(safety_score.get("verdict", ""))

    if ev == "FAIL" or cv == "FAIL" or rv == "FAIL" or sv == "FAIL":
        verdict = "FAIL"
        decision = "STOP"
        can_continue = False
        required_next = ["STOP_SUBMIT_FLOW", "MANUAL_INCIDENT_REVIEW"]
    elif rv == "PASS" and sv == "PASS":
        verdict = "PASS"
        decision = "ALLOW_THIRD_MANUAL_TESTNET_SUBMIT"
        can_continue = True
        required_next = ["KEEP_SINGLE_SUBMIT_LIMIT", "REQUIRE_MANUAL_TOKEN_GATE"]
    elif rv == "PARTIAL" or sv == "PARTIAL" or ev == "PARTIAL" or cv == "PARTIAL":
        verdict = "PARTIAL"
        decision = "REVIEW"
        can_continue = False
        required_next = ["MANUAL_REVIEW", "COLLECT_MORE_EVIDENCE"]
    else:
        verdict = "PARTIAL"
        decision = "REVIEW"
        can_continue = False
        required_next = ["REVIEW_CHAIN_STATE"]

    can_submit_again = decision == "ALLOW_THIRD_MANUAL_TESTNET_SUBMIT"
    max_next_submit_count = 1 if can_submit_again else 0

    if max_next_submit_count > 1:
        blockers.append("MAX_NEXT_SUBMIT_COUNT_EXCEEDS_ONE")
        verdict = "FAIL"
        decision = "STOP"
        can_continue = False
        can_submit_again = False
        max_next_submit_count = 0

    if not can_submit_again:
        warnings.append("NO_AUTO_REPEAT_SUBMIT")

    next_task = (
        "THIRD_MANUAL_TESTNET_SUBMIT_GATE" if can_submit_again else "SECOND_SUBMIT_REVIEW_REMEDIATION"
    )

    return {
        "ok": verdict == "PASS",
        "verdict": verdict,
        "phase": PHASE,
        "decision": decision,
        "can_continue": can_continue,
        "can_submit_again": can_submit_again,
        "max_next_submit_count": max_next_submit_count,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "required_next_actions": required_next,
        "next_task_recommendation": next_task,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate second testnet submit phase control report")
    parser.add_argument("--eligibility-json", required=True)
    parser.add_argument("--command-packet-json", required=True)
    parser.add_argument("--repeatability-json", required=True)
    parser.add_argument("--safety-score-json", required=True)
    parser.add_argument("--output-json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = generate_phase_report(
        load_json(args.eligibility_json),
        load_json(args.command_packet_json),
        load_json(args.repeatability_json),
        load_json(args.safety_score_json),
    )

    if args.output_json:
        if not write_json(args.output_json, report):
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
