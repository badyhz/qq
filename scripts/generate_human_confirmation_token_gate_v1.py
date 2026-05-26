#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, Optional

from core.execution_guards import assert_dry_run_required, normalize_execution_mode


def load_json(path: str) -> Optional[Dict[str, Any]]:
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def write_json(path: str, data: Dict[str, Any]) -> bool:
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, sort_keys=True, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def _extract_check_value(invariant_report: Dict[str, Any], check_name: str) -> Any:
    checks = invariant_report.get("invariant_checks") or []
    for item in checks:
        if item.get("name") == check_name:
            return item.get("value")
    return None


def _extract_symbol_side(invariant_report: Dict[str, Any], risk_delta_report: Dict[str, Any]) -> Dict[str, str]:
    symbol = str(_extract_check_value(invariant_report, "symbol_exists") or "UNKNOWN")
    side = str(_extract_check_value(invariant_report, "side_valid") or "UNKNOWN")
    if symbol == "UNKNOWN":
        for delta in risk_delta_report.get("machine_readable_deltas", []):
            if delta.get("field") == "symbol":
                symbol = str(delta.get("to") or delta.get("from") or "UNKNOWN")
    if side == "UNKNOWN":
        for delta in risk_delta_report.get("machine_readable_deltas", []):
            if delta.get("field") == "side":
                side = str(delta.get("to") or delta.get("from") or "UNKNOWN")
    return {"symbol": symbol, "side": side}


def generate_token_gate(phase_report: Optional[Dict[str, Any]], invariant_report: Optional[Dict[str, Any]], risk_delta_report: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    blockers = []
    warnings = []

    if phase_report is None:
        blockers.append("PHASE_REPORT_LOAD_FAILED")
    if invariant_report is None:
        blockers.append("INVARIANT_REPORT_LOAD_FAILED")
    if risk_delta_report is None:
        blockers.append("RISK_DELTA_REPORT_LOAD_FAILED")

    phase_pass = bool(phase_report and phase_report.get("verdict") == "PASS")
    if not phase_pass:
        blockers.append("PHASE_REPORT_NOT_PASS")

    invariant_pass = bool(invariant_report and invariant_report.get("verdict") == "PASS")
    if not invariant_pass:
        blockers.append("INVARIANT_REPORT_NOT_PASS")

    delta_verdict = str((risk_delta_report or {}).get("verdict", ""))
    if delta_verdict == "FAIL":
        blockers.append("RISK_DELTA_DANGEROUS")

    env_value = str(_extract_check_value(invariant_report or {}, "env_is_testnet") or "").lower()
    if env_value != "testnet":
        blockers.append("ENV_NOT_TESTNET")

    info = _extract_symbol_side(invariant_report or {}, risk_delta_report or {})
    stable_base = f"{info['symbol']}|{info['side']}|{env_value}|{delta_verdict}|{str((phase_report or {}).get('phase', ''))}"
    digest = hashlib.sha256(stable_base.encode("utf-8")).hexdigest()[:8].upper()
    date_tag = datetime.utcnow().strftime("%Y%m%d")
    token = f"TESTNET_SUBMIT_{info['symbol']}_{info['side']}_{date_tag}_{digest}"

    if blockers:
        verdict = "FAIL"
        ok = False
    else:
        verdict = "PASS"
        ok = True

    return {
        "ok": ok,
        "verdict": verdict,
        "confirmation_token": token,
        "token_requirements": [
            "EXACT_MATCH_REQUIRED",
            "REQUIRES_ALLOW_TESTNET_SUBMIT_FLAG",
            "REQUIRES_ENV_TESTNET",
            "SINGLE_USE_RECOMMENDED",
        ],
        "blocking_reasons": sorted(set(blockers)),
        "warnings": warnings,
        "token_context": {"symbol": info["symbol"], "side": info["side"], "env": env_value},
    }


def main(argv=None) -> int:
    mode = normalize_execution_mode(os.environ.get("QQ_RUNTIME_MODE"))
    assert_dry_run_required(mode)

    parser = argparse.ArgumentParser(description="Generate human confirmation token gate")
    parser.add_argument("--inputs", nargs=3, metavar=("PHASE_REPORT", "INVARIANT_REPORT", "RISK_DELTA_REPORT"), required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = generate_token_gate(
        load_json(args.inputs[0]),
        load_json(args.inputs[1]),
        load_json(args.inputs[2]),
    )
    if not write_json(args.output, report):
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
