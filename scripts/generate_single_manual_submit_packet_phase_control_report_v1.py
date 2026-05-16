#!/usr/bin/env python3
import argparse
import json
import os
import sys
from typing import Any, Dict, Optional


PHASE = "SINGLE_MANUAL_SUBMIT_PACKET_GENERATION"


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


def generate_phase_report(
    eligibility: Optional[Dict[str, Any]],
    single_packet: Optional[Dict[str, Any]],
    preflight: Optional[Dict[str, Any]],
    token_packet: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    warnings = []
    blockers = []

    payloads = {
        "eligibility": eligibility,
        "single_packet": single_packet,
        "preflight": preflight,
        "token_packet": token_packet,
    }
    for name, value in payloads.items():
        if not isinstance(value, dict):
            blockers.append(f"{name.upper()}_MISSING")

    verdicts = [str((v or {}).get("verdict", "")) for v in payloads.values()]

    if any(bool((v or {}).get("submit_allowed") is True) for v in payloads.values()):
        blockers.append("SUBMIT_ALLOWED_TRUE_NOT_PERMITTED")

    max_submit_count = 1

    if blockers or any(v == "FAIL" for v in verdicts):
        verdict = "FAIL"
        decision = "STOP"
        ok = False
        can_continue = False
    elif any(v == "PARTIAL" for v in verdicts):
        verdict = "PARTIAL"
        decision = "REVIEW"
        ok = False
        can_continue = False
    else:
        verdict = "PASS"
        decision = "READY_FOR_HUMAN_MANUAL_TESTNET_SUBMIT"
        ok = True
        can_continue = True

    return {
        "ok": ok,
        "verdict": verdict,
        "phase": PHASE,
        "decision": decision,
        "can_continue": can_continue,
        "submit_allowed": False,
        "max_submit_count": max_submit_count,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "required_next_actions": (
            ["HUMAN_REVIEW_AND_TOKEN_CONFIRMATION"]
            if decision == "READY_FOR_HUMAN_MANUAL_TESTNET_SUBMIT"
            else ["RESOLVE_PACKET_REVIEW_GAPS"]
        ),
        "next_task_recommendation": (
            "human_gated_execution_wrapper_review"
            if decision == "READY_FOR_HUMAN_MANUAL_TESTNET_SUBMIT"
            else "manual_submit_packet_review"
        ),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate single manual submit packet phase control report")
    parser.add_argument("--packet-eligibility-json", required=True)
    parser.add_argument("--single-submit-packet-json", required=True)
    parser.add_argument("--preflight-invariant-json", required=True)
    parser.add_argument("--human-token-packet-json", required=True)
    parser.add_argument("--output-json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = generate_phase_report(
        load_json(args.packet_eligibility_json),
        load_json(args.single_submit_packet_json),
        load_json(args.preflight_invariant_json),
        load_json(args.human_token_packet_json),
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
