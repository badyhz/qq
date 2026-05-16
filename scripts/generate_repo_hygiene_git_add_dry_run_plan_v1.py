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


def _is_blocked(path: str) -> bool:
    lower = path.lower()
    if lower.startswith("logs/"):
        return True
    if lower.startswith("reports/"):
        return True
    if lower.endswith(".csv"):
        return True
    if lower.endswith(".txt"):
        return True
    if lower.startswith(".env"):
        return True
    if lower.startswith("certs/"):
        return True
    if lower.startswith(".claude/"):
        return True
    if lower.startswith(".codex/"):
        return True
    if lower.startswith(".trae/"):
        return True
    if lower.startswith(".agents/"):
        return True
    if lower.startswith(".npm/"):
        return True
    secret_keywords = ["key", "secret", "token", "cert", "credential", ".env"]
    for kw in secret_keywords:
        if kw in lower:
            return True
    return False


def generate_git_add_plan(
    tracking_recommendation: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    blockers = []
    warnings = []

    if not isinstance(tracking_recommendation, dict):
        blockers.append("TRACKING_RECOMMENDATION_JSON_MISSING")
        return {
            "ok": False,
            "verdict": "FAIL",
            "plan_type": "REPO_HYGIENE_GIT_ADD_DRY_RUN",
            "dry_run_only": True,
            "git_add_commands": [],
            "excluded_files": [],
            "blocked_files": [],
            "blockers": sorted(set(blockers)),
            "warnings": [],
            "human_instructions": [],
        }

    track_files = tracking_recommendation.get("recommended_track_files", [])

    safe_files = []
    excluded_files = []
    blocked_files = []

    for path in track_files:
        if _is_blocked(path):
            blocked_files.append(path)
        else:
            safe_files.append(path)

    if blocked_files:
        verdict = "FAIL"
        ok = False
        blockers.append("BLOCKED_FILES_WOULD_BE_ADDED")
    elif not safe_files:
        verdict = "PARTIAL"
        ok = False
        warnings.append("NO_FILES_TO_ADD")
    else:
        verdict = "PASS"
        ok = True

    git_add_commands = []
    if safe_files:
        git_add_commands.append("git add --dry-run scripts/generate_*_v1.py tests/unit/test_t*.py")
        git_add_commands.append("# Or selectively: git add --dry-run <file1> <file2> ...")

    human_instructions = [
        "THIS IS A DRY RUN PLAN ONLY",
        "Review the safe_files list carefully",
        "Run git add --dry-run first to verify",
        "Do NOT add blocked_files",
        "Do NOT add logs/, reports/, *.csv, .env, certs/",
    ]

    return {
        "ok": ok,
        "verdict": verdict,
        "plan_type": "REPO_HYGIENE_GIT_ADD_DRY_RUN",
        "dry_run_only": True,
        "git_add_commands": git_add_commands,
        "safe_files": safe_files,
        "excluded_files": excluded_files,
        "blocked_files": blocked_files,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "human_instructions": human_instructions,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate repo hygiene git add dry-run plan")
    parser.add_argument("--tracking-recommendation-json", required=True)
    parser.add_argument("--output-json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = generate_git_add_plan(load_json(args.tracking_recommendation_json))

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
