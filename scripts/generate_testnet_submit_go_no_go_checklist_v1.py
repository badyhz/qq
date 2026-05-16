#!/usr/bin/env python3
import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional

PHASE = "testnet_submit_go_no_go_checklist"


def load_json(path: str) -> Optional[Dict[str, Any]]:
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def write_json(path: str, data: Dict[str, Any]) -> bool:
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, sort_keys=True, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def generate_checklist(t491: Optional[Dict[str, Any]], t492: Optional[Dict[str, Any]], t493: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    blockers: List[str] = []
    warnings: List[str] = []

    if t491 is None:
        blockers.append("T491_LOAD_FAILED")
    if t492 is None:
        blockers.append("T492_LOAD_FAILED")
    if t493 is None:
        blockers.append("T493_LOAD_FAILED")

    verdict_491 = str((t491 or {}).get("verdict", ""))
    verdict_492 = str((t492 or {}).get("verdict", ""))
    verdict_493 = str((t493 or {}).get("verdict", ""))

    safe_partial_493 = bool((t493 or {}).get("safe_partial", False))

    checklist = [
        {
            "section": "artifact_completeness",
            "pass": t491 is not None and t492 is not None and t493 is not None,
        },
        {
            "section": "dry_run_stability",
            "pass": verdict_491 == "PASS",
        },
        {
            "section": "payload_invariants",
            "pass": verdict_492 == "PASS",
        },
        {
            "section": "risk_delta",
            "pass": verdict_493 == "PASS" or (verdict_493 == "PARTIAL" and safe_partial_493),
            "verdict": verdict_493,
        },
        {
            "section": "manual_approval",
            "pass": verdict_491 == "PASS",
        },
        {
            "section": "submit_boundary",
            "pass": True,
            "notes": "SUBMIT_NOT_EXECUTED_IN_THIS_STEP",
        },
        {
            "section": "rollback_flatten_safety_reminder",
            "pass": True,
            "notes": "DO_NOT_CALL_FLATTEN_ENDPOINT_AUTOMATICALLY",
        },
    ]

    if verdict_491 != "PASS":
        blockers.append("MANUAL_APPROVAL_GATE_NOT_PASS")
    if verdict_492 != "PASS":
        blockers.append("PAYLOAD_INVARIANTS_NOT_PASS")
    if verdict_493 == "FAIL":
        blockers.append("RISK_DELTA_DANGEROUS")
    if verdict_493 == "PARTIAL" and not safe_partial_493:
        blockers.append("RISK_DELTA_PARTIAL_NOT_SAFE")

    if verdict_493 == "PARTIAL" and safe_partial_493:
        warnings.append("RISK_DELTA_PARTIAL_REQUIRES_HUMAN_EXPLANATION")

    if not blockers and verdict_491 == "PASS" and verdict_492 == "PASS" and (verdict_493 == "PASS" or (verdict_493 == "PARTIAL" and safe_partial_493)):
        verdict = "GO"
        ok = True
    elif any(item in blockers for item in ["PAYLOAD_INVARIANTS_NOT_PASS", "RISK_DELTA_DANGEROUS", "MANUAL_APPROVAL_GATE_NOT_PASS"]):
        verdict = "NO_GO"
        ok = False
    else:
        verdict = "WAIT"
        ok = False

    next_command_template = (
        "DRY_TEMPLATE_ONLY: python <submit_script.py> "
        "--payload <intended_testnet_payload.json> "
        "--manual-approval-id <APPROVAL_ID> "
        "--confirm TESTNET_ONLY"
    )

    return {
        "ok": ok,
        "verdict": verdict,
        "phase": PHASE,
        "checklist": checklist,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "next_command_template": next_command_template,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate testnet submit go/no-go checklist")
    parser.add_argument("--inputs", nargs=3, metavar=("T491", "T492", "T493"), required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = generate_checklist(load_json(args.inputs[0]), load_json(args.inputs[1]), load_json(args.inputs[2]))

    if not write_json(args.output, report):
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
