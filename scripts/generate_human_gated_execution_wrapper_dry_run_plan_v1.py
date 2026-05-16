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


def _has_forbidden_live_marker(text: Any) -> bool:
    if not isinstance(text, str):
        return False
    lower = text.lower()
    return "mainnet" in lower or "live" in lower or "api.binance.com" in lower


def _has_autosubmit_marker(text: Any) -> bool:
    if not isinstance(text, str):
        return False
    lower = text.lower()
    return "--auto-submit" in lower or "--loop" in lower or "--repeat" in lower


def _max_submit_count_ok(text: Any) -> bool:
    if not isinstance(text, str):
        return True
    import re
    matches = re.findall(r"max_submit_count\s*[=:]\s*(\d+)", text, re.IGNORECASE)
    for m in matches:
        if int(m) > 1:
            return False
    return True


def _has_required_token_gate(text: Any) -> bool:
    if not isinstance(text, str):
        return False
    return "--allow-testnet-submit" in text and "--confirm-token" in text and "--env testnet" in text


def generate_plan(
    wrapper_eligibility: Optional[Dict[str, Any]],
    single_submit_packet: Optional[Dict[str, Any]],
    human_token_packet: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    blockers = []
    warnings = []

    if not isinstance(wrapper_eligibility, dict):
        blockers.append("WRAPPER_ELIGIBILITY_MISSING")
    if not isinstance(single_submit_packet, dict):
        blockers.append("SINGLE_SUBMIT_PACKET_MISSING")
    if not isinstance(human_token_packet, dict):
        blockers.append("HUMAN_TOKEN_PACKET_MISSING")

    if str((wrapper_eligibility or {}).get("verdict", "")) != "PASS":
        blockers.append("WRAPPER_ELIGIBILITY_NOT_PASS")

    dry_run_command = str((single_submit_packet or {}).get("dry_run_command", ""))
    execution_command_template = str((single_submit_packet or {}).get("manual_submit_command_template", ""))

    if _has_forbidden_live_marker(dry_run_command) or _has_forbidden_live_marker(execution_command_template):
        blockers.append("FORBIDDEN_LIVE_MARKER_FOUND")
    if _has_autosubmit_marker(dry_run_command) or _has_autosubmit_marker(execution_command_template):
        blockers.append("FORBIDDEN_AUTO_SUBMIT_MARKER_FOUND")
    if not _max_submit_count_ok(dry_run_command) or not _max_submit_count_ok(execution_command_template):
        blockers.append("MAX_SUBMIT_COUNT_GT_1_FOUND")
    if not _has_required_token_gate(execution_command_template):
        blockers.append("REQUIRED_TOKEN_GATE_MISSING_IN_TEMPLATE")

    if any(bool((v or {}).get("submit_allowed") is True) for v in [wrapper_eligibility, single_submit_packet, human_token_packet]):
        blockers.append("SUBMIT_ALLOWED_TRUE_IN_INPUT")

    if blockers:
        verdict = "FAIL"
        ok = False
    else:
        verdict = "PASS"
        ok = True

    return {
        "ok": ok,
        "verdict": verdict,
        "wrapper_mode": "HUMAN_GATED_SINGLE_TESTNET_SUBMIT",
        "dry_run_only": True,
        "submit_allowed": False,
        "max_submit_count": 1,
        "dry_run_command": dry_run_command,
        "execution_command_template": execution_command_template,
        "required_runtime_inputs": [
            "--allow-testnet-submit",
            "--confirm-token <EXACT_TOKEN>",
            "--env testnet",
        ],
        "forbidden_runtime_inputs": [
            "mainnet",
            "live",
            "--auto-submit",
            "--loop",
            "--repeat",
            "max_submit_count > 1",
        ],
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate human-gated execution wrapper dry-run plan")
    parser.add_argument("--wrapper-eligibility-json", required=True)
    parser.add_argument("--single-submit-packet-json", required=True)
    parser.add_argument("--human-token-packet-json", required=True)
    parser.add_argument("--output-json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = generate_plan(
        load_json(args.wrapper_eligibility_json),
        load_json(args.single_submit_packet_json),
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
