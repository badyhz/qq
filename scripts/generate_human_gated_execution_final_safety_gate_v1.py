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


def generate_gate(
    wrapper_eligibility: Optional[Dict[str, Any]],
    dry_run_plan: Optional[Dict[str, Any]],
    token_validation: Optional[Dict[str, Any]],
    preflight_invariant: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    blockers = []
    warnings = []

    payloads = {
        "wrapper_eligibility": wrapper_eligibility,
        "dry_run_plan": dry_run_plan,
        "token_validation": token_validation,
        "preflight_invariant": preflight_invariant,
    }
    for name, value in payloads.items():
        if not isinstance(value, dict):
            blockers.append(f"{name.upper()}_MISSING")

    if str((wrapper_eligibility or {}).get("verdict", "")) != "PASS":
        blockers.append("WRAPPER_ELIGIBILITY_NOT_PASS")
    if str((dry_run_plan or {}).get("verdict", "")) != "PASS":
        blockers.append("DRY_RUN_PLAN_NOT_PASS")
    if str((preflight_invariant or {}).get("verdict", "")) != "PASS":
        blockers.append("PREFLIGHT_NOT_PASS")

    token_verdict = str((token_validation or {}).get("verdict", ""))
    token_matches = bool((token_validation or {}).get("token_matches") is True)

    if any(bool((v or {}).get("submit_allowed") is True) for v in payloads.values()):
        blockers.append("SUBMIT_ALLOWED_TRUE_IN_INPUT")

    gate_status = "BLOCKED"
    if blockers:
        verdict = "FAIL"
        ok = False
    elif token_verdict == "PARTIAL":
        verdict = "PARTIAL"
        ok = False
        gate_status = "NEEDS_REVIEW"
        warnings.append("AWAITING_TOKEN_CONFIRMATION")
    elif not token_matches:
        verdict = "FAIL"
        ok = False
        gate_status = "BLOCKED"
    else:
        verdict = "PASS"
        ok = True
        gate_status = "READY_FOR_HUMAN_EXECUTION"

    return {
        "ok": ok,
        "verdict": verdict,
        "gate_status": gate_status,
        "submit_allowed": False,
        "execution_requires_allow_flag": True,
        "execution_requires_confirm_token": True,
        "execution_requires_env_testnet": True,
        "max_submit_count": 1,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "final_human_checks": [
            "VERIFY_ENV_IS_TESTNET",
            "VERIFY_SYMBOL_SIDE_QUANTITY_ARE_CORRECT",
            "VERIFY_TOKEN_MATCHES_EXACTLY",
            "VERIFY_ALLOW_TESTNET_SUBMIT_FLAG_IS_INTENTIONAL",
            "VERIFY_NO_MAINNET_OR_LIVE_MARKERS",
            "VERIFY_NO_AUTO_OR_REPEAT_SUBMIT",
            "VERIFY_MAX_SUBMIT_COUNT_IS_1",
        ],
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate human-gated execution final safety gate")
    parser.add_argument("--wrapper-eligibility-json", required=True)
    parser.add_argument("--dry-run-plan-json", required=True)
    parser.add_argument("--token-validation-json", required=True)
    parser.add_argument("--preflight-invariant-json", required=True)
    parser.add_argument("--output-json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = generate_gate(
        load_json(args.wrapper_eligibility_json),
        load_json(args.dry_run_plan_json),
        load_json(args.token_validation_json),
        load_json(args.preflight_invariant_json),
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
