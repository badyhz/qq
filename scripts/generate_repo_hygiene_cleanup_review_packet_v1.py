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


def generate_cleanup_packet(
    inventory: Optional[Dict[str, Any]],
    tracking_recommendation: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    blockers = []
    warnings = []
    recommendations = []

    if not isinstance(inventory, dict):
        blockers.append("INVENTORY_JSON_MISSING")

    all_paths = []
    if isinstance(inventory, dict):
        for cat_paths in inventory.get("categories", {}).values():
            all_paths.extend(cat_paths)

    suggested_archive_groups: Dict[str, List[str]] = {
        "csv_data": [],
        "logs_reports": [],
        "temp_misc": [],
        "config_tooling": [],
    }
    for path in all_paths:
        if path.endswith(".csv"):
            suggested_archive_groups["csv_data"].append(path)
        elif (
            path.startswith("logs/")
            or path.startswith("reports/")
            or path.endswith(".log")
            or path.endswith(".txt")
        ):
            suggested_archive_groups["logs_reports"].append(path)
        elif "tmp" in path.lower() or "temp" in path.lower():
            suggested_archive_groups["temp_misc"].append(path)
        elif (
            path.startswith(".claude/")
            or path.startswith(".codex/")
            or path.startswith(".trae/")
            or path.startswith(".agents/")
            or path.startswith(".npm/")
        ):
            suggested_archive_groups["config_tooling"].append(path)

    never_delete_without_manual_review = [
        "core/",
        "scripts/",
        "tests/",
        "docs/",
        "config.yaml",
        "certs/",
        "*.pem",
        "*.key",
        "*.secret",
        ".env*",
    ]

    suggested_ignore_patterns = [
        "logs/",
        "reports/",
        "*.txt",
        "*.csv",
        ".claude/",
        ".codex/",
        ".trae/",
        ".agents/",
        ".npm/",
    ]

    many_temp = (
        len(suggested_archive_groups["csv_data"])
        + len(suggested_archive_groups["logs_reports"])
        + len(suggested_archive_groups["temp_misc"])
    ) > 20

    if blockers:
        verdict = "FAIL"
        ok = False
    elif many_temp:
        verdict = "PARTIAL"
        ok = False
        warnings.append("MANY_TEMP_DATA_FILES_DETECTED")
    else:
        verdict = "PASS"
        ok = True

    return {
        "ok": ok,
        "verdict": verdict,
        "packet_type": "REPO_HYGIENE_CLEANUP_REVIEW",
        "cleanup_mode": "REVIEW_ONLY",
        "delete_allowed": False,
        "archive_allowed": False,
        "suggested_archive_groups": suggested_archive_groups,
        "suggested_ignore_patterns": suggested_ignore_patterns,
        "never_delete_without_manual_review": never_delete_without_manual_review,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "recommendations": recommendations,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate repo hygiene cleanup review packet")
    parser.add_argument("--inventory-json", required=True)
    parser.add_argument("--tracking-recommendation-json")
    parser.add_argument("--output-json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = generate_cleanup_packet(
        load_json(args.inventory_json),
        load_json(args.tracking_recommendation_json) if args.tracking_recommendation_json else None,
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
