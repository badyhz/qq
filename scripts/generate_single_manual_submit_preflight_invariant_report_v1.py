#!/usr/bin/env python3
import argparse
import json
import os
import sys
from typing import Any, Dict, Optional


ACCEPTED_SIDES = {"BUY", "SELL", "LONG", "SHORT"}


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


def _has_token_gate(template: Any) -> bool:
    if not isinstance(template, str):
        return False
    return "--allow-testnet-submit" in template and "--confirm-token" in template and "--env testnet" in template


def _live_marker(text: Any) -> bool:
    if not isinstance(text, str):
        return False
    lower = text.lower()
    return "mainnet" in lower or "api.binance.com" in lower or "live" in lower


def generate_report(packet: Optional[Dict[str, Any]], checklist: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    blockers = []
    warnings = []

    if not isinstance(packet, dict):
        blockers.append("SINGLE_SUBMIT_PACKET_MISSING")
        packet = {}
    if not isinstance(checklist, dict):
        blockers.append("RISK_ACCEPTANCE_CHECKLIST_MISSING")
        checklist = {}

    env = str(packet.get("env", ""))
    symbol = packet.get("symbol")
    side = str(packet.get("side", ""))
    qty = packet.get("quantity")
    dry_run_command = packet.get("dry_run_command")
    manual_template = packet.get("manual_submit_command_template")

    checked = {
        "env_testnet": env.lower() == "testnet",
        "symbol_present": bool(symbol),
        "side_accepted": side in ACCEPTED_SIDES,
        "quantity_positive": False,
        "no_mainnet_live_marker": not any(_live_marker(v) for v in [env, str(dry_run_command), str(manual_template)]),
        "dry_run_command_present": isinstance(dry_run_command, str) and len(dry_run_command) > 0,
        "manual_template_token_gated": _has_token_gate(manual_template),
        "checklist_pass": str(checklist.get("verdict", "")) == "PASS",
        "submit_allowed_false_before_token_gate": bool(packet.get("submit_allowed") is False),
        "max_submit_count_is_1": int(packet.get("max_submit_count", -1)) == 1,
    }

    try:
        checked["quantity_positive"] = float(qty) > 0
    except Exception:
        checked["quantity_positive"] = False

    critical_keys = [
        "env_testnet",
        "symbol_present",
        "side_accepted",
        "quantity_positive",
        "no_mainnet_live_marker",
        "dry_run_command_present",
        "manual_template_token_gated",
        "submit_allowed_false_before_token_gate",
        "max_submit_count_is_1",
    ]

    for key in critical_keys:
        if not checked[key]:
            blockers.append(f"INVARIANT_FAILED:{key.upper()}")

    if not checked["checklist_pass"]:
        warnings.append("CHECKLIST_NOT_PASS")

    if blockers:
        verdict = "FAIL"
        ok = False
        status = "INVARIANTS_BLOCKED"
    elif warnings:
        verdict = "PARTIAL"
        ok = True
        status = "INVARIANTS_WARNINGS"
    else:
        verdict = "PASS"
        ok = True
        status = "INVARIANTS_PASSED"

    return {
        "ok": ok,
        "verdict": verdict,
        "invariant_status": status,
        "checked_invariants": checked,
        "submit_allowed": False,
        "max_submit_count": 1,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "next_actions": (
            ["GENERATE_HUMAN_TOKEN_PACKET"] if verdict == "PASS" else ["RESOLVE_INVARIANTS"]
        ),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate single manual submit preflight invariant report")
    parser.add_argument("--single-submit-packet-json", required=True)
    parser.add_argument("--risk-acceptance-checklist-json", required=True)
    parser.add_argument("--output-json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = generate_report(
        load_json(args.single_submit_packet_json),
        load_json(args.risk_acceptance_checklist_json),
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
