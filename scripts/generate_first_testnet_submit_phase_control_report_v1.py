#!/usr/bin/env python3
import argparse
import json
import os
import sys
from typing import Any, Dict, Optional

PHASE = "first_testnet_submit_control"
FORBIDDEN_NEXT_ACTIONS = [
    "REAL_SUBMIT",
    "MAINNET_SUBMIT",
    "CANCEL_ORDER",
    "FLATTEN_POSITION",
]


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


def _has_mainnet_evidence(report: Dict[str, Any]) -> bool:
    text = json.dumps(report, sort_keys=True, ensure_ascii=False).lower()
    if "api.binance.com" in text or "mainnet" in text or "live" in text:
        return True
    return False


def generate_phase_control(t496: Optional[Dict[str, Any]], t497: Optional[Dict[str, Any]], t498: Optional[Dict[str, Any]], t499: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    blockers = []
    warnings = []

    if t496 is None:
        blockers.append("T496_LOAD_FAILED")
    if t497 is None:
        blockers.append("T497_LOAD_FAILED")
    if t498 is None:
        blockers.append("T498_LOAD_FAILED")
    if t499 is None:
        blockers.append("T499_LOAD_FAILED")

    component_verdicts = {
        "T496": (t496 or {}).get("verdict"),
        "T497": (t497 or {}).get("verdict"),
        "T498": (t498 or {}).get("verdict"),
        "T499": (t499 or {}).get("verdict"),
    }

    submit_executed = bool((t498 or {}).get("submit_executed") is True)
    submit_attempted = bool((t498 or {}).get("submit_attempted") is True)

    if _has_mainnet_evidence(t496 or {}) or _has_mainnet_evidence(t498 or {}):
        blockers.append("MAINNET_OR_LIVE_EVIDENCE_DETECTED")

    joined = json.dumps({"t498": t498, "t499": t499}, sort_keys=True, ensure_ascii=False).lower()
    if "cancel" in joined and "none occurred" not in joined:
        blockers.append("CANCEL_EVIDENCE_DETECTED")
    if "flatten" in joined and "none occurred" not in joined:
        blockers.append("FLATTEN_EVIDENCE_DETECTED")

    if str((t496 or {}).get("verdict")) == "FAIL":
        blockers.append("T496_NOT_READY")
    if str((t497 or {}).get("verdict")) != "PASS":
        blockers.append("T497_TOKEN_GATE_NOT_PASS")

    if submit_executed:
        if str((t499 or {}).get("verdict")) != "PASS":
            blockers.append("T499_NOT_PASS_FOR_SUBMITTED_FLOW")

    if blockers:
        if any(x in blockers for x in ["MAINNET_OR_LIVE_EVIDENCE_DETECTED", "CANCEL_EVIDENCE_DETECTED", "FLATTEN_EVIDENCE_DETECTED"]):
            verdict = "FAIL"
        elif submit_executed and "T499_NOT_PASS_FOR_SUBMITTED_FLOW" in blockers:
            verdict = "FAIL"
        else:
            verdict = "PARTIAL"
        ok = False
    else:
        verdict = "PASS"
        ok = True

    if verdict == "PASS" and not submit_executed:
        allowed_next_actions = ["ready_for_manual_testnet_submit", "continue_readonly_verification"]
        warnings.append("NOT_ACTUALLY_SUBMITTED_YET")
    elif verdict == "PASS" and submit_executed:
        allowed_next_actions = ["monitor_testnet_position_readonly", "archive_submit_artifacts"]
    else:
        allowed_next_actions = ["fix_blockers", "rerun_dry_run_wrapper"]

    return {
        "ok": ok,
        "verdict": verdict,
        "phase": PHASE,
        "component_verdicts": component_verdicts,
        "submit_executed": submit_executed,
        "submit_attempted": submit_attempted,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "allowed_next_actions": allowed_next_actions,
        "forbidden_next_actions": FORBIDDEN_NEXT_ACTIONS,
        "required_human_decision": "APPROVE_SUBMIT_OR_KEEP_DRY_RUN",
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate first testnet submit phase control report")
    parser.add_argument("--inputs", nargs=4, metavar=("T496", "T497", "T498", "T499"), required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = generate_phase_control(
        load_json(args.inputs[0]),
        load_json(args.inputs[1]),
        load_json(args.inputs[2]),
        load_json(args.inputs[3]),
    )

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
