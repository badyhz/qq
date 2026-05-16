#!/usr/bin/env python3
import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional


DASHBOARD_TYPE = "ONE_SHOT_SUBMIT_LIFECYCLE_SAFETY_DASHBOARD_V1"


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


def _has_unsafe_marker(data: Any) -> bool:
    if isinstance(data, str):
        lower = data.lower()
        return (
            "mainnet" in lower
            or "live" in lower
            or "api.binance.com" in lower
            or "fapi.binance.com" in lower
        )
    if isinstance(data, dict):
        return any(_has_unsafe_marker(v) for v in data.values())
    if isinstance(data, list):
        return any(_has_unsafe_marker(v) for v in data)
    return False


def generate_safety_dashboard(
    replay_index: Optional[Dict[str, Any]],
    regression_guard: Optional[Dict[str, Any]],
    final_phase: Optional[Dict[str, Any]],
    health_score: Optional[Dict[str, Any]],
    operator_summary: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    blockers: List[str] = []
    warnings: List[str] = []

    payloads = [replay_index, regression_guard, final_phase, health_score, operator_summary]
    labels = [
        "REPLAY_INDEX",
        "REGRESSION_GUARD",
        "FINAL_PHASE",
        "HEALTH_SCORE",
        "OPERATOR_SUMMARY",
    ]
    for label, payload in zip(labels, payloads):
        if not isinstance(payload, dict):
            blockers.append(f"{label}_MISSING")

    if blockers:
        return {
            "ok": False,
            "verdict": "FAIL",
            "dashboard_type": DASHBOARD_TYPE,
            "lifecycle_status": "STOP",
            "safety_tiles": {},
            "readonly": True,
            "submit_allowed": False,
            "cancel_allowed": False,
            "flatten_allowed": False,
            "blockers": sorted(set(blockers)),
            "warnings": sorted(set(warnings)),
            "operator_next_actions": ["restore_required_dashboard_inputs"],
        }

    for payload in payloads:
        if _has_unsafe_marker(payload):
            blockers.append("UNSAFE_MARKER_DETECTED")

    action_allowed = any(
        bool(p.get("submit_allowed")) or bool(p.get("cancel_allowed")) or bool(p.get("flatten_allowed"))
        for p in payloads
    )
    if action_allowed:
        blockers.append("ACTION_PERMISSION_TRUE_NOT_ALLOWED")

    final_decision = str(final_phase.get("decision", ""))
    final_verdict = str(final_phase.get("verdict", ""))
    regression_verdict = str(regression_guard.get("verdict", ""))
    regression_status = str(regression_guard.get("regression_status", ""))
    incident_level = str(health_score.get("incident_level", "NONE"))
    score_value = int(health_score.get("health_score", 0))
    operator_status = str(operator_summary.get("session_status", ""))

    checked_guards = regression_guard.get("checked_guards", [])
    audit_status = "UNKNOWN"
    if isinstance(checked_guards, list):
        for guard in checked_guards:
            if isinstance(guard, dict) and guard.get("name") == "audit_manifest_pass_required_for_healthy_close":
                audit_status = "PASS" if bool(guard.get("passed")) else "FAIL"

    max_submit_count = int(final_phase.get("max_submit_count", 0))
    rollback_required = (
        "ROLLBACK" in final_decision.upper()
        or "ROLLBACK" in operator_status.upper()
        or regression_status == "UNSAFE_REGRESSION"
        or incident_level in ("HIGH", "CRITICAL")
    )

    safety_tiles = {
        "final decision": final_decision,
        "health score": score_value,
        "incident level": incident_level,
        "audit status": audit_status,
        "regression status": regression_status,
        "action permissions": {
            "submit_allowed": False,
            "cancel_allowed": False,
            "flatten_allowed": False,
        },
        "max submit count": max_submit_count,
        "rollback requirement": rollback_required,
    }

    if blockers:
        verdict = "FAIL"
        ok = False
        lifecycle_status = "STOP"
        operator_next_actions = ["stop_and_resolve_blockers"]
    elif rollback_required:
        verdict = "FAIL"
        ok = False
        lifecycle_status = "ROLLBACK_REVIEW"
        operator_next_actions = ["require_human_rollback_review"]
    elif final_decision == "REVIEW" or operator_status == "REVIEW_REQUIRED":
        verdict = "PARTIAL"
        ok = False
        lifecycle_status = "REVIEW"
        operator_next_actions = ["human_review_required_before_archive"]
    elif regression_verdict == "PASS" and final_decision == "CLOSED":
        verdict = "PASS"
        ok = True
        lifecycle_status = "CLOSED_HEALTHY"
        operator_next_actions = ["archive_closeout_snapshot"]
    elif (
        final_decision == "MONITOR"
        or operator_status == "MONITOR"
        or regression_status == "WARNING_DRIFT"
        or final_verdict == "PARTIAL"
    ):
        verdict = "PARTIAL"
        ok = False
        lifecycle_status = "MONITOR"
        operator_next_actions = ["monitor_drift_and_recheck_regression_guards"]
    else:
        verdict = "FAIL"
        ok = False
        lifecycle_status = "STOP"
        operator_next_actions = ["resolve_unknown_lifecycle_state"]

    if lifecycle_status in ("MONITOR", "REVIEW") and verdict == "PARTIAL":
        pass
    elif lifecycle_status in ("ROLLBACK_REVIEW", "STOP") and verdict != "FAIL":
        verdict = "FAIL"
        ok = False

    return {
        "ok": ok,
        "verdict": verdict,
        "dashboard_type": DASHBOARD_TYPE,
        "lifecycle_status": lifecycle_status,
        "safety_tiles": safety_tiles,
        "readonly": True,
        "submit_allowed": False,
        "cancel_allowed": False,
        "flatten_allowed": False,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "operator_next_actions": operator_next_actions,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate one-shot submit lifecycle safety dashboard")
    parser.add_argument("--replay-index-json", required=True)
    parser.add_argument("--regression-guard-json", required=True)
    parser.add_argument("--final-phase-json", required=True)
    parser.add_argument("--health-score-json", required=True)
    parser.add_argument("--operator-summary-json", required=True)
    parser.add_argument("--output-json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = generate_safety_dashboard(
        load_json(args.replay_index_json),
        load_json(args.regression_guard_json),
        load_json(args.final_phase_json),
        load_json(args.health_score_json),
        load_json(args.operator_summary_json),
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
