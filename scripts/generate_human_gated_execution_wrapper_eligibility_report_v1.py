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


def generate_report(
    single_manual_submit_phase: Optional[Dict[str, Any]],
    human_token_packet: Optional[Dict[str, Any]],
    preflight_invariant: Optional[Dict[str, Any]],
    single_submit_packet: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    blockers = []
    warnings = []
    inherited_constraints = []

    payloads = {
        "single_manual_submit_phase": single_manual_submit_phase,
        "human_token_packet": human_token_packet,
        "preflight_invariant": preflight_invariant,
        "single_submit_packet": single_submit_packet,
    }
    for name, value in payloads.items():
        if not isinstance(value, dict):
            blockers.append(f"{name.upper()}_MISSING")

    if str((single_manual_submit_phase or {}).get("decision", "")) != "READY_FOR_HUMAN_MANUAL_TESTNET_SUBMIT":
        blockers.append("SINGLE_MANUAL_SUBMIT_PHASE_NOT_READY")
    if str((human_token_packet or {}).get("verdict", "")) != "PASS":
        blockers.append("HUMAN_TOKEN_PACKET_NOT_PASS")
    if str((preflight_invariant or {}).get("verdict", "")) != "PASS":
        blockers.append("PREFLIGHT_NOT_PASS")
    if str((single_submit_packet or {}).get("verdict", "")) != "PASS":
        blockers.append("SINGLE_SUBMIT_PACKET_NOT_PASS")

    token_required = bool((human_token_packet or {}).get("token_required") is True)
    if not token_required:
        blockers.append("TOKEN_REQUIRED_NOT_TRUE")

    max_submit_count = 1
    token_packet_count = int((human_token_packet or {}).get("max_submit_count", -1))
    single_packet_count = int((single_submit_packet or {}).get("max_submit_count", -1))
    if token_packet_count != 1:
        blockers.append("TOKEN_PACKET_MAX_SUBMIT_COUNT_NOT_1")
    if single_packet_count != 1:
        blockers.append("SINGLE_PACKET_MAX_SUBMIT_COUNT_NOT_1")

    if any(bool((v or {}).get("submit_allowed") is True) for v in payloads.values()):
        blockers.append("SUBMIT_ALLOWED_TRUE_IN_INPUT")

    eligible_for_execution_wrapper = False
    wrapper_mode = "NOT_ELIGIBLE"

    if not blockers:
        eligible_for_execution_wrapper = True
        wrapper_mode = "HUMAN_GATED_SINGLE_TESTNET_SUBMIT"
        inherited_constraints = [
            "REQUIRES_EXACT_TOKEN_MATCH",
            "REQUIRES_ALLOW_TESTNET_SUBMIT_FLAG",
            "REQUIRES_ENV_TESTNET",
            "MAX_SUBMIT_COUNT_1",
            "NO_AUTO_SUBMIT",
            "NO_REPEAT_SUBMIT",
        ]

    if blockers:
        verdict = "FAIL"
        ok = False
    elif warnings:
        verdict = "PARTIAL"
        ok = True
    else:
        verdict = "PASS"
        ok = True

    return {
        "ok": ok,
        "verdict": verdict,
        "eligible_for_execution_wrapper": eligible_for_execution_wrapper,
        "wrapper_mode": wrapper_mode,
        "submit_allowed": False,
        "max_submit_count": 1,
        "required_manual_confirmation": True,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "inherited_constraints": inherited_constraints,
        "next_actions": (
            ["GENERATE_DRY_RUN_PLAN"] if verdict == "PASS" else ["RESOLVE_ELIGIBILITY_BLOCKERS"]
        ),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate human-gated execution wrapper eligibility report")
    parser.add_argument("--single-manual-submit-phase-json", required=True)
    parser.add_argument("--human-token-packet-json", required=True)
    parser.add_argument("--preflight-invariant-json", required=True)
    parser.add_argument("--single-submit-packet-json", required=True)
    parser.add_argument("--output-json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = generate_report(
        load_json(args.single_manual_submit_phase_json),
        load_json(args.human_token_packet_json),
        load_json(args.preflight_invariant_json),
        load_json(args.single_submit_packet_json),
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
