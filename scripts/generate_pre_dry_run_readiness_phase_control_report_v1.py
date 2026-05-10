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


REQUIRED_BLOCKED_ACTIONS = [
    "TESTNET_DRY_RUN_ONLY",
    "TESTNET_SUBMIT",
    "REAL_SUBMIT",
    "SUBMIT_ORDER",
    "CANCEL_ORDER",
    "FLATTEN_POSITION"
]

ALLOWED_ACTIONS = [
    "READ_REPORTS",
    "GENERATE_PRE_DRY_RUN_READINESS_PHASE_CONTROL_REPORT",
    "MANUAL_REVIEW_ONLY"
]

BLOCKED_ACTIONS = list(REQUIRED_BLOCKED_ACTIONS)


def generate_phase_control_report(
    input_packet: Optional[Dict[str, Any]],
    safety_report: Optional[Dict[str, Any]],
    data_ledger_report: Optional[Dict[str, Any]],
    score_report: Optional[Dict[str, Any]],
    input_path: str,
    safety_path: str,
    data_ledger_path: str,
    score_path: str
) -> Dict[str, Any]:
    ok = False
    blockers: List[str] = []
    notes: List[str] = []

    component_statuses = {
        "T426": "UNKNOWN",
        "T427": "UNKNOWN",
        "T428": "UNKNOWN",
        "T429": "UNKNOWN",
        "EXECUTION_BLOCK": "UNKNOWN"
    }

    readiness_score = 0
    readiness_grade = "UNKNOWN"

    # Check each component
    # T426
    if input_packet:
        if (input_packet.get("ok") is True and
                input_packet.get("final_decision") == "READY_FOR_MANUAL_PRE_DRY_RUN_REVIEW_INPUT_PACKET"):
            component_statuses["T426"] = "PASS"
        else:
            component_statuses["T426"] = "FAIL"
            blockers.append("T426_INPUT_PACKET_NOT_READY")
    else:
        component_statuses["T426"] = "FAIL"
        blockers.append("T426_INPUT_PACKET_NOT_READY")

    # T427
    if safety_report:
        if (safety_report.get("ok") is True and
                safety_report.get("final_decision") == "SAFETY_GATES_VERIFIED_FOR_PRE_DRY_RUN_REVIEW"):
            component_statuses["T427"] = "PASS"
        else:
            component_statuses["T427"] = "FAIL"
            blockers.append("T427_SAFETY_GATES_NOT_VERIFIED")
    else:
        component_statuses["T427"] = "FAIL"
        blockers.append("T427_SAFETY_GATES_NOT_VERIFIED")

    # T428
    if data_ledger_report:
        if (data_ledger_report.get("ok") is True and
                data_ledger_report.get("final_decision") == "DATA_LINEAGE_AND_LEDGER_VERIFIED_FOR_PRE_DRY_RUN_REVIEW"):
            component_statuses["T428"] = "PASS"
        else:
            component_statuses["T428"] = "FAIL"
            blockers.append("T428_DATA_LEDGER_NOT_VERIFIED")
    else:
        component_statuses["T428"] = "FAIL"
        blockers.append("T428_DATA_LEDGER_NOT_VERIFIED")

    # T429
    if score_report:
        readiness_score = score_report.get("readiness_score", 0)
        readiness_grade = score_report.get("readiness_grade", "UNKNOWN")
        if (score_report.get("ok") is True and
                score_report.get("readiness_score") == 100 and
                score_report.get("final_decision") == "READY_FOR_MANUAL_PRE_DRY_RUN_REVIEW"):
            component_statuses["T429"] = "PASS"
        else:
            component_statuses["T429"] = "FAIL"
            blockers.append("T429_READINESS_SCORE_NOT_READY")
    else:
        component_statuses["T429"] = "FAIL"
        blockers.append("T429_READINESS_SCORE_NOT_READY")

    # Check execution block
    execution_block_ok = True
    reports = [input_packet, safety_report, data_ledger_report, score_report]
    for report in reports:
        if report:
            sf = report.get("safety_flags", {})
            if (sf.get("testnet_dry_run_allowed") is True or
                    sf.get("testnet_submit_allowed") is True or
                    sf.get("real_submit_allowed") is True or
                    sf.get("submit_attempted") is True or
                    sf.get("cancel_attempted") is True or
                    sf.get("flatten_attempted") is True):
                execution_block_ok = False
                break
            allowed = report.get("allowed_actions", [])
            for blocked in REQUIRED_BLOCKED_ACTIONS:
                if blocked in allowed:
                    execution_block_ok = False
                    break
            if not execution_block_ok:
                break
            blocked_reported = report.get("blocked_actions", [])
            for required in REQUIRED_BLOCKED_ACTIONS:
                if required not in blocked_reported:
                    execution_block_ok = False
                    break
            if not execution_block_ok:
                break

    if execution_block_ok:
        component_statuses["EXECUTION_BLOCK"] = "PASS"
    else:
        component_statuses["EXECUTION_BLOCK"] = "FAIL"
        blockers.append("EXECUTION_BLOCK_NOT_CONFIRMED")

    # Determine final decision
    if (component_statuses["T426"] == "PASS" and
            component_statuses["T427"] == "PASS" and
            component_statuses["T428"] == "PASS" and
            component_statuses["T429"] == "PASS" and
            component_statuses["EXECUTION_BLOCK"] == "PASS"):
        ok = True
        phase_completion_status = "COMPLETED_PENDING_MANUAL_PRE_DRY_RUN_REVIEW"
        current_phase = "PRE_DRY_RUN_READINESS_REVIEW"
        next_phase = "MANUAL_PRE_DRY_RUN_REVIEW"
        final_decision = "READY_FOR_MANUAL_PRE_DRY_RUN_REVIEW"
    else:
        ok = False
        phase_completion_status = "BLOCKED"
        current_phase = "PRE_DRY_RUN_READINESS_REVIEW"
        next_phase = "PRE_DRY_RUN_READINESS_REVIEW"
        final_decision = "CONTINUE_PRE_DRY_RUN_READINESS_REVIEW"

    return {
        "ok": ok,
        "task": "T430",
        "phase": "PRE_DRY_RUN_READINESS_REVIEW",
        "source_reports": {
            "input_packet": input_path,
            "safety_gate_report": safety_path,
            "data_ledger_report": data_ledger_path,
            "readiness_score_report": score_path
        },
        "phase_completion_status": phase_completion_status,
        "current_phase": current_phase,
        "next_phase": next_phase,
        "component_statuses": component_statuses,
        "readiness_score": readiness_score,
        "readiness_grade": readiness_grade,
        "blockers": blockers,
        "blocker_count": len(blockers),
        "safety_flags": {
            "shadow_only": True,
            "testnet_dry_run_allowed": False,
            "testnet_submit_allowed": False,
            "real_submit_allowed": False,
            "submit_attempted": False,
            "cancel_attempted": False,
            "flatten_attempted": False
        },
        "allowed_actions": ALLOWED_ACTIONS,
        "blocked_actions": BLOCKED_ACTIONS,
        "final_decision": final_decision,
        "notes": notes
    }


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        description="Generate PRE_DRY_RUN_READINESS_REVIEW phase control report"
    )
    parser.add_argument("--input-packet", type=str, required=True, help="Path to T426 input packet JSON")
    parser.add_argument("--safety-gate-report", type=str, required=True, help="Path to T427 safety gate report JSON")
    parser.add_argument("--data-ledger-report", type=str, required=True, help="Path to T428 data/ledger report JSON")
    parser.add_argument("--readiness-score-report", type=str, required=True, help="Path to T429 readiness score report JSON")
    parser.add_argument("--output", type=str, help="Path to write output JSON")
    parser.add_argument("--json", action="store_true", help="Print JSON to stdout")

    args = parser.parse_args(argv)

    input_packet = load_json(args.input_packet)
    safety_report = load_json(args.safety_gate_report)
    data_ledger_report = load_json(args.data_ledger_report)
    score_report = load_json(args.readiness_score_report)

    report = generate_phase_control_report(
        input_packet,
        safety_report,
        data_ledger_report,
        score_report,
        args.input_packet,
        args.safety_gate_report,
        args.data_ledger_report,
        args.readiness_score_report
    )

    if args.output:
        write_ok = write_json(args.output, report)
        if not write_ok:
            print("Failed to write output", file=sys.stderr)
            return 1

    if args.json or not args.output:
        print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))

    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
