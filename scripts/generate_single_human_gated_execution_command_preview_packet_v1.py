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


def _has_unsafe_marker(artifact: Dict[str, Any]) -> bool:
    text_fields = [
        str(artifact.get("dry_run_command", "")),
        str(artifact.get("human_execution_command_template", "")),
    ]
    for text in text_fields:
        lower = text.lower()
        if "mainnet" in lower or "live" in lower or "api.binance.com" in lower:
            return True
        if "--auto-submit" in lower or "--loop" in lower or "--repeat" in lower:
            return True
    return False


def generate_preview(
    wrapper_artifact: Optional[Dict[str, Any]],
    wrapper_invariant: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    blockers = []
    warnings = []

    if not isinstance(wrapper_artifact, dict):
        blockers.append("WRAPPER_ARTIFACT_MISSING")
    if not isinstance(wrapper_invariant, dict):
        blockers.append("WRAPPER_INVARIANT_MISSING")

    artifact_verdict = str((wrapper_artifact or {}).get("verdict", ""))
    invariant_verdict = str((wrapper_invariant or {}).get("verdict", ""))

    if _has_unsafe_marker(wrapper_artifact or {}):
        blockers.append("UNSAFE_MARKER_DETECTED")

    if artifact_verdict != "PASS":
        blockers.append("ARTIFACT_NOT_PASS")
    if invariant_verdict == "FAIL":
        blockers.append("INVARIANT_FAILED")

    dry_run_command = str((wrapper_artifact or {}).get("dry_run_command", ""))
    human_execution_command_template = str((wrapper_artifact or {}).get("human_execution_command_template", ""))

    if blockers:
        verdict = "FAIL"
        ok = False
    elif invariant_verdict == "PARTIAL":
        verdict = "PARTIAL"
        ok = True
    else:
        verdict = "PASS"
        ok = True

    return {
        "ok": ok,
        "verdict": verdict,
        "command_preview_type": "HUMAN_REVIEW_ONLY",
        "dry_run_command": dry_run_command,
        "human_execution_command_template": human_execution_command_template,
        "execution_locked": True,
        "unlock_requirements": [
            "EXACT_CONFIRM_TOKEN",
            "--allow-testnet-submit",
            "--env testnet",
            "HUMAN_CONFIRMATION",
            "MAX_SUBMIT_COUNT=1",
        ],
        "submit_allowed": False,
        "max_submit_count": 1,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate single human-gated execution command preview packet")
    parser.add_argument("--wrapper-artifact-json", required=True)
    parser.add_argument("--wrapper-invariant-json", required=True)
    parser.add_argument("--output-json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = generate_preview(
        load_json(args.wrapper_artifact_json),
        load_json(args.wrapper_invariant_json),
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
