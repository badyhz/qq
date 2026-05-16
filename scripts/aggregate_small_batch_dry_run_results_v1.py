#!/usr/bin/env python3
import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional


def load_json(path: str) -> Optional[Dict[str, Any]]:
    if not os.path.exists(path):
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


def aggregate(paths: List[str]) -> Dict[str, Any]:
    blockers: List[str] = []
    warnings: List[str] = []
    summaries: List[Dict[str, Any]] = []

    pass_count = 0
    partial_count = 0
    fail_count = 0
    unsafe_count = 0
    submit_executed_count = 0

    for path in paths:
        payload = load_json(path)
        if payload is None:
            blockers.append(f"MALFORMED_JSON:{path}")
            unsafe_count += 1
            continue

        verdict = str(payload.get("verdict", ""))
        env = str(payload.get("env") or payload.get("request_plan", {}).get("env", "")).lower()
        submit_executed = bool(payload.get("submit_executed") is True)
        submit_allowed = bool(payload.get("submit_allowed") is True)

        text = json.dumps(payload, sort_keys=True, ensure_ascii=False).lower()
        mainnet_marker = any(x in text for x in ["api.binance.com", "mainnet", "--live"])

        if verdict == "PASS":
            pass_count += 1
        elif verdict == "PARTIAL":
            partial_count += 1
        else:
            fail_count += 1

        if submit_executed:
            unsafe_count += 1
            submit_executed_count += 1
            blockers.append(f"SUBMIT_EXECUTED_TRUE:{path}")
        if submit_allowed:
            unsafe_count += 1
            blockers.append(f"SUBMIT_ALLOWED_TRUE:{path}")
        if env != "testnet":
            unsafe_count += 1
            blockers.append(f"ENV_NOT_TESTNET:{path}")
        if mainnet_marker:
            unsafe_count += 1
            blockers.append(f"MAINNET_MARKER:{path}")

        summaries.append({
            "path": path,
            "verdict": verdict,
            "env": env,
            "submit_executed": submit_executed,
            "submit_allowed": submit_allowed,
        })

    result_count = len(paths)
    submit_allowed_output = False

    if blockers:
        verdict = "FAIL"
        ok = False
    elif partial_count > 0:
        verdict = "PARTIAL"
        ok = True
    elif fail_count > 0:
        verdict = "FAIL"
        ok = False
    else:
        verdict = "PASS"
        ok = True

    return {
        "ok": ok,
        "verdict": verdict,
        "result_count": result_count,
        "pass_count": pass_count,
        "partial_count": partial_count,
        "fail_count": fail_count,
        "unsafe_count": unsafe_count,
        "submit_executed_count": submit_executed_count,
        "submit_allowed": submit_allowed_output,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "result_summaries": summaries,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Aggregate small batch dry-run results")
    parser.add_argument("--dry-run-result-jsons", nargs="+", required=True)
    parser.add_argument("--output-json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = aggregate(args.dry_run_result_jsons)

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
