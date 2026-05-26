#!/usr/bin/env python3
import argparse
import json
import os
import sys
from typing import Any, Dict, Optional

from core.execution_guards import assert_dry_run_required, normalize_execution_mode


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


FORBIDDEN_FLAGS = [
    "--allow-testnet-submit",
    "--confirm-token",
    "--submit",
    "--live",
    "mainnet",
    "--auto-submit",
    "--loop",
    "--repeat",
]


def _has_forbidden(text: str) -> bool:
    lower = text.lower()
    for flag in FORBIDDEN_FLAGS:
        if flag.lower() in lower:
            return True
    return False


def verify_command(
    dry_run_readiness: Optional[Dict[str, Any]],
    provided_command: Optional[str] = None,
) -> Dict[str, Any]:
    blockers = []
    warnings = []

    if not isinstance(dry_run_readiness, dict):
        blockers.append("DRY_RUN_READINESS_MISSING")
        dry_run_readiness = {}

    expected_command = str((dry_run_readiness or {}).get("dry_run_command", "")).strip()
    provided = provided_command is not None and len(str(provided_command).strip()) > 0
    matches = False
    forbidden_flags_detected = []

    if provided:
        cmd = str(provided_command).strip()
        matches = cmd == expected_command

        for flag in FORBIDDEN_FLAGS:
            if flag.lower() in cmd.lower():
                forbidden_flags_detected.append(flag)
                blockers.append(f"FORBIDDEN_FLAG_{flag.upper().replace('-', '_')}")

    command_safety_status = "UNVERIFIED"
    if not provided:
        verdict = "PARTIAL"
        ok = False
    elif forbidden_flags_detected:
        verdict = "FAIL"
        ok = False
        command_safety_status = "UNSAFE"
    elif not matches:
        verdict = "FAIL"
        ok = False
        command_safety_status = "MISMATCHED"
    else:
        verdict = "PASS"
        ok = True
        command_safety_status = "SAFE_DRY_RUN_ONLY"

    return {
        "ok": ok,
        "verdict": verdict,
        "command_provided": provided,
        "command_matches_expected": matches,
        "submit_allowed": False,
        "command_safety_status": command_safety_status,
        "forbidden_flags_detected": forbidden_flags_detected,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
    }


def main(argv=None) -> int:
    mode = normalize_execution_mode(os.environ.get("QQ_RUNTIME_MODE"))
    assert_dry_run_required(mode)
    parser = argparse.ArgumentParser(description="Verify human copy-paste dry-run command")
    parser.add_argument("--dry-run-readiness-json", required=True)
    parser.add_argument("--provided-command")
    parser.add_argument("--output-json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = verify_command(
        load_json(args.dry_run_readiness_json),
        args.provided_command,
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
