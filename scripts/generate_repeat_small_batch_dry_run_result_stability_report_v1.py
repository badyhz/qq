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


def _pass_rate(agg: Dict[str, Any]) -> float:
    total = int(agg.get("result_count", 0) or 0)
    passed = int(agg.get("pass_count", 0) or 0)
    if total <= 0:
        return 0.0
    return passed / total


def _has_unsafe_marker(agg: Dict[str, Any]) -> bool:
    if int(agg.get("submit_executed_count", 0) or 0) > 0:
        return True
    if bool(agg.get("submit_allowed") is True):
        return True
    if int(agg.get("unsafe_count", 0) or 0) > 0:
        return True
    for item in agg.get("result_summaries", []) if isinstance(agg.get("result_summaries"), list) else []:
        if not isinstance(item, dict):
            continue
        env = str(item.get("env", "")).lower()
        if env and env != "testnet":
            return True
        text = json.dumps(item, sort_keys=True, ensure_ascii=False).lower()
        if "mainnet" in text or "api.binance.com" in text:
            return True
    return False


def generate_report(
    previous_aggregate: Optional[Dict[str, Any]],
    repeat_aggregate: Optional[Dict[str, Any]],
    previous_risk: Optional[Dict[str, Any]] = None,
    repeat_risk: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    blockers = []
    warnings = []

    if previous_aggregate is None:
        blockers.append("PREVIOUS_AGGREGATE_MALFORMED_OR_MISSING")
    if repeat_aggregate is None:
        blockers.append("REPEAT_AGGREGATE_MALFORMED_OR_MISSING")

    if blockers:
        return {
            "ok": False,
            "verdict": "FAIL",
            "stability_status": "UNSAFE",
            "previous_result_count": 0,
            "repeat_result_count": 0,
            "pass_rate_delta": 0.0,
            "unsafe_count_delta": 0,
            "concentration_change": None,
            "blockers": sorted(set(blockers)),
            "warnings": warnings,
            "recommendations": ["FIX_MALFORMED_INPUTS"],
        }

    if _has_unsafe_marker(previous_aggregate) or _has_unsafe_marker(repeat_aggregate):
        blockers.append("UNSAFE_MARKER_DETECTED_IN_AGGREGATES")

    prev_count = int(previous_aggregate.get("result_count", 0) or 0)
    rep_count = int(repeat_aggregate.get("result_count", 0) or 0)
    pass_rate_delta = _pass_rate(repeat_aggregate) - _pass_rate(previous_aggregate)
    unsafe_count_delta = int(repeat_aggregate.get("unsafe_count", 0) or 0) - int(previous_aggregate.get("unsafe_count", 0) or 0)

    conc_prev = str((previous_risk or {}).get("concentration_status", "")) if previous_risk else None
    conc_rep = str((repeat_risk or {}).get("concentration_status", "")) if repeat_risk else None
    concentration_change = {"previous": conc_prev, "repeat": conc_rep} if previous_risk or repeat_risk else None

    if str(previous_aggregate.get("verdict", "")) != "PASS" or str(repeat_aggregate.get("verdict", "")) != "PASS":
        warnings.append("ONE_OR_BOTH_AGGREGATES_NOT_PASS")

    significant_pass_rate_drift = abs(pass_rate_delta) >= 0.2
    if significant_pass_rate_drift:
        warnings.append("SIGNIFICANT_PASS_RATE_DRIFT")

    concentration_worse_to_high = conc_rep == "HIGH" and conc_prev in ["LOW", "MEDIUM", "PASS", "PARTIAL", None]
    if concentration_worse_to_high:
        warnings.append("CONCENTRATION_WORSENED_TO_HIGH")

    if blockers:
        verdict = "FAIL"
        ok = False
        status = "UNSAFE"
    elif significant_pass_rate_drift or concentration_worse_to_high or warnings:
        verdict = "PARTIAL"
        ok = True
        status = "DRIFT_DETECTED"
    else:
        verdict = "PASS"
        ok = True
        status = "STABLE"

    recommendations = []
    if verdict == "PASS":
        recommendations.append("CONTINUE_REPEAT_DRY_RUN_VALIDATION")
    elif verdict == "PARTIAL":
        recommendations.append("REVIEW_DRIFT_BEFORE_NEXT_REPEAT")
    else:
        recommendations.append("STOP_AND_MANUAL_REVIEW")

    return {
        "ok": ok,
        "verdict": verdict,
        "stability_status": status,
        "previous_result_count": prev_count,
        "repeat_result_count": rep_count,
        "pass_rate_delta": pass_rate_delta,
        "unsafe_count_delta": unsafe_count_delta,
        "concentration_change": concentration_change,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "recommendations": recommendations,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate repeat small batch dry-run result stability report")
    parser.add_argument("--previous-result-aggregate-json", required=True)
    parser.add_argument("--repeat-result-aggregate-json", required=True)
    parser.add_argument("--previous-risk-concentration-json")
    parser.add_argument("--repeat-risk-concentration-json")
    parser.add_argument("--output-json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = generate_report(
        load_json(args.previous_result_aggregate_json),
        load_json(args.repeat_result_aggregate_json),
        load_json(args.previous_risk_concentration_json) if args.previous_risk_concentration_json else None,
        load_json(args.repeat_risk_concentration_json) if args.repeat_risk_concentration_json else None,
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
