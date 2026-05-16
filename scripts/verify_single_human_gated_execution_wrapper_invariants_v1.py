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


def _has_auto_marker(text: Any) -> bool:
    if not isinstance(text, str):
        return False
    lower = text.lower()
    return "--auto-submit" in lower or "--loop" in lower or "--repeat" in lower


def _has_token_gate(text: Any) -> bool:
    if not isinstance(text, str):
        return False
    return "--allow-testnet-submit" in text and "--confirm-token" in text and "--env testnet" in text


def verify_invariants(wrapper_artifact: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    blockers = []
    warnings = []

    if not isinstance(wrapper_artifact, dict):
        blockers.append("WRAPPER_ARTIFACT_MISSING")
        wrapper_artifact = {}

    checked = {}

    # Critical invariants
    checked["artifact_type_correct"] = str(wrapper_artifact.get("artifact_type", "")).strip() == "SINGLE_HUMAN_GATED_TESTNET_EXECUTION_WRAPPER"
    checked["wrapper_mode_correct"] = str(wrapper_artifact.get("wrapper_mode", "")).strip() == "HUMAN_GATED_SINGLE_TESTNET_SUBMIT"
    checked["env_is_testnet"] = str(wrapper_artifact.get("env", "")).strip().lower() == "testnet"
    checked["symbol_present"] = bool(wrapper_artifact.get("symbol"))
    checked["side_present"] = bool(wrapper_artifact.get("side"))

    qty = wrapper_artifact.get("quantity")
    try:
        checked["quantity_positive"] = float(qty) > 0 if qty not in (None, "", 0, "0", "0.0") else False
    except (ValueError, TypeError):
        checked["quantity_positive"] = False

    checked["submit_allowed_false"] = bool(wrapper_artifact.get("submit_allowed") is False)
    checked["max_submit_count_1"] = int(wrapper_artifact.get("max_submit_count", 0)) == 1
    checked["dry_run_command_present"] = isinstance(wrapper_artifact.get("dry_run_command"), str) and len(str(wrapper_artifact.get("dry_run_command")).strip()) > 0
    checked["token_gated_template"] = _has_token_gate(wrapper_artifact.get("human_execution_command_template", ""))
    checked["no_live_marker"] = not _has_live_marker(str(wrapper_artifact.get("dry_run_command", ""))) and not _has_live_marker(str(wrapper_artifact.get("human_execution_command_template", "")))
    checked["no_auto_submit"] = not _has_auto_marker(str(wrapper_artifact.get("dry_run_command", ""))) and not _has_auto_marker(str(wrapper_artifact.get("human_execution_command_template", "")))

    # Optional fields check (warnings only)
    checked["safety_notes_present"] = isinstance(wrapper_artifact.get("safety_notes"), list) and len(wrapper_artifact.get("safety_notes", [])) > 0

    # Check all critical invariants
    critical_keys = [
        "artifact_type_correct",
        "wrapper_mode_correct",
        "env_is_testnet",
        "symbol_present",
        "side_present",
        "quantity_positive",
        "submit_allowed_false",
        "max_submit_count_1",
        "dry_run_command_present",
        "token_gated_template",
        "no_live_marker",
        "no_auto_submit",
    ]

    for key in critical_keys:
        if not checked.get(key, False):
            blockers.append(f"INVARIANT_FAILED_{key.upper()}")

    # Check optional fields
    if not checked.get("safety_notes_present", False):
        warnings.append("SAFETY_NOTES_MISSING")

    if blockers:
        verdict = "FAIL"
        ok = False
        invariant_status = "INVARIANTS_VIOLATED"
    elif warnings:
        verdict = "PARTIAL"
        ok = True
        invariant_status = "INVARIANTS_PASS_WITH_WARNINGS"
    else:
        verdict = "PASS"
        ok = True
        invariant_status = "INVARIANTS_PASS"

    return {
        "ok": ok,
        "verdict": verdict,
        "invariant_status": invariant_status,
        "checked_invariants": checked,
        "submit_allowed": False,
        "max_submit_count": 1,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Verify single human-gated execution wrapper invariants")
    parser.add_argument("--wrapper-artifact-json", required=True)
    parser.add_argument("--output-json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = verify_invariants(load_json(args.wrapper_artifact_json))

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
