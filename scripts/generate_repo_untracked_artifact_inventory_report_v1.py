#!/usr/bin/env python3
import argparse
import json
import os
import re
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


def _classify_path(path: str) -> str:
    if path.startswith("scripts/"):
        return "scripts"
    if path.startswith("tests/"):
        return "tests"
    if path.startswith("core/"):
        return "core"
    if path.startswith("docs/"):
        return "docs"
    lower = path.lower()
    if ".csv" in lower:
        return "csv_data"
    if (
        "/logs/" in lower
        or lower.startswith("logs/")
        or "/reports/" in lower
        or lower.startswith("reports/")
        or lower.endswith(".log")
        or lower.endswith(".txt")
    ):
        return "logs_reports"
    if (
        lower.startswith(".claude/")
        or lower.startswith(".codex/")
        or lower.startswith(".trae/")
        or lower.startswith(".agents/")
        or lower.startswith(".npm/")
    ):
        return "config_tooling"
    if lower.endswith(".tmp") or lower.endswith(".temp") or "tmp" in lower.split("/")[-1]:
        return "temp_misc"
    return "unknown"


def _is_secret_risk(path: str) -> bool:
    lower = path.lower()
    secret_keywords = ["key", "secret", "token", "cert", "credential", ".env"]
    for kw in secret_keywords:
        if kw in lower:
            return True
    return False


def _is_large_data_hint(path: str) -> bool:
    lower = path.lower()
    if lower.endswith(".csv"):
        return True
    if lower.endswith(".jsonl"):
        return True
    if lower.endswith(".parquet"):
        return True
    return True


def generate_inventory_report(
    git_status_text: Optional[str] = None,
    repo_root: str = ".",
) -> Dict[str, Any]:
    blockers = []
    warnings = []
    recommendations = []
    categories: Dict[str, List[str]] = {
        "scripts": [],
        "tests": [],
        "core": [],
        "logs_reports": [],
        "csv_data": [],
        "temp_misc": [],
        "config_tooling": [],
        "docs": [],
        "unknown": [],
    }
    important_new_code_files = []
    likely_temp_files = []
    likely_large_data_files = []
    likely_logs_reports = []
    likely_config_or_secret_risk = []

    untracked_paths: List[str] = []

    if git_status_text:
        for line in git_status_text.split("\n"):
            line = line.rstrip()
            if line.startswith("?? "):
                path = line[3:]
                untracked_paths.append(path)

    for path in untracked_paths:
        category = _classify_path(path)
        categories[category].append(path)

        if category in ["scripts", "tests", "core"]:
            important_new_code_files.append(path)
        if category == "temp_misc":
            likely_temp_files.append(path)
        if _is_large_data_hint(path):
            likely_large_data_files.append(path)
        if category == "logs_reports":
            likely_logs_reports.append(path)
        if _is_secret_risk(path):
            likely_config_or_secret_risk.append(path)

    total_untracked = len(untracked_paths)

    if likely_config_or_secret_risk:
        verdict = "FAIL"
        ok = False
        blockers.append("SECRET_RISK_FILES_DETECTED")
        recommendations.append("REVIEW_SECRET_RISK_FILES_BEFORE_GIT_OPERATIONS")
    elif len(categories["unknown"]) > 10 or len(likely_large_data_files) > 20:
        verdict = "PARTIAL"
        ok = False
        warnings.append("MANY_UNKNOWN_OR_LARGE_DATA_FILES_PRESENT")
        recommendations.append("REVIEW_UNKNOWN_FILES_AND_ARCHIVE_LARGE_DATA")
    else:
        verdict = "PASS"
        ok = True

    return {
        "ok": ok,
        "verdict": verdict,
        "report_type": "REPO_UNTRACKED_ARTIFACT_INVENTORY",
        "total_untracked": total_untracked,
        "categories": categories,
        "important_new_code_files": important_new_code_files,
        "likely_temp_files": likely_temp_files,
        "likely_large_data_files": likely_large_data_files,
        "likely_logs_reports": likely_logs_reports,
        "likely_config_or_secret_risk": likely_config_or_secret_risk,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "recommendations": sorted(set(recommendations)),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate repo untracked artifact inventory report")
    parser.add_argument("--git-status-text", help="Path to git status text file, or raw text")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output-json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    git_status_text = None
    if args.git_status_text:
        if os.path.exists(args.git_status_text):
            with open(args.git_status_text, "r", encoding="utf-8") as f:
                git_status_text = f.read()
        else:
            git_status_text = args.git_status_text

    report = generate_inventory_report(git_status_text, args.repo_root)

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
