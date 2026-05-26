#!/usr/bin/env python3
import argparse
import json
import os
import sys
from typing import Any, Dict, Optional

from core.execution_guards import assert_dry_run_required, normalize_execution_mode


PHASE = "SINGLE_HUMAN_GATED_EXECUTION_WRAPPER_ARTIFACT"


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
    wrapper_artifact: Optional[Dict[str, Any]],
    wrapper_invariant: Optional[Dict[str, Any]],
    command_preview: Optional[Dict[str, Any]],
    local_audit_manifest: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    warnings = []
    blockers = []

    payloads = {
        "wrapper_artifact": wrapper_artifact,
        "wrapper_invariant": wrapper_invariant,
        "command_preview": command_preview,
        "local_audit_manifest": local_audit_manifest,
    }
    for name, value in payloads.items():
        if not isinstance(value, dict):
            blockers.append(f"{name.upper()}_MISSING")

    verdicts = [str((v or {}).get("verdict", "")) for v in payloads.values()]

    if any(bool((v or {}).get("submit_allowed") is True) for v in payloads.values()):
        blockers.append("SUBMIT_ALLOWED_TRUE_NOT_PERMITTED")

    max_submit_count = 1

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
    else:
        verdict = "PASS"
        decision = "READY_FOR_HUMAN_GATED_SINGLE_TESTNET_SUBMIT"
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
            ["HUMAN_COPY_PASTE_TESTNET_DRY_RUN", "HUMAN_GATED_SINGLE_TESTNET_SUBMIT"]
            if decision == "READY_FOR_HUMAN_GATED_SINGLE_TESTNET_SUBMIT"
            else ["RESOLVE_WRAPPER_ARTIFACT_GAPS"]
        ),
        "next_task_recommendation": (
            "human_copy_paste_dry_run_final_manual_submit_checklist"
            if decision == "READY_FOR_HUMAN_GATED_SINGLE_TESTNET_SUBMIT"
            else "single_human_gated_execution_wrapper_artifact_review"
        ),
    }


def main(argv=None) -> int:
    mode = normalize_execution_mode(os.environ.get("QQ_RUNTIME_MODE"))
    assert_dry_run_required(mode)
    parser = argparse.ArgumentParser(description="Generate single human-gated execution wrapper artifact phase control report")
    parser.add_argument("--wrapper-artifact-json", required=True)
    parser.add_argument("--wrapper-invariant-json", required=True)
    parser.add_argument("--command-preview-json", required=True)
    parser.add_argument("--local-audit-manifest-json", required=True)
    parser.add_argument("--output-json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = generate_phase_report(
        load_json(args.wrapper_artifact_json),
        load_json(args.wrapper_invariant_json),
        load_json(args.command_preview_json),
        load_json(args.local_audit_manifest_json),
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
