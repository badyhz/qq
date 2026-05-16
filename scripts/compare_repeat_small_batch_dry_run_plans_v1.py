#!/usr/bin/env python3
import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional

FORBIDDEN = ["--allow-testnet-submit", "--confirm-token", "--submit", "--live", "mainnet"]


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


def _commands(plan: Dict[str, Any]) -> Optional[List[str]]:
    cmds = plan.get("dry_run_commands")
    if isinstance(cmds, list) and all(isinstance(x, str) for x in cmds):
        return cmds
    return None


def compare_plans(previous_plan: Optional[Dict[str, Any]], repeat_plan: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    blockers = []
    warnings = []
    drift_items: List[Dict[str, Any]] = []
    forbidden_found: List[str] = []

    if previous_plan is None:
        blockers.append("PREVIOUS_PLAN_MALFORMED_OR_MISSING")
    if repeat_plan is None:
        blockers.append("REPEAT_PLAN_MALFORMED_OR_MISSING")

    if blockers:
        return {
            "ok": False,
            "verdict": "FAIL",
            "plan_consistency_status": "UNSAFE",
            "previous_command_count": 0,
            "repeat_command_count": 0,
            "command_count_delta": 0,
            "forbidden_flags_detected": [],
            "drift_items": [],
            "blockers": sorted(set(blockers)),
            "warnings": warnings,
        }

    prev_cmds = _commands(previous_plan)
    rep_cmds = _commands(repeat_plan)

    incomplete = False
    if prev_cmds is None:
        incomplete = True
        prev_cmds = []
    if rep_cmds is None:
        incomplete = True
        rep_cmds = []

    if bool(previous_plan.get("submit_allowed") is True) or bool(repeat_plan.get("submit_allowed") is True):
        blockers.append("SUBMIT_ALLOWED_TRUE_DETECTED")

    for cmd in prev_cmds + rep_cmds:
        lower = cmd.lower()
        for token in FORBIDDEN:
            if token in lower:
                forbidden_found.append(token)

    if forbidden_found:
        blockers.append("FORBIDDEN_FLAGS_IN_PLAN")

    prev_count = len(prev_cmds)
    rep_count = len(rep_cmds)
    delta = rep_count - prev_count

    if delta != 0:
        drift_items.append({"field": "command_count", "previous": prev_count, "repeat": rep_count, "delta": delta})

    if blockers:
        verdict = "FAIL"
        ok = False
        status = "UNSAFE"
    elif incomplete:
        verdict = "PARTIAL"
        ok = True
        status = "INCOMPLETE"
    elif delta != 0:
        verdict = "PARTIAL"
        ok = True
        status = "DRIFT_DETECTED"
    else:
        verdict = "PASS"
        ok = True
        status = "CONSISTENT"

    return {
        "ok": ok,
        "verdict": verdict,
        "plan_consistency_status": status,
        "previous_command_count": prev_count,
        "repeat_command_count": rep_count,
        "command_count_delta": delta,
        "forbidden_flags_detected": sorted(set(forbidden_found)),
        "drift_items": drift_items,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Compare repeat small batch dry-run plans")
    parser.add_argument("--previous-execution-plan-json", required=True)
    parser.add_argument("--repeat-execution-plan-json", required=True)
    parser.add_argument("--output-json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = compare_plans(load_json(args.previous_execution_plan_json), load_json(args.repeat_execution_plan_json))

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
