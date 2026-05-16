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


def _has_live_marker(text: Any) -> bool:
    if not isinstance(text, str):
        return False
    lower = text.lower()
    return "mainnet" in lower or "live" in lower or "api.binance.com" in lower


def generate_readiness(
    wrapper_artifact_phase: Optional[Dict[str, Any]],
    command_preview: Optional[Dict[str, Any]],
    wrapper_invariant: Optional[Dict[str, Any]],
    local_audit_manifest: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    blockers = []
    warnings = []

    payloads = {
        "wrapper_artifact_phase": wrapper_artifact_phase,
        "command_preview": command_preview,
        "wrapper_invariant": wrapper_invariant,
        "local_audit_manifest": local_audit_manifest,
    }
    for name, value in payloads.items():
        if not isinstance(value, dict):
            blockers.append(f"{name.upper()}_MISSING")

    if str((wrapper_artifact_phase or {}).get("verdict", "")) != "PASS":
        blockers.append("WRAPPER_ARTIFACT_PHASE_NOT_PASS")
    if str((command_preview or {}).get("verdict", "")) != "PASS":
        blockers.append("COMMAND_PREVIEW_NOT_PASS")
    if str((wrapper_invariant or {}).get("verdict", "")) != "PASS":
        blockers.append("WRAPPER_INVARIANT_NOT_PASS")
    if str((local_audit_manifest or {}).get("verdict", "")) != "PASS":
        blockers.append("LOCAL_AUDIT_MANIFEST_NOT_PASS")

    dry_run_command = str((command_preview or {}).get("dry_run_command", "")).strip()

    if not dry_run_command:
        blockers.append("DRY_RUN_COMMAND_MISSING")

    if _has_live_marker(dry_run_command):
        blockers.append("LIVE_OR_MAINNET_MARKER_DETECTED")

    if any(bool((v or {}).get("submit_allowed") is True) for v in payloads.values()):
        blockers.append("SUBMIT_ALLOWED_TRUE_IN_INPUT")

    dry_run_ready = False
    if not blockers:
        dry_run_ready = True

    if blockers:
        verdict = "FAIL"
        ok = False
    elif warnings:
        verdict = "PARTIAL"
        ok = True
    else:
        verdict = "PASS"
        ok = True

    return {
        "ok": ok,
        "verdict": verdict,
        "readiness_type": "HUMAN_COPY_PASTE_DRY_RUN_ONLY",
        "dry_run_ready": dry_run_ready,
        "submit_allowed": False,
        "max_submit_count": 1,
        "dry_run_command": dry_run_command,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "human_instructions": [
            "COPY_PASTE_COMMAND_BELOW_ONLY",
            "DO_NOT_MODIFY_COMMAND",
            "DO_NOT_ADD_SUBMIT_FLAGS",
            "VERIFY_OUTPUT_IS_DRY_RUN_ONLY",
        ],
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate human copy-paste dry-run readiness packet")
    parser.add_argument("--wrapper-artifact-phase-json", required=True)
    parser.add_argument("--command-preview-json", required=True)
    parser.add_argument("--wrapper-invariant-json", required=True)
    parser.add_argument("--local-audit-manifest-json", required=True)
    parser.add_argument("--output-json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = generate_readiness(
        load_json(args.wrapper_artifact_phase_json),
        load_json(args.command_preview_json),
        load_json(args.wrapper_invariant_json),
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
