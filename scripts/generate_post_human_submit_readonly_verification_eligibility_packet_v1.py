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


def generate_eligibility(
    final_one_shot_phase: Optional[Dict[str, Any]],
    runbook: Optional[Dict[str, Any]],
    final_checklist: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    blockers = []
    warnings = []

    payloads = {
        "final_one_shot_phase": final_one_shot_phase,
        "runbook": runbook,
        "final_checklist": final_checklist,
    }
    for name, value in payloads.items():
        if not isinstance(value, dict):
            blockers.append(f"{name.upper()}_MISSING")

    phase_decision = str((final_one_shot_phase or {}).get("decision", ""))
    ready_for_oneshot = phase_decision == "READY_FOR_ONE_SHOT_HUMAN_GATED_TESTNET_SUBMIT"
    ready_for_dryrun = phase_decision == "READY_FOR_HUMAN_COPY_PASTE_DRY_RUN"

    max_submit_count = int((final_one_shot_phase or {}).get("max_submit_count", 0))
    if max_submit_count > 1:
        blockers.append("MAX_SUBMIT_COUNT_GT_1")

    if str((runbook or {}).get("verdict", "")) != "PASS":
        blockers.append("RUNBOOK_NOT_PASS")
    if str((final_checklist or {}).get("verdict", "")) != "PASS":
        blockers.append("FINAL_CHECKLIST_NOT_PASS")

    for name, data in payloads.items():
        if _has_unsafe_marker(data or {}):
            blockers.append(f"{name.upper()}_HAS_UNSAFE_MARKER")
    if any(bool((v or {}).get("submit_allowed") is True) for v in payloads.values()):
        blockers.append("SUBMIT_ALLOWED_TRUE_IN_INPUT")
    if any(bool((v or {}).get("cancel_allowed") is True) for v in payloads.values()):
        blockers.append("CANCEL_ALLOWED_TRUE_IN_INPUT")
    if any(bool((v or {}).get("flatten_allowed") is True) for v in payloads.values()):
        blockers.append("FLATTEN_ALLOWED_TRUE_IN_INPUT")

    eligible_for_post_submit_verification = False
    if not blockers and ready_for_oneshot:
        eligible_for_post_submit_verification = True

    if blockers:
        verdict = "FAIL"
        ok = False
    elif ready_for_dryrun:
        verdict = "PARTIAL"
        ok = False
    elif str((final_checklist or {}).get("verdict", "")) == "PARTIAL":
        verdict = "PARTIAL"
        ok = False
    else:
        verdict = "PASS"
        ok = True

    return {
        "ok": ok,
        "verdict": verdict,
        "verification_mode": "POST_HUMAN_SUBMIT_READONLY",
        "readonly": True,
        "eligible_for_post_submit_verification": eligible_for_post_submit_verification,
        "submit_allowed": False,
        "cancel_allowed": False,
        "flatten_allowed": False,
        "max_submit_count": 1,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "inherited_constraints": [
            "READONLY_ONLY",
            "NO_SUBMIT",
            "NO_CANCEL",
            "NO_FLATTEN",
            "NO_MAINNET_LIVE",
            "NO_REPEAT_SUBMIT",
        ],
        "next_actions": (
            ["PARSE_EXECUTION_RECEIPT", "RUN_READONLY_PROTECTION_CHECKS", "AGGREGATE_EVIDENCE"]
            if verdict == "PASS"
            else ["RESOLVE_ELIGIBILITY_BLOCKERS"]
        ),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate post-human-submit readonly verification eligibility packet")
    parser.add_argument("--final-one-shot-phase-json", required=True)
    parser.add_argument("--runbook-json", required=True)
    parser.add_argument("--final-checklist-json", required=True)
    parser.add_argument("--output-json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = generate_eligibility(
        load_json(args.final_one_shot_phase_json),
        load_json(args.runbook_json),
        load_json(args.final_checklist_json),
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
