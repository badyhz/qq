#!/usr/bin/env python3
import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional


REQUIRED_BLOCKED_ACTIONS = [
    "TESTNET_SUBMIT",
    "REAL_SUBMIT",
    "SUBMIT_ORDER",
    "CANCEL_ORDER",
    "FLATTEN_POSITION",
]

SAFE_BASE_FLAGS = {
    "shadow_only": True,
    "testnet_submit_allowed": False,
    "real_submit_allowed": False,
    "submit_attempted": False,
    "cancel_attempted": False,
    "flatten_attempted": False,
}

ALLOWED_ACTIONS_BLOCKED = [
    "READ_REPORTS",
    "GENERATE_TESTNET_DRY_RUN_ENABLEMENT_PHASE_CONTROL_REPORT",
    "MANUAL_REVIEW_ONLY",
]

ALLOWED_ACTIONS_READY = [
    "READ_REPORTS",
    "GENERATE_TESTNET_DRY_RUN_ENABLEMENT_PHASE_CONTROL_REPORT",
    "TESTNET_DRY_RUN_ONLY",
]

BLOCKED_ACTIONS = list(REQUIRED_BLOCKED_ACTIONS)


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
            json.dump(data, f, indent=2, sort_keys=True, ensure_ascii=False)
        return True
    except Exception:
        return False


def _submit_cancel_flatten_block_ok(report: Optional[Dict[str, Any]]) -> bool:
    if not report:
        return False

    safety = report.get("safety_flags") or {}
    if safety.get("testnet_submit_allowed") is not False:
        return False
    if safety.get("real_submit_allowed") is not False:
        return False
    if safety.get("submit_attempted") is not False:
        return False
    if safety.get("cancel_attempted") is not False:
        return False
    if safety.get("flatten_attempted") is not False:
        return False

    allowed = report.get("allowed_actions") or []
    blocked = report.get("blocked_actions") or []

    for item in REQUIRED_BLOCKED_ACTIONS:
        if item in allowed:
            return False
        if item not in blocked:
            return False

    return True


def generate_enablement_phase_control_report(
    enablement_packet: Optional[Dict[str, Any]],
    safety_switch_report: Optional[Dict[str, Any]],
    operator_confirmation_artifact: Optional[Dict[str, Any]],
    final_gate_report: Optional[Dict[str, Any]],
    enablement_packet_path: str,
    safety_switch_report_path: str,
    operator_confirmation_artifact_path: str,
    final_gate_report_path: str,
) -> Dict[str, Any]:
    blockers: List[str] = []

    t451_ok = (
        enablement_packet
        and enablement_packet.get("final_decision")
        == "READY_FOR_TESTNET_DRY_RUN_ENABLEMENT_SAFETY_SWITCH_REVIEW"
    )
    t452_ok = (
        safety_switch_report
        and safety_switch_report.get("final_decision")
        == "READY_FOR_TESTNET_DRY_RUN_OPERATOR_CONFIRMATION"
    )
    t453_ok = (
        operator_confirmation_artifact
        and operator_confirmation_artifact.get("final_decision")
        == "READY_FOR_TESTNET_DRY_RUN_ENABLEMENT_FINAL_GATE"
    )
    t454_ok = (
        final_gate_report
        and final_gate_report.get("final_decision")
        == "READY_FOR_TESTNET_DRY_RUN_ONLY_MODE"
    )

    if not t451_ok:
        blockers.append("T451_ENABLEMENT_PACKET_NOT_READY")
    if not t452_ok:
        blockers.append("T452_SAFETY_SWITCH_NOT_VERIFIED")
    if not t453_ok:
        blockers.append("T453_OPERATOR_CONFIRMATION_NOT_READY")
    if not t454_ok:
        blockers.append("T454_FINAL_GATE_NOT_PASSED")

    submit_cancel_flatten_block_ok = (
        _submit_cancel_flatten_block_ok(enablement_packet)
        and _submit_cancel_flatten_block_ok(safety_switch_report)
        and _submit_cancel_flatten_block_ok(operator_confirmation_artifact)
        and _submit_cancel_flatten_block_ok(final_gate_report)
    )

    if not submit_cancel_flatten_block_ok:
        blockers.append("SUBMIT_CANCEL_FLATTEN_BLOCK_NOT_CONFIRMED")

    all_ok = bool(t451_ok and t452_ok and t453_ok and t454_ok and submit_cancel_flatten_block_ok)

    if all_ok:
        ok = True
        phase_completion_status = "COMPLETED_READY_FOR_TESTNET_DRY_RUN_ONLY_MODE"
        next_phase = "TESTNET_DRY_RUN_ONLY_MODE"
        final_decision = "READY_FOR_TESTNET_DRY_RUN_ONLY_MODE"
        safety_flags = {
            **SAFE_BASE_FLAGS,
            "testnet_dry_run_allowed": True,
        }
        allowed_actions = list(ALLOWED_ACTIONS_READY)
    else:
        ok = False
        phase_completion_status = "BLOCKED"
        next_phase = "TESTNET_DRY_RUN_ENABLEMENT_REVIEW"
        final_decision = "CONTINUE_TESTNET_DRY_RUN_ENABLEMENT_REVIEW"
        safety_flags = {
            **SAFE_BASE_FLAGS,
            "testnet_dry_run_allowed": False,
        }
        allowed_actions = list(ALLOWED_ACTIONS_BLOCKED)

    return {
        "ok": ok,
        "task": "T455",
        "phase": "TESTNET_DRY_RUN_ENABLEMENT_REVIEW",
        "source_reports": {
            "enablement_packet": enablement_packet_path,
            "safety_switch_report": safety_switch_report_path,
            "operator_confirmation_artifact": operator_confirmation_artifact_path,
            "final_gate_report": final_gate_report_path,
        },
        "phase_completion_status": phase_completion_status,
        "current_phase": "TESTNET_DRY_RUN_ENABLEMENT_REVIEW",
        "next_phase": next_phase,
        "component_statuses": {
            "t451": bool(t451_ok),
            "t452": bool(t452_ok),
            "t453": bool(t453_ok),
            "t454": bool(t454_ok),
            "submit_cancel_flatten_block_confirmed": submit_cancel_flatten_block_ok,
        },
        "blockers": blockers,
        "blocker_count": len(blockers),
        "safety_flags": safety_flags,
        "allowed_actions": allowed_actions,
        "blocked_actions": list(BLOCKED_ACTIONS),
        "final_decision": final_decision,
        "notes": [],
    }


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        description="Generate TESTNET_DRY_RUN enablement phase control report"
    )
    parser.add_argument("--enablement-packet", required=True, help="Path to T451 enablement packet JSON")
    parser.add_argument(
        "--safety-switch-report", required=True, help="Path to T452 safety switch report JSON"
    )
    parser.add_argument(
        "--operator-confirmation-artifact",
        required=True,
        help="Path to T453 operator confirmation artifact JSON",
    )
    parser.add_argument("--final-gate-report", required=True, help="Path to T454 final gate report JSON")
    parser.add_argument("--output", help="Path to write output JSON")
    parser.add_argument("--json", action="store_true", help="Print JSON to stdout")
    args = parser.parse_args(argv)

    enablement_packet = load_json(args.enablement_packet)
    safety_switch_report = load_json(args.safety_switch_report)
    operator_confirmation_artifact = load_json(args.operator_confirmation_artifact)
    final_gate_report = load_json(args.final_gate_report)

    report = generate_enablement_phase_control_report(
        enablement_packet,
        safety_switch_report,
        operator_confirmation_artifact,
        final_gate_report,
        args.enablement_packet,
        args.safety_switch_report,
        args.operator_confirmation_artifact,
        args.final_gate_report,
    )

    if args.output:
        if not write_json(args.output, report):
            print("Failed to write output", file=sys.stderr)
            return 1

    if args.json or not args.output:
        print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))

    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
