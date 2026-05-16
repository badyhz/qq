#!/usr/bin/env python3
import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional


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


def _is_recommended_track(path: str) -> bool:
    if path.startswith("scripts/"):
        fn = os.path.basename(path)
        if fn.startswith("generate_") and fn.endswith("_v1.py"):
            return True
        if fn.startswith("verify_") and fn.endswith("_v1.py"):
            return True
        if fn.startswith("aggregate_") and fn.endswith("_v1.py"):
            return True
        if fn.startswith("classify_") and fn.endswith("_v1.py"):
            return True
        if fn.startswith("compare_") and fn.endswith("_v1.py"):
            return True
        if fn.startswith("parse_") and fn.endswith("_v1.py"):
            return True
        if fn.startswith("simulate_") and fn.endswith("_v1.py"):
            return True
    if path.startswith("tests/unit/"):
        fn = os.path.basename(path)
        if fn.startswith("test_t") and fn.endswith(".py"):
            return True
    return False


def _is_recommended_ignore(path: str) -> bool:
    if path.startswith("logs/"):
        return True
    if path.startswith("reports/"):
        return True
    if path.endswith(".csv"):
        return True
    if path.endswith(".txt"):
        return True
    if path.startswith(".claude/"):
        return True
    if path.startswith(".codex/"):
        return True
    if path.startswith(".trae/"):
        return True
    if path.startswith(".agents/"):
        return True
    if path.startswith(".npm/"):
        return True
    if "tmp" in os.path.basename(path).lower() or "temp" in os.path.basename(path).lower():
        return True
    return False


def _is_secret_risk(path: str) -> bool:
    lower = path.lower()
    secret_keywords = ["key", "secret", "token", "cert", "credential", ".env"]
    for kw in secret_keywords:
        if kw in lower:
            return True
    return False


def _is_expected_lifecycle_file(path: str) -> bool:
    if path.startswith("scripts/"):
        fn = os.path.basename(path)
        if fn.startswith("test_t"):
            return False
        for tnum in range(491, 571):
            if f"t{tnum}" in fn.lower():
                return True
    if path.startswith("tests/unit/"):
        fn = os.path.basename(path)
        for tnum in range(491, 571):
            if fn.startswith(f"test_t{tnum}_"):
                return True
    return False


def generate_tracking_recommendation(
    inventory: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    blockers = []
    warnings = []
    rationale: List[str] = []

    if not isinstance(inventory, dict):
        blockers.append("INVENTORY_JSON_MISSING")
        return {
            "ok": False,
            "verdict": "FAIL",
            "report_type": "LIFECYCLE_SCRIPTS_TRACKING_RECOMMENDATION",
            "recommended_track_files": [],
            "recommended_hold_files": [],
            "recommended_ignore_patterns": [],
            "missing_expected_lifecycle_files": [],
            "duplicate_or_suspicious_files": [],
            "blockers": sorted(set(blockers)),
            "warnings": [],
            "rationale": [],
        }

    all_paths = []
    for cat_paths in inventory.get("categories", {}).values():
        all_paths.extend(cat_paths)

    recommended_track_files = []
    recommended_hold_files = []
    missing_expected_lifecycle_files = []
    duplicate_or_suspicious_files = []

    for path in all_paths:
        if _is_secret_risk(path):
            blockers.append(f"SECRET_RISK_FILE_CANNOT_BE_TRACKED: {path}")
            recommended_hold_files.append(path)
        elif _is_recommended_track(path):
            recommended_track_files.append(path)
        elif _is_recommended_ignore(path):
            recommended_hold_files.append(path)
        else:
            recommended_hold_files.append(path)

    if blockers:
        verdict = "FAIL"
        ok = False
    else:
        verdict = "PASS"
        ok = True

    recommended_ignore_patterns = [
        "logs/",
        "reports/",
        "*.csv",
        "*.txt",
        ".claude/",
        ".codex/",
        ".trae/",
        ".agents/",
        ".npm/",
    ]

    return {
        "ok": ok,
        "verdict": verdict,
        "report_type": "LIFECYCLE_SCRIPTS_TRACKING_RECOMMENDATION",
        "recommended_track_files": sorted(recommended_track_files),
        "recommended_hold_files": sorted(recommended_hold_files),
        "recommended_ignore_patterns": recommended_ignore_patterns,
        "missing_expected_lifecycle_files": missing_expected_lifecycle_files,
        "duplicate_or_suspicious_files": duplicate_or_suspicious_files,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "rationale": rationale,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate lifecycle scripts tracking recommendation report")
    parser.add_argument("--inventory-json", required=True)
    parser.add_argument("--output-json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = generate_tracking_recommendation(load_json(args.inventory_json))

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
