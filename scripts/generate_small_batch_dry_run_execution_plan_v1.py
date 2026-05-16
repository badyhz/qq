#!/usr/bin/env python3
import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional

FORBIDDEN_TOKENS = ["--allow-testnet-submit", "--confirm-token", "--submit", "--live", "mainnet"]


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


def generate_plan(selection: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    blockers: List[str] = []
    warnings: List[str] = []
    commands: List[str] = []
    forbidden_detected: List[str] = []

    if selection is None:
        blockers.append("SELECTION_MALFORMED_OR_MISSING")
        selection = {}

    if str(selection.get("verdict", "")) not in ["PASS", "PARTIAL"]:
        blockers.append("SELECTION_NOT_USABLE")

    if bool(selection.get("submit_allowed") is True):
        blockers.append("SELECTION_SUBMIT_ALLOWED_MUST_BE_FALSE")

    batch_mode = "DRY_RUN_ONLY"
    submit_allowed = False

    candidates = selection.get("selected_candidates")
    if not isinstance(candidates, list):
        blockers.append("SELECTED_CANDIDATES_MALFORMED")
        candidates = []

    for c in candidates:
        if not isinstance(c, dict):
            continue
        symbol = c.get("symbol")
        side = c.get("side")
        qty = c.get("quantity")
        base_url = c.get("base_url")
        cmd = (
            "python3 scripts/run_testnet_submit_execution_wrapper_v1.py "
            "--inputs <command_packet.json> <token_gate.json> <payload.json> <invariants.json> <phase_report.json> "
            f"--env testnet --output <dry_run_result_{symbol}_{side}.json> --json"
        )
        if any(x in str(base_url).lower() for x in ["mainnet", "api.binance.com", "live"]):
            blockers.append("CANDIDATE_MAINNET_OR_LIVE_MARKER")
        if not symbol or side not in ["BUY", "SELL"] or qty in [None, "", 0, 0.0, "0"]:
            blockers.append("CANDIDATE_FIELDS_INVALID")
        commands.append(cmd)

    for cmd in commands:
        lower = cmd.lower()
        for token in FORBIDDEN_TOKENS:
            if token in lower:
                forbidden_detected.append(token)

    if forbidden_detected:
        blockers.append("FORBIDDEN_FLAGS_DETECTED")

    if not commands:
        blockers.append("NO_DRY_RUN_COMMAND_GENERATED")

    if blockers:
        verdict = "FAIL"
        ok = False
    else:
        verdict = "PASS"
        ok = True

    return {
        "ok": ok,
        "verdict": verdict,
        "batch_mode": batch_mode,
        "submit_allowed": submit_allowed,
        "command_count": len(commands),
        "dry_run_commands": commands,
        "forbidden_flags_detected": sorted(set(forbidden_detected)),
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate small batch dry-run execution plan")
    parser.add_argument("--candidate-selection-json", required=True)
    parser.add_argument("--output-json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = generate_plan(load_json(args.candidate_selection_json))

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
