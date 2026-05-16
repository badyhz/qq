#!/usr/bin/env python3
import argparse
import json
import os
import sys
from typing import Any, Dict, Optional


ALLOWED_SIDES = {"BUY", "SELL"}


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


def _is_live_marker(url: Any) -> bool:
    if not isinstance(url, str):
        return False
    lower = url.lower()
    return "api.binance.com" in lower or "mainnet" in lower or "live" in lower


def _pick_candidate(candidate_review: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    pref = candidate_review.get("preferred_candidate")
    if isinstance(pref, dict) and pref:
        return pref
    reviewed = candidate_review.get("reviewed_candidates")
    if isinstance(reviewed, list) and reviewed and isinstance(reviewed[0], dict):
        return reviewed[0]
    return None


def generate_packet(
    packet_eligibility: Optional[Dict[str, Any]],
    candidate_review: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    blockers = []
    warnings = []

    if not isinstance(packet_eligibility, dict):
        blockers.append("PACKET_ELIGIBILITY_MISSING")
        packet_eligibility = {}
    if not isinstance(candidate_review, dict):
        blockers.append("CANDIDATE_REVIEW_MISSING")
        candidate_review = {}

    if str(packet_eligibility.get("verdict", "")) != "PASS":
        blockers.append("PACKET_ELIGIBILITY_NOT_PASS")
    if not bool(packet_eligibility.get("eligible_for_packet_generation") is True):
        blockers.append("PACKET_ELIGIBILITY_FALSE")
    if str(candidate_review.get("verdict", "")) != "PASS":
        blockers.append("CANDIDATE_REVIEW_NOT_PASS")

    candidate = _pick_candidate(candidate_review)
    if not isinstance(candidate, dict):
        blockers.append("PREFERRED_CANDIDATE_MISSING")
        candidate = {}

    env = str(candidate.get("env", ""))
    symbol = candidate.get("symbol")
    side = str(candidate.get("side", ""))
    quantity = candidate.get("quantity")
    base_url = candidate.get("base_url")

    if env.lower() != "testnet":
        blockers.append("ENV_NOT_TESTNET")
    if _is_live_marker(base_url):
        blockers.append("MAINNET_OR_LIVE_BASE_URL_MARKER")
    if not symbol:
        blockers.append("SYMBOL_MISSING")
    if side not in ALLOWED_SIDES:
        blockers.append("SIDE_INVALID")
    if quantity in [None, "", 0, 0.0, "0", "0.0"]:
        blockers.append("QUANTITY_MISSING")

    token_source = f"{env}:{symbol}:{side}:{quantity}:COUNT_1"
    dry_run_command = (
        f"python3 scripts/run_testnet_submit_execution_wrapper_v1.py "
        f"--env {env or 'testnet'} --symbol {symbol or 'SYMBOL'} --side {side or 'BUY'} "
        f"--quantity {quantity or 'QTY'} --dry-run"
    )
    manual_submit_command_template = (
        f"python3 scripts/run_testnet_submit_execution_wrapper_v1.py "
        f"--allow-testnet-submit --confirm-token <TOKEN> --env testnet "
        f"--symbol {symbol or 'SYMBOL'} --side {side or 'BUY'} --quantity {quantity or 'QTY'}"
    )

    if blockers:
        verdict = "FAIL"
        ok = False
    else:
        verdict = "PASS"
        ok = True

    return {
        "ok": ok,
        "verdict": verdict,
        "packet_type": "SINGLE_MANUAL_TESTNET_SUBMIT",
        "env": env,
        "symbol": symbol,
        "side": side,
        "quantity": quantity,
        "submit_allowed": False,
        "max_submit_count": 1,
        "dry_run_command": dry_run_command,
        "manual_submit_command_template": manual_submit_command_template,
        "required_flags": ["--allow-testnet-submit", "--confirm-token", "--env testnet"],
        "required_confirmation_token_source": token_source,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "rationale": "single manual packet generation only; execution remains human gated",
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate single manual testnet submit packet")
    parser.add_argument("--packet-eligibility-json", required=True)
    parser.add_argument("--candidate-review-json", required=True)
    parser.add_argument("--output-json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = generate_packet(
        load_json(args.packet_eligibility_json),
        load_json(args.candidate_review_json),
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
