import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Reset global lists in case previous tests modified them
REQUIRED_BLOCKED_ACTIONS_ORIGINAL = [
    "TESTNET_DRY_RUN_ONLY",
    "TESTNET_SUBMIT",
    "REAL_SUBMIT",
    "SUBMIT_ORDER",
    "CANCEL_ORDER",
    "FLATTEN_POSITION"
]

ALLOWED_ACTIONS_ORIGINAL = [
    "READ_REPORTS",
    "GENERATE_PRE_DRY_RUN_READINESS_INPUT_PACKET",
    "MANUAL_REVIEW_ONLY"
]

from scripts.verify_pre_dry_run_safety_gates_v1 import (
    load_json,
    write_json,
    verify_safety_gates,
    main,
    REQUIRED_BLOCKED_ACTIONS,
    ALLOWED_ACTIONS,
    BLOCKED_ACTIONS
)

# Restore the global lists to their original state
REQUIRED_BLOCKED_ACTIONS[:] = REQUIRED_BLOCKED_ACTIONS_ORIGINAL
ALLOWED_ACTIONS[:] = ALLOWED_ACTIONS_ORIGINAL
BLOCKED_ACTIONS[:] = list(REQUIRED_BLOCKED_ACTIONS)


def create_valid_packet():
    return {
        "ok": True,
        "task": "T426",
        "phase": "PRE_DRY_RUN_READINESS_REVIEW",
        "safety_flags": {
            "shadow_only": True,
            "testnet_dry_run_allowed": False,
            "testnet_submit_allowed": False,
            "real_submit_allowed": False,
            "submit_attempted": False,
            "cancel_attempted": False,
            "flatten_attempted": False
        },
        "allowed_actions": list(ALLOWED_ACTIONS),
        "blocked_actions": list(BLOCKED_ACTIONS)
    }


def test_valid_packet(tmp_path):
    packet = create_valid_packet()
    packet_path = str(tmp_path / "input.json")
    write_json(packet_path, packet)

    report = verify_safety_gates(packet, packet_path)

    assert report["ok"] is True
    assert report["safety_gate_status"] == "ALL_EXECUTION_GATES_BLOCKED"
    assert report["final_decision"] == "SAFETY_GATES_VERIFIED_FOR_PRE_DRY_RUN_REVIEW"


def test_testnet_dry_run_allowed_true(tmp_path):
    packet = create_valid_packet()
    packet["safety_flags"]["testnet_dry_run_allowed"] = True
    packet_path = str(tmp_path / "input.json")
    write_json(packet_path, packet)

    report = verify_safety_gates(packet, packet_path)

    assert report["ok"] is False
    assert any("testnet_dry_run_allowed is true" in v for v in report["violations"])


def test_testnet_submit_allowed_true(tmp_path):
    packet = create_valid_packet()
    packet["safety_flags"]["testnet_submit_allowed"] = True
    packet_path = str(tmp_path / "input.json")
    write_json(packet_path, packet)

    report = verify_safety_gates(packet, packet_path)

    assert report["ok"] is False
    assert any("testnet_submit_allowed is true" in v for v in report["violations"])


def test_real_submit_allowed_true(tmp_path):
    packet = create_valid_packet()
    packet["safety_flags"]["real_submit_allowed"] = True
    packet_path = str(tmp_path / "input.json")
    write_json(packet_path, packet)

    report = verify_safety_gates(packet, packet_path)

    assert report["ok"] is False
    assert any("real_submit_allowed is true" in v for v in report["violations"])


def test_submit_attempted_true(tmp_path):
    packet = create_valid_packet()
    packet["safety_flags"]["submit_attempted"] = True
    packet_path = str(tmp_path / "input.json")
    write_json(packet_path, packet)

    report = verify_safety_gates(packet, packet_path)

    assert report["ok"] is False
    assert any("submit_attempted is true" in v for v in report["violations"])


def test_cancel_attempted_true(tmp_path):
    packet = create_valid_packet()
    packet["safety_flags"]["cancel_attempted"] = True
    packet_path = str(tmp_path / "input.json")
    write_json(packet_path, packet)

    report = verify_safety_gates(packet, packet_path)

    assert report["ok"] is False
    assert any("cancel_attempted is true" in v for v in report["violations"])


def test_flatten_attempted_true(tmp_path):
    packet = create_valid_packet()
    packet["safety_flags"]["flatten_attempted"] = True
    packet_path = str(tmp_path / "input.json")
    write_json(packet_path, packet)

    report = verify_safety_gates(packet, packet_path)

    assert report["ok"] is False
    assert any("flatten_attempted is true" in v for v in report["violations"])


def test_allowed_contains_testnet_dry_run(tmp_path):
    packet = create_valid_packet()
    packet["allowed_actions"].append("TESTNET_DRY_RUN_ONLY")
    packet_path = str(tmp_path / "input.json")
    write_json(packet_path, packet)

    report = verify_safety_gates(packet, packet_path)

    assert report["ok"] is False
    assert any("allowed_actions contains TESTNET_DRY_RUN_ONLY" in v for v in report["violations"])


def test_blocked_missing_cancel_order(tmp_path):
    packet = create_valid_packet()
    packet["blocked_actions"].remove("CANCEL_ORDER")
    packet_path = str(tmp_path / "input.json")
    write_json(packet_path, packet)

    report = verify_safety_gates(packet, packet_path)

    assert report["ok"] is False
    assert any("blocked_actions missing CANCEL_ORDER" in v for v in report["violations"])


def test_invalid_json(tmp_path):
    packet_path = str(tmp_path / "input.json")
    with open(packet_path, "w") as f:
        f.write("not valid json")

    report = verify_safety_gates(load_json(packet_path), packet_path)

    assert report["ok"] is False


def test_missing_file(tmp_path):
    packet_path = str(tmp_path / "input.json")

    report = verify_safety_gates(load_json(packet_path), packet_path)

    assert report["ok"] is False


def test_cli_smoke(tmp_path):
    packet = create_valid_packet()
    packet_path = str(tmp_path / "input.json")
    output_path = str(tmp_path / "output.json")
    write_json(packet_path, packet)

    proc = subprocess.Popen(
        [
            sys.executable,
            str(Path(__file__).parent.parent.parent / "scripts" / "verify_pre_dry_run_safety_gates_v1.py"),
            "--input-packet", packet_path,
            "--output", output_path,
            "--json"
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    stdout, stderr = proc.communicate()

    assert proc.returncode in [0, 1]
    assert os.path.exists(output_path)
