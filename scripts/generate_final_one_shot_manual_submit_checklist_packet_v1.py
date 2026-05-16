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


def _has_unsafe_marker(data: Dict[str, Any]) -> bool:
    for k, v in data.items():
        if isinstance(v, str):
            lower = v.lower()
            if "mainnet" in lower or "live" in lower or "api.binance.com" in lower:
                return True
        elif isinstance(v, dict):
            if _has_unsafe_marker(v):
                return True
    return False


def generate_checklist(
    wrapper_artifact: Optional[Dict[str, Any]],
    command_preview: Optional[Dict[str, Any]],
    human_token_packet: Optional[Dict[str, Any]],
    dry_run_command_verification: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    blockers = []
    warnings = []

    payloads = {
        "wrapper_artifact": wrapper_artifact,
        "command_preview": command_preview,
        "human_token_packet": human_token_packet,
        "dry_run_command_verification": dry_run_command_verification,
    }
    for name, value in payloads.items():
        if not isinstance(value, dict):
            blockers.append(f"{name.upper()}_MISSING")

    if str((dry_run_command_verification or {}).get("verdict", "")) == "FAIL":
        blockers.append("DRY_RUN_COMMAND_VERIFICATION_FAILED")
    if str((wrapper_artifact or {}).get("verdict", "")) != "PASS":
        blockers.append("WRAPPER_ARTIFACT_NOT_PASS")

    for name, data in payloads.items():
        if _has_unsafe_marker(data or {}):
            blockers.append(f"{name.upper()}_HAS_UNSAFE_MARKER")

    if any(bool((v or {}).get("submit_allowed") is True) for v in payloads.values()):
        blockers.append("SUBMIT_ALLOWED_TRUE_IN_INPUT")

    checklist_status = "BLOCKED"
    if blockers:
        verdict = "FAIL"
        ok = False
    elif str((dry_run_command_verification or {}).get("verdict", "")) == "PARTIAL":
        verdict = "PARTIAL"
        ok = False
        checklist_status = "NEEDS_REVIEW"
    else:
        verdict = "PASS"
        ok = True
        checklist_status = "READY_FOR_HUMAN_DECISION"

    return {
        "ok": ok,
        "verdict": verdict,
        "checklist_type": "FINAL_ONE_SHOT_MANUAL_TESTNET_SUBMIT",
        "checklist_status": checklist_status,
        "submit_allowed": False,
        "max_submit_count": 1,
        "required_human_checks": [
            "CONFIRM_DRY_RUN_COMMAND_WAS_VERIFIED_PASS",
            "CONFIRM_ENV_IS_TESTNET",
            "CONFIRM_SYMBOL_SIDE_QUANTITY_ARE_CORRECT",
            "CONFIRM_TOKEN_EXACT_MATCH",
            "CONFIRM_ALLOW_FLAG_INTENTIONAL",
            "CONFIRM_NO_MAINNET_OR_LIVE_MARKER",
            "CONFIRM_NO_AUTO_LOOP_OR_REPEAT_SUBMIT",
            "CONFIRM_MAX_SUBMIT_COUNT_IS_1",
            "CONFIRM_PROTECTIVE_SL_TP_PLAN_EXISTS",
            "CONFIRM_POST_SUBMIT_READONLY_VERIFICATION_WILL_RUN",
        ],
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "human_warning": "THIS_IS_THE_FINAL_CHECK_BEFORE_YOU_INTENTIONALLY_EXECUTE_A_TESTNET_SUBMIT_COMMAND. EXECUTE_AT_YOUR_OWN_RISK. DO_NOT_RUN_ON_MAINNET.",
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate final one-shot manual submit checklist packet")
    parser.add_argument("--wrapper-artifact-json", required=True)
    parser.add_argument("--command-preview-json", required=True)
    parser.add_argument("--human-token-packet-json", required=True)
    parser.add_argument("--dry-run-command-verification-json", required=True)
    parser.add_argument("--output-json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = generate_checklist(
        load_json(args.wrapper_artifact_json),
        load_json(args.command_preview_json),
        load_json(args.human_token_packet_json),
        load_json(args.dry_run_command_verification_json),
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
