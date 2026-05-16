#!/usr/bin/env python3
import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional, Tuple


GUARD_TYPE = "ONE_SHOT_SUBMIT_LIFECYCLE_REGRESSION_GUARD_V1"


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


def _final_is_closed_healthy(final_phase: Dict[str, Any]) -> bool:
    decision = str(final_phase.get("decision", ""))
    return decision == "CLOSED"


def _rollback_required(incident: Dict[str, Any], final_phase: Dict[str, Any]) -> bool:
    if bool(incident.get("rollback_required")):
        return True
    if bool(incident.get("eligible_for_rollback_review")):
        return True
    if "ROLLBACK" in str(incident.get("decision", "")).upper():
        return True
    if "ROLLBACK" in str(final_phase.get("decision", "")).upper():
        return True
    return False


def _get_incident_level(incident: Optional[Dict[str, Any]], final_phase: Optional[Dict[str, Any]]) -> str:
    level = str((incident or {}).get("incident_level", "")).upper().strip()
    if level:
        return level
    return str((final_phase or {}).get("incident_level", "NONE")).upper().strip() or "NONE"


def _append_guard(
    checked_guards: List[Dict[str, Any]],
    name: str,
    passed: bool,
    severity: str,
    detail: str,
    blockers: List[str],
    warnings: List[str],
) -> None:
    checked_guards.append(
        {
            "name": name,
            "passed": passed,
            "severity": severity,
            "detail": detail,
        }
    )
    if passed:
        return
    if severity == "warning":
        warnings.append(f"{name}:{detail}")
    else:
        blockers.append(f"{name}:{detail}")


def generate_regression_guard_report(
    replay_index: Optional[Dict[str, Any]],
    final_phase: Optional[Dict[str, Any]],
    audit_manifest: Optional[Dict[str, Any]],
    incident: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    blockers: List[str] = []
    warnings: List[str] = []
    recommendations: List[str] = []
    checked_guards: List[Dict[str, Any]] = []

    if not isinstance(replay_index, dict):
        blockers.append("REPLAY_INDEX_MISSING")
    if not isinstance(final_phase, dict):
        blockers.append("FINAL_PHASE_MISSING")
    if not isinstance(audit_manifest, dict):
        blockers.append("AUDIT_MANIFEST_MISSING")

    payloads = [p for p in [replay_index, final_phase, audit_manifest, incident] if isinstance(p, dict)]

    if blockers:
        regression_status = "REGRESSION_DETECTED"
        verdict = "FAIL"
        ok = False
        recommendations.append("restore_required_artifacts")
        return {
            "ok": ok,
            "verdict": verdict,
            "guard_type": GUARD_TYPE,
            "regression_status": regression_status,
            "checked_guards": checked_guards,
            "readonly": True,
            "submit_allowed": False,
            "cancel_allowed": False,
            "flatten_allowed": False,
            "blockers": sorted(set(blockers)),
            "warnings": sorted(set(warnings)),
            "recommendations": recommendations,
        }

    _append_guard(
        checked_guards,
        "no_mainnet_live_marker",
        not any(_has_unsafe_marker(p) for p in payloads),
        "unsafe",
        "unsafe_marker_detected" if any(_has_unsafe_marker(p) for p in payloads) else "ok",
        blockers,
        warnings,
    )

    action_allowed = any(bool(p.get("submit_allowed")) or bool(p.get("cancel_allowed")) or bool(p.get("flatten_allowed")) for p in payloads)
    _append_guard(
        checked_guards,
        "no_actions_allowed_after_final_closeout",
        not action_allowed,
        "unsafe",
        "action_permission_true_detected" if action_allowed else "ok",
        blockers,
        warnings,
    )

    final_max_submit = int(final_phase.get("max_submit_count", 0))
    replay_readonly_phase_count = 0
    replay_readonly_phase_nonzero = False
    for art in replay_index.get("artifacts", []):
        if not isinstance(art, dict):
            continue
        if art.get("phase_family") == "POST_HUMAN_SUBMIT_READONLY_VERIFICATION":
            replay_readonly_phase_count += 1
            if int(art.get("max_submit_count", 0)) != 0:
                replay_readonly_phase_nonzero = True

    max_submit_guard_ok = final_max_submit == 0 and not replay_readonly_phase_nonzero
    if replay_readonly_phase_count == 0:
        _append_guard(
            checked_guards,
            "max_submit_count_zero_after_post_submit_verification",
            False,
            "warning",
            "readonly_verification_phase_not_found_in_replay_index",
            blockers,
            warnings,
        )
    else:
        _append_guard(
            checked_guards,
            "max_submit_count_zero_after_post_submit_verification",
            max_submit_guard_ok,
            "unsafe",
            "max_submit_count_not_zero" if not max_submit_guard_ok else "ok",
            blockers,
            warnings,
        )

    incident_level = _get_incident_level(incident, final_phase)
    healthy_closed = _final_is_closed_healthy(final_phase)
    high_cannot_close_healthy = not (incident_level in ("HIGH", "CRITICAL") and healthy_closed)
    _append_guard(
        checked_guards,
        "high_critical_incident_cannot_close_healthy",
        high_cannot_close_healthy,
        "unsafe",
        f"incident_level={incident_level},final_decision={final_phase.get('decision', '')}",
        blockers,
        warnings,
    )

    rollback_required = _rollback_required(incident or {}, final_phase)
    rollback_state_cannot_close = not (rollback_required and healthy_closed)
    _append_guard(
        checked_guards,
        "rollback_required_state_cannot_be_closed",
        rollback_state_cannot_close,
        "unsafe",
        "rollback_required_but_final_closed" if not rollback_state_cannot_close else "ok",
        blockers,
        warnings,
    )

    audit_verdict = str(audit_manifest.get("verdict", ""))
    audit_pass_for_healthy_close = not healthy_closed or audit_verdict == "PASS"
    _append_guard(
        checked_guards,
        "audit_manifest_pass_required_for_healthy_close",
        audit_pass_for_healthy_close,
        "unsafe",
        f"audit_verdict={audit_verdict}" if not audit_pass_for_healthy_close else "ok",
        blockers,
        warnings,
    )

    replay_verdict = str(replay_index.get("verdict", ""))
    _append_guard(
        checked_guards,
        "replay_index_must_not_fail",
        replay_verdict != "FAIL",
        "unsafe",
        f"replay_index_verdict={replay_verdict}",
        blockers,
        warnings,
    )

    unsafe_failure = any(g["severity"] == "unsafe" and not g["passed"] for g in checked_guards)
    warning_only = not unsafe_failure and any(not g["passed"] for g in checked_guards)

    if unsafe_failure:
        regression_status = "UNSAFE_REGRESSION"
        verdict = "FAIL"
        ok = False
        recommendations.extend([
            "block_closeout_and_require_human_review",
            "restore_readonly_and_action_safety_invariants",
        ])
    elif warning_only:
        regression_status = "WARNING_DRIFT"
        verdict = "PARTIAL"
        ok = False
        recommendations.append("review_warning_drift_and_rebaseline_artifacts")
    elif str(final_phase.get("verdict", "")) == "FAIL" or str(audit_manifest.get("verdict", "")) == "FAIL":
        regression_status = "REGRESSION_DETECTED"
        verdict = "FAIL"
        ok = False
        recommendations.append("resolve_phase_or_audit_failures_before_archive")
    else:
        regression_status = "NO_REGRESSION"
        verdict = "PASS"
        ok = True
        recommendations.append("no_regression_detected_ready_for_dashboard")

    return {
        "ok": ok,
        "verdict": verdict,
        "guard_type": GUARD_TYPE,
        "regression_status": regression_status,
        "checked_guards": checked_guards,
        "readonly": True,
        "submit_allowed": False,
        "cancel_allowed": False,
        "flatten_allowed": False,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "recommendations": recommendations,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate one-shot submit lifecycle regression guard report")
    parser.add_argument("--replay-index-json", required=True)
    parser.add_argument("--final-phase-json", required=True)
    parser.add_argument("--audit-manifest-json", required=True)
    parser.add_argument("--incident-json")
    parser.add_argument("--output-json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = generate_regression_guard_report(
        load_json(args.replay_index_json),
        load_json(args.final_phase_json),
        load_json(args.audit_manifest_json),
        load_json(args.incident_json) if args.incident_json else None,
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
