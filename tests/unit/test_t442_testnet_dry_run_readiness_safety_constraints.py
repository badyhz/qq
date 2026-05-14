import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.verify_testnet_dry_run_readiness_safety_constraints_v1 import (
    load_json,
    write_json,
    verify_safety_constraints,
    main,
    REQUIRED_BLOCKED_ACTIONS,
    ALLOWED_ACTIONS,
    BLOCKED_ACTIONS
)


def create_valid_t441_packet() -> dict:
    return {
        "ok": True,
        "final_decision": "READY_FOR_TESTNET_DRY_RUN_READINESS_SAFETY_CONSTRAINT_REVIEW",
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


def test_valid_t441(tmp_path):
    t441_packet = create_valid_t441_packet()
    t441_path = str(tmp_path / "t441.json")
    write_json(t441_path, t441_packet)

    report = verify_safety_constraints(t441_packet, t441_path)

    assert report["ok"] is True
    assert report["final_decision"] == "READY_FOR_TESTNET_DRY_RUN_ARTIFACT_DEPENDENCY_REVIEW"


def test_t441_ok_false(tmp_path):
    t441_packet = create_valid_t441_packet()
    t441_packet["ok"] = False
    t441_path = str(tmp_path / "t441.json")
    write_json(t441_path, t441_packet)

    report = verify_safety_constraints(t441_packet, t441_path)

    assert report["ok"] is False
    assert "READINESS_INPUT_PACKET_NOT_READY" in report["violations"]


def test_testnet_dry_run_allowed_true(tmp_path):
    t441_packet = create_valid_t441_packet()
    t441_packet["safety_flags"]["testnet_dry_run_allowed"] = True
    t441_path = str(tmp_path / "t441.json")
    write_json(t441_path, t441_packet)

    report = verify_safety_constraints(t441_packet, t441_path)

    assert report["ok"] is False
    assert "TESTNET_DRY_RUN_NOT_BLOCKED" in report["violations"]


def test_testnet_submit_allowed_true(tmp_path):
    t441_packet = create_valid_t441_packet()
    t441_packet["safety_flags"]["testnet_submit_allowed"] = True
    t441_path = str(tmp_path / "t441.json")
    write_json(t441_path, t441_packet)

    report = verify_safety_constraints(t441_packet, t441_path)

    assert report["ok"] is False
    assert "TESTNET_SUBMIT_NOT_BLOCKED" in report["violations"]


def test_real_submit_allowed_true(tmp_path):
    t441_packet = create_valid_t441_packet()
    t441_packet["safety_flags"]["real_submit_allowed"] = True
    t441_path = str(tmp_path / "t441.json")
    write_json(t441_path, t441_packet)

    report = verify_safety_constraints(t441_packet, t441_path)

    assert report["ok"] is False
    assert "REAL_SUBMIT_NOT_BLOCKED" in report["violations"]


def test_submit_attempted_true(tmp_path):
    t441_packet = create_valid_t441_packet()
    t441_packet["safety_flags"]["submit_attempted"] = True
    t441_path = str(tmp_path / "t441.json")
    write_json(t441_path, t441_packet)

    report = verify_safety_constraints(t441_packet, t441_path)

    assert report["ok"] is False
    assert "SUBMIT_ATTEMPTED" in report["violations"]


def test_cancel_attempted_true(tmp_path):
    t441_packet = create_valid_t441_packet()
    t441_packet["safety_flags"]["cancel_attempted"] = True
    t441_path = str(tmp_path / "t441.json")
    write_json(t441_path, t441_packet)

    report = verify_safety_constraints(t441_packet, t441_path)

    assert report["ok"] is False
    assert "CANCEL_ATTEMPTED" in report["violations"]


def test_flatten_attempted_true(tmp_path):
    t441_packet = create_valid_t441_packet()
    t441_packet["safety_flags"]["flatten_attempted"] = True
    t441_path = str(tmp_path / "t441.json")
    write_json(t441_path, t441_packet)

    report = verify_safety_constraints(t441_packet, t441_path)

    assert report["ok"] is False
    assert "FLATTEN_ATTEMPTED" in report["violations"]


def test_allowed_contains_testnet_dry_run(tmp_path):
    t441_packet = create_valid_t441_packet()
    t441_packet["allowed_actions"].append("TESTNET_DRY_RUN_ONLY")
    t441_path = str(tmp_path / "t441.json")
    write_json(t441_path, t441_packet)

    report = verify_safety_constraints(t441_packet, t441_path)

    assert report["ok"] is False
    assert "ALLOWED_ACTION_CONTAINS_BLOCKED_ACTION" in report["violations"]


def test_blocked_missing_cancel_order(tmp_path):
    t441_packet = create_valid_t441_packet()
    t441_packet["blocked_actions"].remove("CANCEL_ORDER")
    t441_path = str(tmp_path / "t441.json")
    write_json(t441_path, t441_packet)

    report = verify_safety_constraints(t441_packet, t441_path)

    assert report["ok"] is False
    assert "BLOCKED_ACTION_MISSING" in report["violations"]


def test_output_safety_flags_always_blocked(tmp_path):
    t441_packet = create_valid_t441_packet()
    t441_packet["safety_flags"]["testnet_dry_run_allowed"] = True
    t441_path = str(tmp_path / "t441.json")
    write_json(t441_path, t441_packet)

    report = verify_safety_constraints(t441_packet, t441_path)

    assert report["safety_flags"]["testnet_dry_run_allowed"] is False
    assert report["safety_flags"]["testnet_submit_allowed"] is False
    assert report["safety_flags"]["real_submit_allowed"] is False
    assert report["safety_flags"]["submit_attempted"] is False
    assert report["safety_flags"]["cancel_attempted"] is False
    assert report["safety_flags"]["flatten_attempted"] is False


def test_invalid_json_clean_failure(tmp_path):
    t441_path = str(tmp_path / "t441.json")
    with open(t441_path, "w") as f:
        f.write("invalid json")

    report = verify_safety_constraints(load_json(t441_path), t441_path)

    assert report["ok"] is False


def test_missing_input_file_clean_failure(tmp_path):
    t441_path = str(tmp_path / "nonexistent.json")

    report = verify_safety_constraints(load_json(t441_path), t441_path)

    assert report["ok"] is False


def test_cli_smoke(tmp_path):
    t441_packet = create_valid_t441_packet()
    t441_path = str(tmp_path / "t441.json")
    write_json(t441_path, t441_packet)
    output_path = str(tmp_path / "output.json")

    proc = subprocess.Popen(
        [
            sys.executable,
            str(Path(__file__).parent.parent.parent / "scripts" / "verify_testnet_dry_run_readiness_safety_constraints_v1.py"),
            "--readiness-input-packet", t441_path,
            "--output", output_path,
            "--json"
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    stdout, stderr = proc.communicate()

    assert proc.returncode in [0, 1]
    assert os.path.exists(output_path)
