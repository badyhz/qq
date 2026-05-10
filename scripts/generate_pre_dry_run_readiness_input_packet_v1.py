#!/usr/bin/env python3
import argparse
import json
import os
import sys
from typing import Optional, Dict, Any, List


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


def build_packet(
    gap_report: Optional[Dict[str, Any]],
    manual_report: Optional[Dict[str, Any]],
    gap_path: str,
    manual_path: str
) -> Dict[str, Any]:
    ok = False
    input_status = "UNKNOWN"
    gap_blocked = True
    manual_blocked = True
    final_decision = "UNKNOWN"
    notes: List[str] = []

    # Check gap report
    if gap_report:
        readiness = gap_report.get("readiness_status", "")
        final_decision_gap = gap_report.get("final_decision", "")
        if (readiness == "GAP_VALIDATED_PENDING_REVIEW" or
                final_decision_gap == "READY_FOR_MANUAL_REVIEW_AFTER_GAP_VALIDATION"):
            gap_blocked = False
    else:
        notes.append("Missing or invalid gap control report")

    # Check manual review report
    if manual_report:
        phase_completed = manual_report.get("manual_review_phase_completed", False)
        phase_status = manual_report.get("phase_completion_status", "")
        if (phase_completed or
                phase_status == "COMPLETED_PENDING_PRE_DRY_RUN_REVIEW"):
            manual_blocked = False
    else:
        notes.append("Missing or invalid manual review phase report")

    # Determine input status and final decision
    if not gap_blocked and not manual_blocked:
        ok = True
        input_status = "READY_FOR_PRE_DRY_RUN_READINESS_REVIEW"
        final_decision = "READY_FOR_MANUAL_PRE_DRY_RUN_REVIEW_INPUT_PACKET"
    elif not gap_blocked and manual_blocked:
        input_status = "BLOCKED_BY_MANUAL_REVIEW_PHASE"
        final_decision = "CONTINUE_MANUAL_REVIEW"
    elif gap_blocked and not manual_blocked:
        input_status = "BLOCKED_BY_GAP_VALIDATION"
        final_decision = "CONTINUE_SHADOW_COLLECTION"
    else:
        input_status = "BLOCKED_BY_GAP_AND_MANUAL_REVIEW"
        final_decision = "CONTINUE_SHADOW_COLLECTION"

    # Build summaries
    gap_summary = {
        "readiness_status": gap_report.get("readiness_status", "UNKNOWN") if gap_report else "UNKNOWN",
        "final_decision": gap_report.get("final_decision", "UNKNOWN") if gap_report else "UNKNOWN"
    }

    manual_summary = {
        "phase_completed": manual_report.get("manual_review_phase_completed", False) if manual_report else False,
        "phase_completion_status": manual_report.get("phase_completion_status", "UNKNOWN") if manual_report else "UNKNOWN",
        "manual_gate_passed": manual_report.get("manual_gate_passed", False) if manual_report else False
    }

    return {
        "ok": ok,
        "task": "T426",
        "phase": "PRE_DRY_RUN_READINESS_REVIEW",
        "source_reports": {
            "gap_control_report": gap_path,
            "manual_review_phase_report": manual_path
        },
        "input_status": input_status,
        "gap_validation_summary": gap_summary,
        "manual_review_summary": manual_summary,
        "safety_flags": {
            "shadow_only": True,
            "testnet_dry_run_allowed": False,
            "testnet_submit_allowed": False,
            "real_submit_allowed": False,
            "submit_attempted": False,
            "cancel_attempted": False,
            "flatten_attempted": False
        },
        "allowed_actions": [
            "READ_REPORTS",
            "GENERATE_PRE_DRY_RUN_READINESS_INPUT_PACKET",
            "MANUAL_REVIEW_ONLY"
        ],
        "blocked_actions": [
            "TESTNET_DRY_RUN_ONLY",
            "TESTNET_SUBMIT",
            "REAL_SUBMIT",
            "SUBMIT_ORDER",
            "CANCEL_ORDER",
            "FLATTEN_POSITION"
        ],
        "next_phase_candidate": "PRE_DRY_RUN_READINESS_REVIEW",
        "final_decision": final_decision,
        "notes": notes
    }


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        description="Generate pre-dry-run readiness review input packet"
    )
    parser.add_argument("--gap-control-report", type=str, required=True, help="Path to gap control report JSON")
    parser.add_argument("--manual-review-phase-report", type=str, required=True, help="Path to manual review phase report JSON")
    parser.add_argument("--output", type=str, help="Path to write output JSON")
    parser.add_argument("--json", action="store_true", help="Print JSON to stdout")

    args = parser.parse_args(argv)

    gap_report = load_json(args.gap_control_report)
    manual_report = load_json(args.manual_review_phase_report)

    packet = build_packet(
        gap_report,
        manual_report,
        args.gap_control_report,
        args.manual_review_phase_report
    )

    if args.output:
        write_ok = write_json(args.output, packet)
        if not write_ok:
            print("Failed to write output", file=sys.stderr)
            return 1

    if args.json or not args.output:
        print(json.dumps(packet, indent=2, sort_keys=True, ensure_ascii=False))

    return 0 if packet["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
