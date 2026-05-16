#!/usr/bin/env python3
import argparse
import json
import os
import sys
from typing import Any, Dict, Optional


PHASE = "FINAL_HUMAN_GATED_ONE_SHOT_SUBMIT_REVIEW"


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
    dry_run_readiness: Optional[Dict[str, Any]],
    dry_run_command_verification: Optional[Dict[str, Any]],
    final_checklist: Optional[Dict[str, Any]],
    runbook: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    warnings = []
    blockers = []

    payloads = {
        "dry_run_readiness": dry_run_readiness,
        "dry_run_command_verification": dry_run_command_verification,
        "final_checklist": final_checklist,
        "runbook": runbook,
    }
    for name, value in payloads.items():
        if not isinstance(value, dict):
            blockers.append(f"{name.upper()}_MISSING")

    verdicts = [str((v or {}).get("verdict", "")) for v in payloads.values()]

    if any(bool((v or {}).get("submit_allowed") is True) for v in payloads.values()):
        blockers.append("SUBMIT_ALLOWED_TRUE_NOT_PERMITTED")

    max_submit_count = 1

    readiness_pass = str((dry_run_readiness or {}).get("verdict", "")) == "PASS"
    verification_partial = str((dry_run_command_verification or {}).get("verdict", "")) == "PARTIAL"

    if blockers or any(v == "FAIL" for v in verdicts):
        verdict = "FAIL"
        decision = "STOP"
        ok = False
        can_continue = False
    elif any(v == "PARTIAL" for v in verdicts):
        if readiness_pass and verification_partial:
            verdict = "PASS"
            decision = "READY_FOR_HUMAN_COPY_PASTE_DRY_RUN"
            ok = True
            can_continue = True
        else:
            verdict = "PARTIAL"
            decision = "REVIEW"
            ok = False
            can_continue = False
    else:
        verdict = "PASS"
        decision = "READY_FOR_ONE_SHOT_HUMAN_GATED_TESTNET_SUBMIT"
        ok = True
        can_continue = True

    return {
        "ok": ok,
        "verdict": verdict,
        "phase": PHASE,
        "decision": decision,
        "can_continue": can_continue,
        "submit_allowed": False,
        "max_submit_count": 1,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "required_next_actions": (
            ["HUMAN_COPY_PASTE_DRY_RUN_FIRST", "HUMAN_VERIFY_DRY_RUN_OUTPUT", "THEN_HUMAN_GATED_ONE_SHOT_SUBMIT_IF_READY"]
            if decision == "READY_FOR_ONE_SHOT_HUMAN_GATED_TESTNET_SUBMIT"
            else ["HUMAN_COPY_PASTE_DRY_RUN_ONLY"]
            if decision == "READY_FOR_HUMAN_COPY_PASTE_DRY_RUN"
            else ["RESOLVE_FINAL_REVIEW_GAPS"]
        ),
        "next_task_recommendation": (
            "post_human_submit_readonly_verification_packet"
            if decision == "READY_FOR_ONE_SHOT_HUMAN_GATED_TESTNET_SUBMIT"
            else "final_human_gated_one_shot_submit_review"
        ),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate final human-gated one-shot submit phase control report")
    parser.add_argument("--dry-run-readiness-json", required=True)
    parser.add_argument("--dry-run-command-verification-json", required=True)
    parser.add_argument("--final-checklist-json", required=True)
    parser.add_argument("--runbook-json", required=True)
    parser.add_argument("--output-json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = generate_phase_report(
        load_json(args.dry_run_readiness_json),
        load_json(args.dry_run_command_verification_json),
        load_json(args.final_checklist_json),
        load_json(args.runbook_json),
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
