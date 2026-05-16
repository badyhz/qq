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


def _has_unsafe_marker(data: Any) -> bool:
    if isinstance(data, str):
        lower = data.lower()
        if "mainnet" in lower or "live" in lower or "api.binance.com" in lower or "fapi.binance.com" in lower:
            return True
    elif isinstance(data, dict):
        for k, v in data.items():
            if _has_unsafe_marker(v):
                return True
    elif isinstance(data, list):
        for item in data:
            if _has_unsafe_marker(item):
                return True
    return False


def generate_safe_flatten_review(
    rollback_eligibility: Optional[Dict[str, Any]],
    readonly_evidence: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    blockers = []
    warnings = []

    if not isinstance(rollback_eligibility, dict):
        blockers.append("ROLLBACK_ELIGIBILITY_MISSING")
    if not isinstance(readonly_evidence, dict):
        blockers.append("READONLY_EVIDENCE_MISSING")

    env = str((readonly_evidence or {}).get("env", "")).strip().lower()
    symbol = str((readonly_evidence or {}).get("symbol", "")).strip()
    side = str((readonly_evidence or {}).get("side", "")).strip()
    quantity = str((readonly_evidence or {}).get("quantity", "")).strip()

    eligible = bool((rollback_eligibility or {}).get("eligible_for_rollback_review", False))

    if _has_unsafe_marker(rollback_eligibility or {}):
        blockers.append("ROLLBACK_ELIGIBILITY_HAS_UNSAFE_MARKER")
    if _has_unsafe_marker(readonly_evidence or {}):
        blockers.append("READONLY_EVIDENCE_HAS_UNSAFE_MARKER")

    if env != "testnet":
        blockers.append("ENV_NOT_TESTNET")
    if not symbol and eligible:
        warnings.append("SYMBOL_MISSING")

    dry_run_template = ""
    if eligible and env == "testnet" and symbol:
        dry_run_template = f"python3 scripts/simulate_testnet_flatten_dry_run_v1.py --env testnet --symbol {symbol} --side {side} --quantity {quantity} --dry-run"

    if any(bool((v or {}).get("submit_allowed") is True) for v in [rollback_eligibility, readonly_evidence]):
        blockers.append("SUBMIT_ALLOWED_TRUE_NOT_PERMITTED")
    if any(bool((v or {}).get("cancel_allowed") is True) for v in [rollback_eligibility, readonly_evidence]):
        blockers.append("CANCEL_ALLOWED_TRUE_NOT_PERMITTED")
    if any(bool((v or {}).get("flatten_allowed") is True) for v in [rollback_eligibility, readonly_evidence]):
        blockers.append("FLATTEN_ALLOWED_TRUE_NOT_PERMITTED")

    if blockers:
        verdict = "FAIL"
        ok = False
    elif eligible and env == "testnet" and symbol:
        verdict = "PASS"
        ok = True
    elif eligible and not symbol:
        verdict = "PARTIAL"
        ok = False
    else:
        verdict = "FAIL"
        ok = False

    return {
        "ok": ok,
        "verdict": verdict,
        "packet_type": "SAFE_FLATTEN_DRY_RUN_REVIEW_ONLY",
        "rollback_review_mode": "REVIEW_ONLY",
        "readonly": True,
        "env": env,
        "symbol": symbol,
        "side": side,
        "quantity": quantity,
        "submit_allowed": False,
        "cancel_allowed": False,
        "flatten_allowed": False,
        "dry_run_flatten_command_template": dry_run_template,
        "forbidden_commands": [
            "confirm flatten",
            "live",
            "mainnet",
            "auto flatten",
            "loop",
            "repeat",
        ],
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "rationale": "review-only dry-run flatten packet; no confirm-flatten command generated",
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate post-human-submit safe flatten dry-run review packet")
    parser.add_argument("--rollback-eligibility-json", required=True)
    parser.add_argument("--readonly-evidence-json", required=True)
    parser.add_argument("--output-json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = generate_safe_flatten_review(
        load_json(args.rollback_eligibility_json),
        load_json(args.readonly_evidence_json),
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
