import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_pre_dry_run_readiness_score_v1 import (
    load_json,
    write_json,
    generate_readiness_score,
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
        "final_decision": "READY_FOR_MANUAL_PRE_DRY_RUN_REVIEW_INPUT_PACKET",
        "source_reports": {},
        "gap_validation_summary": {},
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
        "blocked_actions": list(REQUIRED_BLOCKED_ACTIONS)
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
        },
        "allowed_actions": [],
        "blocked_actions": list(REQUIRED_BLOCKED_ACTIONS)
    }


def create_valid_data_ledger_report():
    return {
        "ok": True,
        "task": "T428",
        "phase": "PRE_DRY_RUN_READINESS_REVIEW",
        "readiness_status": "DATA_AND_LEDGER_READY_FOR_PRE_DRY_RUN_REVIEW",
        "final_decision": "DATA_LINEAGE_AND_LEDGER_VERIFIED_FOR_PRE_DRY_RUN_REVIEW",
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
        "blocked_actions": list(REQUIRED_BLOCKED_ACTIONS)
    }


def test_all_components_pass(tmp_path):
    input_packet = create_valid_input_packet()
    safety_report = create_valid_safety_report()
    data_ledger_report = create_valid_data_ledger_report()

    input_path = str(tmp_path / "input_packet.json")
    safety_path = str(tmp_path / "safety_report.json")
    data_path = str(tmp_path / "data_ledger_report.json")

    write_json(input_path, input_packet)
    write_json(safety_path, safety_report)
    write_json(data_path, data_ledger_report)

    report = generate_readiness_score(
        input_packet,
        safety_report,
        data_ledger_report,
        input_path,
        safety_path,
        data_path
    )

    assert report["ok"] is True
    assert report["readiness_score"] == 100
    assert report["readiness_grade"] == "A"
    assert report["readiness_status"] == "READY_FOR_MANUAL_PRE_DRY_RUN_REVIEW"
    assert report["final_decision"] == "READY_FOR_MANUAL_PRE_DRY_RUN_REVIEW"
    assert len(report["blockers"]) == 0


def test_input_packet_fail(tmp_path):
    input_packet = create_valid_input_packet()
    input_packet["ok"] = False
    safety_report = create_valid_safety_report()
    data_ledger_report = create_valid_data_ledger_report()

    input_path = str(tmp_path / "input_packet.json")
    safety_path = str(tmp_path / "safety_report.json")
    data_path = str(tmp_path / "data_ledger_report.json")

    write_json(input_path, input_packet)
    write_json(safety_path, safety_report)
    write_json(data_path, data_ledger_report)

    report = generate_readiness_score(
        input_packet,
        safety_report,
        data_ledger_report,
        input_path,
        safety_path,
        data_path
    )

    assert report["ok"] is False
    assert report["readiness_score"] == 75
    assert report["readiness_grade"] == "B"
    assert any("INPUT_PACKET_NOT_READY" in b for b in report["blockers"])


def test_safety_gate_fail(tmp_path):
    input_packet = create_valid_input_packet()
    safety_report = create_valid_safety_report()
    safety_report["ok"] = False
    data_ledger_report = create_valid_data_ledger_report()

    input_path = str(tmp_path / "input_packet.json")
    safety_path = str(tmp_path / "safety_report.json")
    data_path = str(tmp_path / "data_ledger_report.json")

    write_json(input_path, input_packet)
    write_json(safety_path, safety_report)
    write_json(data_path, data_ledger_report)

    report = generate_readiness_score(
        input_packet,
        safety_report,
        data_ledger_report,
        input_path,
        safety_path,
        data_path
    )

    assert report["ok"] is False
    assert report["readiness_score"] == 75
    assert report["readiness_grade"] == "B"
    assert any("SAFETY_GATES_NOT_VERIFIED" in b for b in report["blockers"])


def test_data_ledger_fail(tmp_path):
    input_packet = create_valid_input_packet()
    safety_report = create_valid_safety_report()
    data_ledger_report = create_valid_data_ledger_report()
    data_ledger_report["ok"] = False

    input_path = str(tmp_path / "input_packet.json")
    safety_path = str(tmp_path / "safety_report.json")
    data_path = str(tmp_path / "data_ledger_report.json")

    write_json(input_path, input_packet)
    write_json(safety_path, safety_report)
    write_json(data_path, data_ledger_report)

    report = generate_readiness_score(
        input_packet,
        safety_report,
        data_ledger_report,
        input_path,
        safety_path,
        data_path
    )

    assert report["ok"] is False
    assert report["readiness_score"] == 75
    assert report["readiness_grade"] == "B"
    assert any("DATA_LINEAGE_AND_LEDGER_NOT_VERIFIED" in b for b in report["blockers"])


def test_execution_flag_violation(tmp_path):
    input_packet = create_valid_input_packet()
    input_packet["safety_flags"]["testnet_dry_run_allowed"] = True
    safety_report = create_valid_safety_report()
    data_ledger_report = create_valid_data_ledger_report()

    input_path = str(tmp_path / "input_packet.json")
    safety_path = str(tmp_path / "safety_report.json")
    data_path = str(tmp_path / "data_ledger_report.json")

    write_json(input_path, input_packet)
    write_json(safety_path, safety_report)
    write_json(data_path, data_ledger_report)

    report = generate_readiness_score(
        input_packet,
        safety_report,
        data_ledger_report,
        input_path,
        safety_path,
        data_path
    )

    assert report["ok"] is False
    assert any("EXECUTION_BLOCK_NOT_CONFIRMED" in b for b in report["blockers"])


def test_allowed_contains_testnet_dry_run(tmp_path):
    input_packet = create_valid_input_packet()
    input_packet["allowed_actions"].append("TESTNET_DRY_RUN_ONLY")
    safety_report = create_valid_safety_report()
    data_ledger_report = create_valid_data_ledger_report()

    input_path = str(tmp_path / "input_packet.json")
    safety_path = str(tmp_path / "safety_report.json")
    data_path = str(tmp_path / "data_ledger_report.json")

    write_json(input_path, input_packet)
    write_json(safety_path, safety_report)
    write_json(data_path, data_ledger_report)

    report = generate_readiness_score(
        input_packet,
        safety_report,
        data_ledger_report,
        input_path,
        safety_path,
        data_path
    )

    assert report["ok"] is False
    assert any("EXECUTION_BLOCK_NOT_CONFIRMED" in b for b in report["blockers"])


def test_blocked_missing_real_submit(tmp_path):
    input_packet = create_valid_input_packet()
    input_packet["blocked_actions"].remove("REAL_SUBMIT")
    safety_report = create_valid_safety_report()
    data_ledger_report = create_valid_data_ledger_report()

    input_path = str(tmp_path / "input_packet.json")
    safety_path = str(tmp_path / "safety_report.json")
    data_path = str(tmp_path / "data_ledger_report.json")

    write_json(input_path, input_packet)
    write_json(safety_path, safety_report)
    write_json(data_path, data_ledger_report)

    report = generate_readiness_score(
        input_packet,
        safety_report,
        data_ledger_report,
        input_path,
        safety_path,
        data_path
    )

    assert report["ok"] is False
    assert any("EXECUTION_BLOCK_NOT_CONFIRMED" in b for b in report["blockers"])


def test_grade_b_c_d_f(tmp_path):
    # Test grade B (75)
    input_packet = create_valid_input_packet()
    safety_report = create_valid_safety_report()
    data_ledger_report = create_valid_data_ledger_report()
    input_packet["ok"] = False
    input_path = str(tmp_path / "input_packet_b.json")
    safety_path = str(tmp_path / "safety_report_b.json")
    data_path = str(tmp_path / "data_ledger_report_b.json")
    write_json(input_path, input_packet)
    write_json(safety_path, safety_report)
    write_json(data_path, data_ledger_report)
    report = generate_readiness_score(input_packet, safety_report, data_ledger_report, input_path, safety_path, data_path)
    assert report["readiness_grade"] == "B"
    assert report["readiness_score"] == 75

    # Test grade C (50)
    input_packet = create_valid_input_packet()
    safety_report = create_valid_safety_report()
    data_ledger_report = create_valid_data_ledger_report()
    input_packet["ok"] = False
    safety_report["ok"] = False
    input_path = str(tmp_path / "input_packet_c.json")
    safety_path = str(tmp_path / "safety_report_c.json")
    data_path = str(tmp_path / "data_ledger_report_c.json")
    write_json(input_path, input_packet)
    write_json(safety_path, safety_report)
    write_json(data_path, data_ledger_report)
    report = generate_readiness_score(input_packet, safety_report, data_ledger_report, input_path, safety_path, data_path)
    assert report["readiness_grade"] == "C"
    assert report["readiness_score"] == 50

    # Test grade D (25)
    input_packet = create_valid_input_packet()
    safety_report = create_valid_safety_report()
    data_ledger_report = create_valid_data_ledger_report()
    input_packet["ok"] = False
    data_ledger_report["ok"] = False
    input_packet["safety_flags"]["testnet_dry_run_allowed"] = True  # Break execution check
    input_path = str(tmp_path / "input_packet_d.json")
    safety_path = str(tmp_path / "safety_report_d.json")
    data_path = str(tmp_path / "data_ledger_report_d.json")
    write_json(input_path, input_packet)
    write_json(safety_path, safety_report)
    write_json(data_path, data_ledger_report)
    report = generate_readiness_score(input_packet, safety_report, data_ledger_report, input_path, safety_path, data_path)
    assert report["readiness_grade"] == "D"
    assert report["readiness_score"] == 25

    # Test grade F (0)
    input_packet = create_valid_input_packet()
    safety_report = create_valid_safety_report()
    data_ledger_report = create_valid_data_ledger_report()
    input_packet["ok"] = False
    safety_report["ok"] = False
    data_ledger_report["ok"] = False
    input_packet["safety_flags"]["testnet_dry_run_allowed"] = True
    input_path = str(tmp_path / "input_packet_f.json")
    safety_path = str(tmp_path / "safety_report_f.json")
    data_path = str(tmp_path / "data_ledger_report_f.json")
    write_json(input_path, input_packet)
    write_json(safety_path, safety_report)
    write_json(data_path, data_ledger_report)
    report = generate_readiness_score(input_packet, safety_report, data_ledger_report, input_path, safety_path, data_path)
    assert report["readiness_grade"] == "F"
    assert report["readiness_score"] == 0


def test_output_allowed_no_blocked(tmp_path):
    input_packet = create_valid_input_packet()
    safety_report = create_valid_safety_report()
    data_ledger_report = create_valid_data_ledger_report()

    input_path = str(tmp_path / "input_packet.json")
    safety_path = str(tmp_path / "safety_report.json")
    data_path = str(tmp_path / "data_ledger_report.json")

    write_json(input_path, input_packet)
    write_json(safety_path, safety_report)
    write_json(data_path, data_ledger_report)

    report = generate_readiness_score(
        input_packet,
        safety_report,
        data_ledger_report,
        input_path,
        safety_path,
        data_path
    )

    for blocked in REQUIRED_BLOCKED_ACTIONS:
        assert blocked not in report["allowed_actions"]


def test_output_blocked_includes_required(tmp_path):
    input_packet = create_valid_input_packet()
    safety_report = create_valid_safety_report()
    data_ledger_report = create_valid_data_ledger_report()

    input_path = str(tmp_path / "input_packet.json")
    safety_path = str(tmp_path / "safety_report.json")
    data_path = str(tmp_path / "data_ledger_report.json")

    write_json(input_path, input_packet)
    write_json(safety_path, safety_report)
    write_json(data_path, data_ledger_report)

    report = generate_readiness_score(
        input_packet,
        safety_report,
        data_ledger_report,
        input_path,
        safety_path,
        data_path
    )

    for required in REQUIRED_BLOCKED_ACTIONS:
        assert required in report["blocked_actions"]


def test_invalid_json(tmp_path):
    input_path = str(tmp_path / "input_packet.json")
    safety_path = str(tmp_path / "safety_report.json")
    data_path = str(tmp_path / "data_ledger_report.json")

    with open(input_path, "w") as f:
        f.write("not valid json")
    write_json(safety_path, create_valid_safety_report())
    write_json(data_path, create_valid_data_ledger_report())

    report = generate_readiness_score(
        load_json(input_path),
        load_json(safety_path),
        load_json(data_path),
        input_path,
        safety_path,
        data_path
    )

    assert report["ok"] is False


def test_missing_input_file(tmp_path):
    input_path = str(tmp_path / "input_packet.json")
    safety_path = str(tmp_path / "safety_report.json")
    data_path = str(tmp_path / "data_ledger_report.json")

    write_json(safety_path, create_valid_safety_report())
    write_json(data_path, create_valid_data_ledger_report())

    report = generate_readiness_score(
        load_json(input_path),
        load_json(safety_path),
        load_json(data_path),
        input_path,
        safety_path,
        data_path
    )

    assert report["ok"] is False


def test_cli_smoke(tmp_path):
    input_packet = create_valid_input_packet()
    safety_report = create_valid_safety_report()
    data_ledger_report = create_valid_data_ledger_report()

    input_path = str(tmp_path / "input_packet.json")
    safety_path = str(tmp_path / "safety_report.json")
    data_path = str(tmp_path / "data_ledger_report.json")
    output_path = str(tmp_path / "output.json")

    write_json(input_path, input_packet)
    write_json(safety_path, safety_report)
    write_json(data_path, data_ledger_report)

    proc = subprocess.Popen(
        [
            sys.executable,
            str(Path(__file__).parent.parent.parent / "scripts" / "generate_pre_dry_run_readiness_score_v1.py"),
            "--input-packet", input_path,
            "--safety-gate-report", safety_path,
            "--data-ledger-report", data_path,
            "--output", output_path,
            "--json"
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    stdout, stderr = proc.communicate()

    assert proc.returncode in [0, 1]
    assert os.path.exists(output_path)
