#!/usr/bin/env python3
import argparse
import json
import os
import sys
from typing import Any, Dict, Optional


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


def generate_recommendation(incident: Optional[Dict[str, Any]], evidence: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    blockers = []
    warnings = []

    if incident is None:
        blockers.append("INCIDENT_INPUT_MALFORMED_OR_MISSING")
        return {
            "ok": False,
            "verdict": "FAIL",
            "recommendation": "REVIEW_REQUIRED",
            "safe_commands": [],
            "forbidden_commands": ["EXECUTE_FLATTEN_NOW", "AUTO_CANCEL_ALL"],
            "blockers": blockers,
            "warnings": warnings,
            "rationale": "incident input missing",
        }

    level = str(incident.get("incident_level", ""))
    symbol = (evidence or {}).get("symbol") or incident.get("evidence_refs", {}).get("symbol") or "<SYMBOL>"

    dry_flatten_template = (
        "DRY_TEMPLATE_ONLY: python3 scripts/safe_flatten_testnet_symbol.py "
        f"--symbol {symbol} --dry-run --env testnet"
    )

    if level == "NONE":
        recommendation = "NO_ACTION"
        verdict = "PASS"
        ok = True
        safe_commands = ["READONLY_MONITOR_ONLY"]
        rationale = "no incident"
    elif level == "LOW":
        recommendation = "MONITOR_ONLY"
        verdict = "PARTIAL"
        ok = True
        safe_commands = ["READONLY_MONITOR_ONLY"]
        rationale = "low-severity warnings"
    elif level == "MEDIUM":
        recommendation = "REVIEW_REQUIRED"
        verdict = "PARTIAL"
        ok = False
        safe_commands = ["MANUAL_REVIEW_CHECKLIST"]
        rationale = "medium incident needs manual review"
    elif level == "HIGH":
        recommendation = "GENERATE_SAFE_FLATTEN_DRY_RUN"
        verdict = "PARTIAL"
        ok = False
        safe_commands = [dry_flatten_template]
        rationale = "high incident requires dry-run flatten preparation"
    elif level == "CRITICAL":
        recommendation = "MANUAL_CONFIRM_FLATTEN_REQUIRED"
        verdict = "FAIL"
        ok = False
        safe_commands = [dry_flatten_template]
        rationale = "critical incident requires manual flatten confirmation"
    else:
        recommendation = "REVIEW_REQUIRED"
        verdict = "FAIL"
        ok = False
        safe_commands = []
        blockers.append("INCIDENT_LEVEL_UNKNOWN")
        rationale = "unknown incident level"

    forbidden_commands = [
        "EXECUTE_FLATTEN_NOW",
        "AUTO_FLATTEN_WITHOUT_CONFIRM",
        "EXECUTE_CANCEL_ALL_NOW",
        "REAL_MAINNET_SUBMIT",
    ]

    return {
        "ok": ok,
        "verdict": verdict,
        "recommendation": recommendation,
        "safe_commands": safe_commands,
        "forbidden_commands": forbidden_commands,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "rationale": rationale,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate first testnet submit rollback recommendation")
    parser.add_argument("--incident-json", required=True)
    parser.add_argument("--evidence-json")
    parser.add_argument("--output-json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = generate_recommendation(load_json(args.incident_json), load_json(args.evidence_json) if args.evidence_json else None)

    if args.output_json:
        if not write_json(args.output_json, report):
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
