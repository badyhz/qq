import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.verify_pre_dry_run_data_lineage_and_ledger_v1 import (
    load_json,
    write_json,
    verify_data_lineage_and_ledger,
    main,
    REQUIRED_BLOCKED_ACTIONS,
    ALLOWED_ACTIONS,
    BLOCKED_ACTIONS
)


def create_valid_input_packet():
    return {
        "ok": True,
        "task": "T426",
        "phase": "PRE_DRY_RUN_READINESS_REVIEW",
        "input_status": "READY_FOR_PRE_DRY_RUN_READINESS_REVIEW",
        "source_reports": {
            "gap_control_report": "gap_report.json",
            "manual_review_phase_report": "manual_report.json"
        },
        "gap_validation_summary": {
            "ledger_idempotency_status": "IDEMPOTENT"
        },
        "manual_review_summary": {},
        "safety_flags": {
            "shadow_only": True,
            "testnet_dry_run_allowed": False,
            "testnet_submit_allowed": False,
            "real_submit_allowed": False,
            "submit_attempted": False,
            "cancel_attempted": False,
            "flatten_attempted": False
        },
        "allowed_actions": [],
        "blocked_actions": []
    }


def create_valid_safety_report():
    return {
        "ok": True,
        "task": "T427",
        "phase": "PRE_DRY_RUN_READINESS_REVIEW",
        "safety_gate_status": "ALL_EXECUTION_GATES_BLOCKED",
        "final_decision": "SAFETY_GATES_VERIFIED_FOR_PRE_DRY_RUN_REVIEW",
        "safety_flags": {
            "shadow_only": True,
            "testnet_dry_run_allowed": False,
            "testnet_submit_allowed": False,
            "real_submit_allowed": False,
            "submit_attempted": False,
            "cancel_attempted": False,
            "flatten_attempted": False
        }
    }


def test_valid_input_and_safety(tmp_path):
    input_packet = create_valid_input_packet()
    safety_report = create_valid_safety_report()

    input_path = str(tmp_path / "input_packet.json")
    safety_path = str(tmp_path / "safety_report.json")

    write_json(input_path, input_packet)
    write_json(safety_path, safety_report)

    report = verify_data_lineage_and_ledger(input_packet, safety_report, input_path, safety_path)

    assert report["ok"] is True
    assert report["data_lineage_status"] == "DATA_LINEAGE_CONFIRMED"
    assert report["ledger_idempotency_status"] == "LEDGER_IDEMPOTENCY_CONFIRMED"
    assert report["readiness_status"] == "DATA_AND_LEDGER_READY_FOR_PRE_DRY_RUN_REVIEW"
    assert report["final_decision"] == "DATA_LINEAGE_AND_LEDGER_VERIFIED_FOR_PRE_DRY_RUN_REVIEW"


def test_input_status_not_ready(tmp_path):
    input_packet = create_valid_input_packet()
    input_packet["input_status"] = "NOT_READY"
    safety_report = create_valid_safety_report()

    input_path = str(tmp_path / "input_packet.json")
    safety_path = str(tmp_path / "safety_report.json")

    write_json(input_path, input_packet)
    write_json(safety_path, safety_report)

    report = verify_data_lineage_and_ledger(input_packet, safety_report, input_path, safety_path)

    assert report["ok"] is False
    assert any("DATA_LINEAGE_NOT_CONFIRMED" in v for v in report["violations"])


def test_missing_gap_validation_summary(tmp_path):
    input_packet = create_valid_input_packet()
    del input_packet["gap_validation_summary"]
    safety_report = create_valid_safety_report()

    input_path = str(tmp_path / "input_packet.json")
    safety_path = str(tmp_path / "safety_report.json")

    write_json(input_path, input_packet)
    write_json(safety_path, safety_report)

    report = verify_data_lineage_and_ledger(input_packet, safety_report, input_path, safety_path)

    assert report["ok"] is False
    assert any("DATA_LINEAGE_NOT_CONFIRMED" in v for v in report["violations"])


def test_missing_manual_review_summary(tmp_path):
    input_packet = create_valid_input_packet()
    del input_packet["manual_review_summary"]
    safety_report = create_valid_safety_report()

    input_path = str(tmp_path / "input_packet.json")
    safety_path = str(tmp_path / "safety_report.json")

    write_json(input_path, input_packet)
    write_json(safety_path, safety_report)

    report = verify_data_lineage_and_ledger(input_packet, safety_report, input_path, safety_path)

    assert report["ok"] is False
    assert any("DATA_LINEAGE_NOT_CONFIRMED" in v for v in report["violations"])


def test_no_ledger_marker(tmp_path):
    input_packet = create_valid_input_packet()
    del input_packet["gap_validation_summary"]["ledger_idempotency_status"]
    safety_report = create_valid_safety_report()

    input_path = str(tmp_path / "input_packet.json")
    safety_path = str(tmp_path / "safety_report.json")

    write_json(input_path, input_packet)
    write_json(safety_path, safety_report)

    report = verify_data_lineage_and_ledger(input_packet, safety_report, input_path, safety_path)

    assert report["ok"] is False
    assert any("LEDGER_IDEMPOTENCY_NOT_CONFIRMED" in v for v in report["violations"])


def test_safety_ok_false(tmp_path):
    input_packet = create_valid_input_packet()
    safety_report = create_valid_safety_report()
    safety_report["ok"] = False

    input_path = str(tmp_path / "input_packet.json")
    safety_path = str(tmp_path / "safety_report.json")

    write_json(input_path, input_packet)
    write_json(safety_path, safety_report)

    report = verify_data_lineage_and_ledger(input_packet, safety_report, input_path, safety_path)

    assert report["ok"] is False
    assert any("SAFETY_GATES_NOT_VERIFIED" in v for v in report["violations"])


def test_safety_gate_status_wrong(tmp_path):
    input_packet = create_valid_input_packet()
    safety_report = create_valid_safety_report()
    safety_report["safety_gate_status"] = "WRONG_STATUS"

    input_path = str(tmp_path / "input_packet.json")
    safety_path = str(tmp_path / "safety_report.json")

    write_json(input_path, input_packet)
    write_json(safety_path, safety_report)

    report = verify_data_lineage_and_ledger(input_packet, safety_report, input_path, safety_path)

    assert report["ok"] is False
    assert any("SAFETY_GATES_NOT_VERIFIED" in v for v in report["violations"])


def test_allowed_actions_no_blocked(tmp_path):
    input_packet = create_valid_input_packet()
    safety_report = create_valid_safety_report()

    input_path = str(tmp_path / "input_packet.json")
    safety_path = str(tmp_path / "safety_report.json")

    report = verify_data_lineage_and_ledger(input_packet, safety_report, input_path, safety_path)

    for blocked in REQUIRED_BLOCKED_ACTIONS:
        assert blocked not in report["allowed_actions"]


def test_blocked_actions_includes_required(tmp_path):
    input_packet = create_valid_input_packet()
    safety_report = create_valid_safety_report()

    input_path = str(tmp_path / "input_packet.json")
    safety_path = str(tmp_path / "safety_report.json")

    report = verify_data_lineage_and_ledger(input_packet, safety_report, input_path, safety_path)

    for required in REQUIRED_BLOCKED_ACTIONS:
        assert required in report["blocked_actions"]


def test_invalid_input_json(tmp_path):
    input_path = str(tmp_path / "input_packet.json")
    safety_path = str(tmp_path / "safety_report.json")

    with open(input_path, "w") as f:
        f.write("not valid json")
    write_json(safety_path, create_valid_safety_report())

    report = verify_data_lineage_and_ledger(
        load_json(input_path),
        load_json(safety_path),
        input_path,
        safety_path
    )

    assert report["ok"] is False


def test_missing_safety_report(tmp_path):
    input_path = str(tmp_path / "input_packet.json")
    safety_path = str(tmp_path / "safety_report.json")

    write_json(input_path, create_valid_input_packet())

    report = verify_data_lineage_and_ledger(
        load_json(input_path),
        load_json(safety_path),
        input_path,
        safety_path
    )

    assert report["ok"] is False


def test_cli_smoke(tmp_path):
    input_packet = create_valid_input_packet()
    safety_report = create_valid_safety_report()

    input_path = str(tmp_path / "input_packet.json")
    safety_path = str(tmp_path / "safety_report.json")
    output_path = str(tmp_path / "output.json")

    write_json(input_path, input_packet)
    write_json(safety_path, safety_report)

    proc = subprocess.Popen(
        [
            sys.executable,
            str(Path(__file__).parent.parent.parent / "scripts" / "verify_pre_dry_run_data_lineage_and_ledger_v1.py"),
            "--input-packet", input_path,
            "--safety-gate-report", safety_path,
            "--output", output_path,
            "--json"
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    stdout, stderr = proc.communicate()

    assert proc.returncode in [0, 1]
    assert os.path.exists(output_path)
