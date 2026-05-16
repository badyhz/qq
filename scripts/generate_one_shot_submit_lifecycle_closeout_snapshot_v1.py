#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional


SNAPSHOT_TYPE = "ONE_SHOT_SUBMIT_LIFECYCLE_CLOSEOUT_SNAPSHOT_V1"


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


def _build_digest(payload: Dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def generate_closeout_snapshot(
    replay_index: Optional[Dict[str, Any]],
    regression_guard: Optional[Dict[str, Any]],
    safety_dashboard: Optional[Dict[str, Any]],
    final_phase: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    blockers: List[str] = []
    warnings: List[str] = []

    payloads = [replay_index, regression_guard, safety_dashboard, final_phase]
    labels = ["REPLAY_INDEX", "REGRESSION_GUARD", "SAFETY_DASHBOARD", "FINAL_PHASE"]
    for label, payload in zip(labels, payloads):
        if not isinstance(payload, dict):
            blockers.append(f"{label}_MISSING")

    if blockers:
        now = datetime.utcnow().isoformat() + "Z"
        return {
            "ok": False,
            "verdict": "FAIL",
            "snapshot_type": SNAPSHOT_TYPE,
            "snapshot_id": f"one_shot_snapshot_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_UTC",
            "created_at": now,
            "readonly": True,
            "lifecycle_status": "STOP",
            "final_decision": "STOP",
            "artifact_count": 0,
            "safety_digest": "",
            "submit_allowed": False,
            "cancel_allowed": False,
            "flatten_allowed": False,
            "max_submit_count": 0,
            "blockers": sorted(set(blockers)),
            "warnings": sorted(set(warnings)),
        }

    for payload in payloads:
        if _has_unsafe_marker(payload):
            blockers.append("UNSAFE_MARKER_DETECTED")

    if any(bool(p.get("submit_allowed")) or bool(p.get("cancel_allowed")) or bool(p.get("flatten_allowed")) for p in payloads):
        blockers.append("ACTION_PERMISSION_TRUE_NOT_ALLOWED")

    if int(final_phase.get("max_submit_count", 0)) != 0:
        blockers.append("MAX_SUBMIT_COUNT_NOT_ZERO")

    replay_verdict = str(replay_index.get("verdict", ""))
    guard_verdict = str(regression_guard.get("verdict", ""))
    dashboard_verdict = str(safety_dashboard.get("verdict", ""))
    final_decision = str(final_phase.get("decision", ""))
    lifecycle_status = str(safety_dashboard.get("lifecycle_status", "STOP"))

    monitor_or_review = lifecycle_status in ("MONITOR", "REVIEW")
    rollback_or_stop = lifecycle_status in ("ROLLBACK_REVIEW", "STOP") or "ROLLBACK" in final_decision.upper()

    if rollback_or_stop:
        verdict = "FAIL"
        ok = False
    elif replay_verdict == "PASS" and guard_verdict == "PASS" and dashboard_verdict == "PASS" and final_decision == "CLOSED" and not blockers:
        verdict = "PASS"
        ok = True
    elif monitor_or_review and not blockers:
        verdict = "PARTIAL"
        ok = False
    else:
        verdict = "FAIL"
        ok = False

    digest_payload = {
        "replay_verdict": replay_verdict,
        "guard_verdict": guard_verdict,
        "dashboard_verdict": dashboard_verdict,
        "lifecycle_status": lifecycle_status,
        "final_decision": final_decision,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
    }
    safety_digest = _build_digest(digest_payload)
    created_at = datetime.utcnow().isoformat() + "Z"
    snapshot_id = f"one_shot_snapshot_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_UTC_{safety_digest[:10]}"

    return {
        "ok": ok,
        "verdict": verdict,
        "snapshot_type": SNAPSHOT_TYPE,
        "snapshot_id": snapshot_id,
        "created_at": created_at,
        "readonly": True,
        "lifecycle_status": lifecycle_status,
        "final_decision": final_decision,
        "artifact_count": int(replay_index.get("artifact_count", 0)),
        "safety_digest": safety_digest,
        "submit_allowed": False,
        "cancel_allowed": False,
        "flatten_allowed": False,
        "max_submit_count": 0,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate one-shot submit lifecycle immutable closeout snapshot")
    parser.add_argument("--replay-index-json", required=True)
    parser.add_argument("--regression-guard-json", required=True)
    parser.add_argument("--safety-dashboard-json", required=True)
    parser.add_argument("--final-phase-json", required=True)
    parser.add_argument("--output-json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = generate_closeout_snapshot(
        load_json(args.replay_index_json),
        load_json(args.regression_guard_json),
        load_json(args.safety_dashboard_json),
        load_json(args.final_phase_json),
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
