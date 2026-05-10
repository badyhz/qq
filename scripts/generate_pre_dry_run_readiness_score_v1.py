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
    "GENERATE_PRE_DRY_RUN_READINESS_SCORE",
    "MANUAL_REVIEW_ONLY"
]

BLOCKED_ACTIONS = list(REQUIRED_BLOCKED_ACTIONS)


def generate_readiness_score(
    input_packet: Optional[Dict[str, Any]],
    safety_report: Optional[Dict[str, Any]],
    data_ledger_report: Optional[Dict[str, Any]],
    input_path: str,
    safety_path: str,
    data_ledger_path: str
) -> Dict[str, Any]:
    ok = False
    blockers: List[str] = []
    notes: List[str] = []

    component_scores = {
        "input_packet_ready": 0,
        "safety_gates_verified": 0,
        "data_lineage_and_ledger_verified": 0,
        "execution_still_blocked": 0
    }

    component_statuses = {
        "input_packet_ready": "UNKNOWN",
        "safety_gates_verified": "UNKNOWN",
        "data_lineage_and_ledger_verified": "UNKNOWN",
        "execution_still_blocked": "UNKNOWN"
    }

    # Component 1: input_packet_ready (25 pts)
    if input_packet:
        if (input_packet.get("ok") is True and
                input_packet.get("input_status") == "READY_FOR_PRE_DRY_RUN_READINESS_REVIEW" and
                input_packet.get("final_decision") == "READY_FOR_MANUAL_PRE_DRY_RUN_REVIEW_INPUT_PACKET"):
            component_scores["input_packet_ready"] = 25
            component_statuses["input_packet_ready"] = "PASS"
        else:
            blockers.append("INPUT_PACKET_NOT_READY")
            component_statuses["input_packet_ready"] = "FAIL"
    else:
        blockers.append("INPUT_PACKET_NOT_READY")
        component_statuses["input_packet_ready"] = "FAIL"

    # Component 2: safety_gates_verified (25 pts)
    if safety_report:
        if (safety_report.get("ok") is True and
                safety_report.get("safety_gate_status") == "ALL_EXECUTION_GATES_BLOCKED" and
                safety_report.get("final_decision") == "SAFETY_GATES_VERIFIED_FOR_PRE_DRY_RUN_REVIEW"):
            component_scores["safety_gates_verified"] = 25
            component_statuses["safety_gates_verified"] = "PASS"
        else:
            blockers.append("SAFETY_GATES_NOT_VERIFIED")
            component_statuses["safety_gates_verified"] = "FAIL"
    else:
        blockers.append("SAFETY_GATES_NOT_VERIFIED")
        component_statuses["safety_gates_verified"] = "FAIL"

    # Component 3: data_lineage_and_ledger_verified (25 pts)
    if data_ledger_report:
        if (data_ledger_report.get("ok") is True and
                data_ledger_report.get("readiness_status") == "DATA_AND_LEDGER_READY_FOR_PRE_DRY_RUN_REVIEW" and
                data_ledger_report.get("final_decision") == "DATA_LINEAGE_AND_LEDGER_VERIFIED_FOR_PRE_DRY_RUN_REVIEW"):
            component_scores["data_lineage_and_ledger_verified"] = 25
            component_statuses["data_lineage_and_ledger_verified"] = "PASS"
        else:
            blockers.append("DATA_LINEAGE_AND_LEDGER_NOT_VERIFIED")
            component_statuses["data_lineage_and_ledger_verified"] = "FAIL"
    else:
        blockers.append("DATA_LINEAGE_AND_LEDGER_NOT_VERIFIED")
        component_statuses["data_lineage_and_ledger_verified"] = "FAIL"

    # Component 4: execution_still_blocked (25 pts)
    execution_block_ok = True

    # Check safety flags in all reports
    reports = [input_packet, safety_report, data_ledger_report]
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
            # Check allowed actions and blocked actions in report
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
        component_scores["execution_still_blocked"] = 25
        component_statuses["execution_still_blocked"] = "PASS"
    else:
        blockers.append("EXECUTION_BLOCK_NOT_CONFIRMED")
        component_statuses["execution_still_blocked"] = "FAIL"

    # Calculate total score and grade
    total_score = sum(component_scores.values())
    if total_score == 100:
        grade = "A"
    elif 75 <= total_score < 100:
        grade = "B"
    elif 50 <= total_score < 75:
        grade = "C"
    elif 1 <= total_score < 50:
        grade = "D"
    else:
        grade = "F"

    # Determine final decision
    if total_score == 100:
        ok = True
        readiness_status = "READY_FOR_MANUAL_PRE_DRY_RUN_REVIEW"
        final_decision = "READY_FOR_MANUAL_PRE_DRY_RUN_REVIEW"
    else:
        ok = False
        readiness_status = "BLOCKED"
        final_decision = "BLOCK_PRE_DRY_RUN_REVIEW"

    return {
        "ok": ok,
        "task": "T429",
        "phase": "PRE_DRY_RUN_READINESS_REVIEW",
        "source_reports": {
            "input_packet": input_path,
            "safety_gate_report": safety_path,
            "data_ledger_report": data_ledger_path
        },
        "readiness_score": total_score,
        "readiness_grade": grade,
        "readiness_status": readiness_status,
        "blocker_count": len(blockers),
        "blockers": blockers,
        "component_scores": component_scores,
        "component_statuses": component_statuses,
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
        description="Generate pre-dry-run readiness score"
    )
    parser.add_argument("--input-packet", type=str, required=True, help="Path to T426 input packet JSON")
    parser.add_argument("--safety-gate-report", type=str, required=True, help="Path to T427 safety gate report JSON")
    parser.add_argument("--data-ledger-report", type=str, required=True, help="Path to T428 data/ledger report JSON")
    parser.add_argument("--output", type=str, help="Path to write output JSON")
    parser.add_argument("--json", action="store_true", help="Print JSON to stdout")

    args = parser.parse_args(argv)

    input_packet = load_json(args.input_packet)
    safety_report = load_json(args.safety_gate_report)
    data_ledger_report = load_json(args.data_ledger_report)

    report = generate_readiness_score(
        input_packet,
        safety_report,
        data_ledger_report,
        args.input_packet,
        args.safety_gate_report,
        args.data_ledger_report
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
