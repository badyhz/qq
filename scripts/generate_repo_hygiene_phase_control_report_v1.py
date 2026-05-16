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


def generate_phase_control(
    inventory: Optional[Dict[str, Any]],
    tracking_recommendation: Optional[Dict[str, Any]],
    git_add_dry_run_plan: Optional[Dict[str, Any]],
    cleanup_review: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    blockers = []
    warnings = []
    required_next_actions = []

    if not isinstance(inventory, dict):
        blockers.append("INVENTORY_JSON_MISSING")
    if not isinstance(tracking_recommendation, dict):
        blockers.append("TRACKING_RECOMMENDATION_JSON_MISSING")
    if not isinstance(git_add_dry_run_plan, dict):
        blockers.append("GIT_ADD_DRY_RUN_PLAN_JSON_MISSING")
    if not isinstance(cleanup_review, dict):
        blockers.append("CLEANUP_REVIEW_JSON_MISSING")

    inventory_ok = isinstance(inventory, dict) and inventory.get("verdict") != "FAIL"
    tracking_ok = isinstance(tracking_recommendation, dict) and tracking_recommendation.get("verdict") != "FAIL"
    git_plan_ok = isinstance(git_add_dry_run_plan, dict) and git_add_dry_run_plan.get("verdict") == "PASS"
    cleanup_ok = isinstance(cleanup_review, dict) and cleanup_review.get("verdict") != "FAIL"

    has_blockers = blockers or (
        isinstance(inventory, dict) and inventory.get("blockers")
        or isinstance(tracking_recommendation, dict) and tracking_recommendation.get("blockers")
        or isinstance(git_add_dry_run_plan, dict) and git_add_dry_run_plan.get("blockers")
        or isinstance(cleanup_review, dict) and cleanup_review.get("blockers")
    )

    has_warnings = (
        isinstance(inventory, dict) and inventory.get("warnings")
        or isinstance(tracking_recommendation, dict) and tracking_recommendation.get("warnings")
        or isinstance(git_add_dry_run_plan, dict) and git_add_dry_run_plan.get("warnings")
        or isinstance(cleanup_review, dict) and cleanup_review.get("warnings")
    )

    if has_blockers:
        verdict = "FAIL"
        ok = False
        decision = "BLOCKED"
        can_continue = False
        required_next_actions = ["RESOLVE_BLOCKERS_BEFORE_CONTINUING"]
        next_task_recommendation = "resolve_blockers_and_rerun_hygiene_review"
    elif has_warnings:
        verdict = "PARTIAL"
        ok = False
        decision = "REVIEW"
        can_continue = False
        required_next_actions = ["REVIEW_WARNINGS_AND_CONFIRM_SAFE_TO_PROCEED"]
        next_task_recommendation = "human_review_hygiene_reports"
    elif inventory_ok and tracking_ok and git_plan_ok and cleanup_ok:
        verdict = "PASS"
        ok = True
        decision = "READY_FOR_MANUAL_GIT_ADD_REVIEW"
        can_continue = False
        required_next_actions = ["REVIEW_GIT_ADD_DRY_RUN_PLAN"]
        next_task_recommendation = "human_review_and_approve_git_add_plan"
    else:
        verdict = "FAIL"
        ok = False
        decision = "BLOCKED"
        can_continue = False
        required_next_actions = ["COMPLETE_ALL_HYGIENE_REPORTS"]
        next_task_recommendation = "complete_hygiene_reports"

    return {
        "ok": ok,
        "verdict": verdict,
        "phase": "REPO_HYGIENE_REVIEW",
        "decision": decision,
        "can_continue": can_continue,
        "git_mutation_allowed": False,
        "delete_allowed": False,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "required_next_actions": required_next_actions,
        "next_task_recommendation": next_task_recommendation,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate repo hygiene phase control report")
    parser.add_argument("--inventory-json", required=True)
    parser.add_argument("--tracking-recommendation-json", required=True)
    parser.add_argument("--git-add-dry-run-plan-json", required=True)
    parser.add_argument("--cleanup-review-json", required=True)
    parser.add_argument("--output-json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = generate_phase_control(
        load_json(args.inventory_json),
        load_json(args.tracking_recommendation_json),
        load_json(args.git_add_dry_run_plan_json),
        load_json(args.cleanup_review_json),
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
