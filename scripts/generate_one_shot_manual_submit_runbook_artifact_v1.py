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


def _has_token_gate(text: Any) -> bool:
    if not isinstance(text, str):
        return False
    return "--allow-testnet-submit" in text and "--confirm-token" in text and "--env testnet" in text


def generate_runbook(
    final_checklist: Optional[Dict[str, Any]],
    wrapper_artifact: Optional[Dict[str, Any]],
    human_token_packet: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    blockers = []
    warnings = []

    payloads = {
        "final_checklist": final_checklist,
        "wrapper_artifact": wrapper_artifact,
        "human_token_packet": human_token_packet,
    }
    for name, value in payloads.items():
        if not isinstance(value, dict):
            blockers.append(f"{name.upper()}_MISSING")

    checklist_pass = str((final_checklist or {}).get("verdict", "")) == "PASS"
    checklist_status = str((final_checklist or {}).get("checklist_status", ""))

    dry_run_command = str((wrapper_artifact or {}).get("dry_run_command", "")).strip()
    human_execution_command_template = str((wrapper_artifact or {}).get("human_execution_command_template", "")).strip()

    if not checklist_pass:
        blockers.append("FINAL_CHECKLIST_NOT_PASS")
    if checklist_status != "READY_FOR_HUMAN_DECISION":
        blockers.append("CHECKLIST_NOT_READY_FOR_HUMAN_DECISION")
    if not _has_token_gate(human_execution_command_template) and checklist_pass:
        blockers.append("EXECUTION_COMMAND_TEMPLATE_MISSING_TOKEN_GATE")

    if any(bool((v or {}).get("submit_allowed") is True) for v in payloads.values()):
        blockers.append("SUBMIT_ALLOWED_TRUE_IN_INPUT")

    if blockers:
        verdict = "FAIL"
        ok = False
        human_execution_command_template = ""
    elif warnings:
        verdict = "PARTIAL"
        ok = True
    else:
        verdict = "PASS"
        ok = True

    return {
        "ok": ok,
        "verdict": verdict,
        "runbook_type": "ONE_SHOT_MANUAL_TESTNET_SUBMIT_RUNBOOK",
        "submit_allowed": False,
        "max_submit_count": 1,
        "dry_run_step": {
            "instruction": "COPY_PASTE_DRY_RUN_COMMAND_VERIFY_OUTPUT",
            "command": dry_run_command,
        },
        "manual_submit_step": {
            "instruction": "IF_DRY_RUN_PASS_COPY_PASTE_SUBMIT_COMMAND_WITH_EXACT_TOKEN",
            "command_template": human_execution_command_template if checklist_pass else "",
            "required_flags": ["--allow-testnet-submit", "--confirm-token", "--env testnet"],
        },
        "post_submit_verification_step": {
            "instruction": "RUN_READONLY_VERIFICATION_NO_MORE_SUBMITS",
            "mode": "READONLY_ONLY",
        },
        "abort_conditions": [
            "ENV_NOT_TESTNET",
            "TOKEN_MISMATCH",
            "COMMAND_MISMATCH",
            "MAINNET_OR_LIVE_MARKER",
            "REPEATED_SUBMIT_ATTEMPT",
            "MISSING_SL_TP_PLAN",
            "DRY_RUN_VERIFICATION_NOT_PASS",
        ],
        "rollback_review_trigger": "ANY_UNEXPECTED_ORDER_OR_POSITION_STATE",
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate one-shot manual submit runbook artifact")
    parser.add_argument("--final-checklist-json", required=True)
    parser.add_argument("--wrapper-artifact-json", required=True)
    parser.add_argument("--human-token-packet-json", required=True)
    parser.add_argument("--output-json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = generate_runbook(
        load_json(args.final_checklist_json),
        load_json(args.wrapper_artifact_json),
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
