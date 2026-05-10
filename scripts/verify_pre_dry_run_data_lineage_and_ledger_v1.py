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
    "VERIFY_DATA_LINEAGE",
    "VERIFY_LEDGER_IDEMPOTENCY",
    "MANUAL_REVIEW_ONLY"
]

BLOCKED_ACTIONS = list(REQUIRED_BLOCKED_ACTIONS)


def verify_data_lineage_and_ledger(
    input_packet: Optional[Dict[str, Any]],
    safety_report: Optional[Dict[str, Any]],
    input_packet_path: str,
    safety_report_path: str
) -> Dict[str, Any]:
    ok = False
    violations: List[str] = []
    notes: List[str] = []

    data_lineage_ok = False
    ledger_idempotency_ok = False
    safety_gate_ok = False

    data_lineage_status = "UNKNOWN"
    ledger_idempotency_status = "UNKNOWN"
    readiness_status = "UNKNOWN"

    data_lineage_summary: Dict[str, Any] = {}
    ledger_summary: Dict[str, Any] = {}
    safety_gate_summary: Dict[str, Any] = {}

    # Check input packet data lineage
    if input_packet:
        data_lineage_summary = {
            "input_status": input_packet.get("input_status", "UNKNOWN"),
            "source_reports": input_packet.get("source_reports", {}),
            "has_gap_summary": "gap_validation_summary" in input_packet,
            "has_manual_summary": "manual_review_summary" in input_packet
        }

        if (input_packet.get("input_status") == "READY_FOR_PRE_DRY_RUN_READINESS_REVIEW" and
                "gap_validation_summary" in input_packet and
                "manual_review_summary" in input_packet and
                input_packet.get("source_reports", {}).get("gap_control_report") and
                input_packet.get("source_reports", {}).get("manual_review_phase_report")):
            data_lineage_ok = True
            data_lineage_status = "DATA_LINEAGE_CONFIRMED"
        else:
            violations.append("DATA_LINEAGE_NOT_CONFIRMED")
            data_lineage_status = "DATA_LINEAGE_NOT_CONFIRMED"
    else:
        violations.append("DATA_LINEAGE_NOT_CONFIRMED")
        data_lineage_status = "DATA_LINEAGE_NOT_CONFIRMED"

    # Check ledger idempotency
    if input_packet:
        gap_summary = input_packet.get("gap_validation_summary", {})
        # Check all possible markers in packet and gap summary
        markers = [
            input_packet.get("ledger_idempotency_status"),
            input_packet.get("ledger_status"),
            input_packet.get("idempotency_status"),
            input_packet.get("validation_ledger_status"),
            input_packet.get("gap_validation_ledger_status"),
            gap_summary.get("ledger_idempotency_status"),
            gap_summary.get("ledger_status"),
            gap_summary.get("idempotency_status"),
            gap_summary.get("validation_ledger_status"),
            gap_summary.get("gap_validation_ledger_status"),
            input_packet.get("ledger_updated"),
            input_packet.get("idempotent_update"),
            gap_summary.get("ledger_updated"),
            gap_summary.get("idempotent_update")
        ]

        ledger_summary = {
            "has_ledger_markers": any(marker is not None for marker in markers),
            "marker_values": [m for m in markers if m is not None]
        }

        # Check if any marker is "IDEMPOTENT" or true
        idempotent_markers = [m for m in markers if m in ["IDEMPOTENT", True]]
        if idempotent_markers:
            ledger_idempotency_ok = True
            ledger_idempotency_status = "LEDGER_IDEMPOTENCY_CONFIRMED"
        else:
            violations.append("LEDGER_IDEMPOTENCY_NOT_CONFIRMED")
            ledger_idempotency_status = "LEDGER_IDEMPOTENCY_NOT_CONFIRMED"
    else:
        violations.append("LEDGER_IDEMPOTENCY_NOT_CONFIRMED")
        ledger_idempotency_status = "LEDGER_IDEMPOTENCY_NOT_CONFIRMED"

    # Check safety gate report
    if safety_report:
        safety_gate_summary = {
            "ok": safety_report.get("ok", False),
            "safety_gate_status": safety_report.get("safety_gate_status", "UNKNOWN"),
            "final_decision": safety_report.get("final_decision", "UNKNOWN")
        }

        if (safety_report.get("ok") is True and
                safety_report.get("safety_gate_status") == "ALL_EXECUTION_GATES_BLOCKED" and
                safety_report.get("final_decision") == "SAFETY_GATES_VERIFIED_FOR_PRE_DRY_RUN_REVIEW"):
            safety_gate_ok = True
        else:
            violations.append("SAFETY_GATES_NOT_VERIFIED")
    else:
        violations.append("SAFETY_GATES_NOT_VERIFIED")
        safety_gate_summary = {
            "ok": False,
            "safety_gate_status": "UNKNOWN",
            "final_decision": "UNKNOWN"
        }

    # Determine final status and decision
    if data_lineage_ok and ledger_idempotency_ok and safety_gate_ok:
        ok = True
        readiness_status = "DATA_AND_LEDGER_READY_FOR_PRE_DRY_RUN_REVIEW"
        final_decision = "DATA_LINEAGE_AND_LEDGER_VERIFIED_FOR_PRE_DRY_RUN_REVIEW"
    else:
        ok = False
        readiness_status = "NOT_READY_FOR_PRE_DRY_RUN_REVIEW"
        final_decision = "BLOCK_PRE_DRY_RUN_REVIEW"

    return {
        "ok": ok,
        "task": "T428",
        "phase": "PRE_DRY_RUN_READINESS_REVIEW",
        "source_reports": {
            "input_packet": input_packet_path,
            "safety_gate_report": safety_report_path
        },
        "data_lineage_status": data_lineage_status,
        "ledger_idempotency_status": ledger_idempotency_status,
        "readiness_status": readiness_status,
        "data_lineage_summary": data_lineage_summary,
        "ledger_summary": ledger_summary,
        "safety_gate_summary": safety_gate_summary,
        "violations": violations,
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
        description="Verify pre-dry-run data lineage and ledger idempotency"
    )
    parser.add_argument("--input-packet", type=str, required=True, help="Path to T426 input packet JSON")
    parser.add_argument("--safety-gate-report", type=str, required=True, help="Path to T427 safety gate report JSON")
    parser.add_argument("--output", type=str, help="Path to write output JSON")
    parser.add_argument("--json", action="store_true", help="Print JSON to stdout")

    args = parser.parse_args(argv)

    input_packet = load_json(args.input_packet)
    safety_report = load_json(args.safety_gate_report)

    report = verify_data_lineage_and_ledger(
        input_packet,
        safety_report,
        args.input_packet,
        args.safety_gate_report
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
