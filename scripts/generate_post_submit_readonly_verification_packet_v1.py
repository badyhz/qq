#!/usr/bin/env python3
import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional

PHASE = "post_submit_readonly_verification"


def load_json(path: str) -> Optional[Dict[str, Any]]:
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def write_json(path: str, data: Dict[str, Any]) -> bool:
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, sort_keys=True, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def generate_verification_packet(submit_result: Optional[Dict[str, Any]], snapshots: List[Optional[Dict[str, Any]]]) -> Dict[str, Any]:
    blockers: List[str] = []
    warnings: List[str] = []

    if submit_result is None:
        blockers.append("SUBMIT_RESULT_LOAD_FAILED")

    submit_executed = bool((submit_result or {}).get("submit_executed") is True)
    submit_attempted = bool((submit_result or {}).get("submit_attempted") is True)

    position_snapshot = None
    order_snapshot = None
    protection_snapshot = None
    for snap in snapshots:
        if not isinstance(snap, dict):
            continue
        kind = str(snap.get("snapshot_type", ""))
        if kind == "position":
            position_snapshot = snap
        elif kind == "order":
            order_snapshot = snap
        elif kind == "protection":
            protection_snapshot = snap

    readonly_checks = {
        "submit_executed": submit_executed,
        "has_position_snapshot": position_snapshot is not None,
        "has_order_snapshot": order_snapshot is not None,
        "has_protection_snapshot": protection_snapshot is not None,
    }

    if not submit_executed:
        verdict = "PARTIAL"
        ok = True
        warnings.append("SUBMIT_NOT_EXECUTED_DRY_RUN_OR_BLOCKED")
    else:
        has_any_snapshot = position_snapshot is not None or order_snapshot is not None or protection_snapshot is not None
        if not has_any_snapshot:
            verdict = "PARTIAL"
            ok = True
            warnings.append("SNAPSHOTS_MISSING_AFTER_SUBMIT")
        elif protection_snapshot is None:
            verdict = "FAIL"
            ok = False
            blockers.append("PROTECTION_SNAPSHOT_MISSING")
        elif bool(protection_snapshot.get("protection_healthy") is not True):
            verdict = "FAIL"
            ok = False
            blockers.append("PROTECTION_NOT_HEALTHY")
        else:
            verdict = "PASS"
            ok = True

    suggested_next = [
        "READONLY_FETCH_OPEN_ORDERS_SNAPSHOT",
        "READONLY_FETCH_POSITION_SNAPSHOT",
        "READONLY_VALIDATE_PROTECTION_ORDERS",
    ]

    protection_status = {
        "present": protection_snapshot is not None,
        "healthy": bool((protection_snapshot or {}).get("protection_healthy") is True),
    }

    return {
        "ok": ok,
        "verdict": verdict,
        "phase": PHASE,
        "submit_result_summary": {
            "submit_attempted": submit_attempted,
            "submit_executed": submit_executed,
            "submit_result_verdict": (submit_result or {}).get("verdict"),
        },
        "readonly_checks": readonly_checks,
        "protection_status": protection_status,
        "blocking_reasons": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "suggested_next_readonly_checks": suggested_next,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate post-submit readonly verification packet")
    parser.add_argument("--inputs", nargs="+", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    submit_result = load_json(args.inputs[0])
    snapshots = [load_json(path) for path in args.inputs[1:]]
    report = generate_verification_packet(submit_result, snapshots)

    if not write_json(args.output, report):
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
