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


def _has_token_gate(text: Any) -> bool:
    if not isinstance(text, str):
        return False
    return "--allow-testnet-submit" in text and "--confirm-token" in text and "--env testnet" in text


def generate_artifact(
    wrapper_phase: Optional[Dict[str, Any]],
    final_safety_gate: Optional[Dict[str, Any]],
    dry_run_plan: Optional[Dict[str, Any]],
    single_submit_packet: Optional[Dict[str, Any]],
    human_token_packet: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    blockers = []
    warnings = []

    payloads = {
        "wrapper_phase": wrapper_phase,
        "final_safety_gate": final_safety_gate,
        "dry_run_plan": dry_run_plan,
        "single_submit_packet": single_submit_packet,
        "human_token_packet": human_token_packet,
    }
    for name, value in payloads.items():
        if not isinstance(value, dict):
            blockers.append(f"{name.upper()}_MISSING")

    if str((wrapper_phase or {}).get("decision", "")) != "READY_FOR_SINGLE_HUMAN_GATED_TESTNET_EXECUTION":
        blockers.append("WRAPPER_PHASE_NOT_READY")
    if str((final_safety_gate or {}).get("gate_status", "")) != "READY_FOR_HUMAN_EXECUTION":
        blockers.append("FINAL_SAFETY_GATE_NOT_READY")

    env = str((single_submit_packet or {}).get("env", "")).strip()
    symbol = (single_submit_packet or {}).get("symbol", "")
    side = str((single_submit_packet or {}).get("side", "")).strip()
    quantity = (single_submit_packet or {}).get("quantity", "")
    dry_run_command = str((dry_run_plan or {}).get("dry_run_command", ""))
    human_execution_command_template = str((dry_run_plan or {}).get("execution_command_template", ""))

    if env.lower() != "testnet":
        blockers.append("ENV_NOT_TESTNET")
    if _has_live_marker(dry_run_command) or _has_live_marker(human_execution_command_template):
        blockers.append("LIVE_OR_MAINNET_MARKER_FOUND")
    if not _has_token_gate(human_execution_command_template):
        blockers.append("REQUIRED_TOKEN_GATE_MISSING")

    max_submit_count = 1
    if int((single_submit_packet or {}).get("max_submit_count", 1)) > 1:
        blockers.append("MAX_SUBMIT_COUNT_GT_1")
    if int((human_token_packet or {}).get("max_submit_count", 1)) > 1:
        blockers.append("TOKEN_MAX_SUBMIT_COUNT_GT_1")

    if any(bool((v or {}).get("submit_allowed") is True) for v in payloads.values()):
        blockers.append("SUBMIT_ALLOWED_TRUE_IN_INPUT")

    if blockers:
        verdict = "FAIL"
        ok = False
    else:
        verdict = "PASS"
        ok = True

    return {
        "ok": ok,
        "verdict": verdict,
        "artifact_type": "SINGLE_HUMAN_GATED_TESTNET_EXECUTION_WRAPPER",
        "wrapper_mode": "HUMAN_GATED_SINGLE_TESTNET_SUBMIT",
        "env": env,
        "symbol": symbol,
        "side": side,
        "quantity": quantity,
        "submit_allowed": False,
        "max_submit_count": 1,
        "dry_run_command": dry_run_command,
        "human_execution_command_template": human_execution_command_template,
        "required_runtime_inputs": [
            "--allow-testnet-submit",
            "--confirm-token <EXACT_TOKEN>",
            "--env testnet",
        ],
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "safety_notes": [
            "THIS IS A TESTNET-ONLY WRAPPER",
            "REQUIRES EXACT TOKEN MATCH TO EXECUTE",
            "MAX_SUBMIT_COUNT=1",
            "NO AUTO-REPEAT",
            "DEFAULT BEHAVIOR IS DRY-RUN",
        ],
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate single human-gated testnet execution wrapper artifact")
    parser.add_argument("--wrapper-phase-json", required=True)
    parser.add_argument("--final-safety-gate-json", required=True)
    parser.add_argument("--dry-run-plan-json", required=True)
    parser.add_argument("--single-submit-packet-json", required=True)
    parser.add_argument("--human-token-packet-json", required=True)
    parser.add_argument("--output-json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = generate_artifact(
        load_json(args.wrapper_phase_json),
        load_json(args.final_safety_gate_json),
        load_json(args.dry_run_plan_json),
        load_json(args.single_submit_packet_json),
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
