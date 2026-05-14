import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_testnet_dry_run_readiness_input_packet_v1 import (
    load_json,
    write_json,
    generate_readiness_input_packet,
    main,
    REQUIRED_BLOCKED_ACTIONS,
    ALLOWED_ACTIONS,
    BLOCKED_ACTIONS,
    REQUIRED_READINESS_ITEMS
)


def create_valid_t440_report() -> dict:
    return {
        "ok": True,
        "phase_completion_status": "COMPLETED_PENDING_TESTNET_DRY_RUN_READINESS_REVIEW",
        "final_decision": "READY_FOR_TESTNET_DRY_RUN_READINESS_REVIEW"
    }


def create_blocked_t440_report() -> dict:
    return {
        "ok": False,
        "phase_completion_status": "CONTINUE",
        "final_decision": "NOT_READY"
    }


def test_ready_t440(tmp_path):
    t440_report = create_valid_t440_report()
    t440_path = str(tmp_path / "t440.json")
    write_json(t440_path, t440_report)

    report = generate_readiness_input_packet(t440_report, t440_path)

    assert report["ok"] is True
    assert report["final_decision"] == "READY_FOR_TESTNET_DRY_RUN_READINESS_SAFETY_CONSTRAINT_REVIEW"


def test_blocked_t440(tmp_path):
    t440_report = create_blocked_t440_report()
    t440_path = str(tmp_path / "t440.json")
    write_json(t440_path, t440_report)

    report = generate_readiness_input_packet(t440_report, t440_path)

    assert report["ok"] is False
    assert report["final_decision"] == "CONTINUE_TESTNET_DRY_RUN_PLANNING_REVIEW"


def test_required_readiness_items_present(tmp_path):
    t440_report = create_valid_t440_report()
    t440_path = str(tmp_path / "t440.json")
    write_json(t440_path, t440_report)

    report = generate_readiness_input_packet(t440_report, t440_path)

    for item in REQUIRED_READINESS_ITEMS:
        assert item in report["required_readiness_items"]


def test_safety_flags_always_blocked(tmp_path):
    t440_report = create_valid_t440_report()
    t440_path = str(tmp_path / "t440.json")
    write_json(t440_path, t440_report)

    report = generate_readiness_input_packet(t440_report, t440_path)

    assert report["safety_flags"]["testnet_dry_run_allowed"] is False
    assert report["safety_flags"]["testnet_submit_allowed"] is False
    assert report["safety_flags"]["real_submit_allowed"] is False
    assert report["safety_flags"]["submit_attempted"] is False
    assert report["safety_flags"]["cancel_attempted"] is False
    assert report["safety_flags"]["flatten_attempted"] is False


def test_allowed_actions_has_no_blocked(tmp_path):
    t440_report = create_valid_t440_report()
    t440_path = str(tmp_path / "t440.json")
    write_json(t440_path, t440_report)

    report = generate_readiness_input_packet(t440_report, t440_path)

    for blocked in REQUIRED_BLOCKED_ACTIONS:
        assert blocked not in report["allowed_actions"]


def test_blocked_actions_includes_required(tmp_path):
    t440_report = create_valid_t440_report()
    t440_path = str(tmp_path / "t440.json")
    write_json(t440_path, t440_report)

    report = generate_readiness_input_packet(t440_report, t440_path)

    for required in REQUIRED_BLOCKED_ACTIONS:
        assert required in report["blocked_actions"]


def test_invalid_json_clean_failure(tmp_path):
    t440_path = str(tmp_path / "t440.json")
    with open(t440_path, "w") as f:
        f.write("invalid json")

    report = generate_readiness_input_packet(load_json(t440_path), t440_path)

    assert report["ok"] is False


def test_missing_input_file_clean_failure(tmp_path):
    t440_path = str(tmp_path / "nonexistent.json")

    report = generate_readiness_input_packet(load_json(t440_path), t440_path)

    assert report["ok"] is False


def test_cli_smoke(tmp_path):
    t440_report = create_valid_t440_report()
    t440_path = str(tmp_path / "t440.json")
    write_json(t440_path, t440_report)
    output_path = str(tmp_path / "output.json")

    proc = subprocess.Popen(
        [
            sys.executable,
            str(Path(__file__).parent.parent.parent / "scripts" / "generate_testnet_dry_run_readiness_input_packet_v1.py"),
            "--planning-phase-report", t440_path,
            "--output", output_path,
            "--json"
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    stdout, stderr = proc.communicate()

    assert proc.returncode in [0, 1]
    assert os.path.exists(output_path)
