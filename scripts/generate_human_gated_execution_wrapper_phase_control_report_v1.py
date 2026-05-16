#!/usr/bin/env python3
import argparse
import json
import os
import sys
from typing import Any, Dict, Optional


PHASE = "HUMAN_GATED_EXECUTION_WRAPPER_REVIEW"


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
    wrapper_eligibility: Optional[Dict[str, Any]],
    dry_run_plan: Optional[Dict[str, Any]],
    token_validation: Optional[Dict[str, Any]],
    final_safety_gate: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    warnings = []
    blockers = []

    payloads = {
        "wrapper_eligibility": wrapper_eligibility,
        "dry_run_plan": dry_run_plan,
        "token_validation": token_validation,
        "final_safety_gate": final_safety_gate,
    }
    for name, value in payloads.items():
        if not isinstance(value, dict):
            blockers.append(f"{name.upper()}_MISSING")

    verdicts = [str((v or {}).get("verdict", "")) for v in payloads.values()]

    if any(bool((v or {}).get("submit_allowed") is True) for v in payloads.values()):
        blockers.append("SUBMIT_ALLOWED_TRUE_NOT_PERMITTED")

    max_submit_count = 1

    gate_status = str((final_safety_gate or {}).get("gate_status", ""))

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
    elif gate_status == "READY_FOR_HUMAN_EXECUTION":
        verdict = "PASS"
        decision = "READY_FOR_SINGLE_HUMAN_GATED_TESTNET_EXECUTION"
        ok = True
        can_continue = True
    else:
        verdict = "FAIL"
        decision = "STOP"
        ok = False
        can_continue = False

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
            ["HUMAN_EXECUTE_SINGLE_TESTNET_SUBMIT"]
            if decision == "READY_FOR_SINGLE_HUMAN_GATED_TESTNET_EXECUTION"
            else ["RESOLVE_WRAPPER_REVIEW_GAPS"]
        ),
        "next_task_recommendation": (
            "single_human_gated_testnet_execution_wrapper"
            if decision == "READY_FOR_SINGLE_HUMAN_GATED_TESTNET_EXECUTION"
            else "human_gated_execution_wrapper_review"
        ),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate human-gated execution wrapper phase control report")
    parser.add_argument("--wrapper-eligibility-json", required=True)
    parser.add_argument("--dry-run-plan-json", required=True)
    parser.add_argument("--token-validation-json", required=True)
    parser.add_argument("--final-safety-gate-json", required=True)
    parser.add_argument("--output-json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = generate_phase_report(
        load_json(args.wrapper_eligibility_json),
        load_json(args.dry_run_plan_json),
        load_json(args.token_validation_json),
        load_json(args.final_safety_gate_json),
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
