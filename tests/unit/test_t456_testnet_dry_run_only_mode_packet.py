import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_testnet_dry_run_only_mode_packet_v1 import (
    DRY_RUN_ONLY_CONSTRAINTS,
    REQUIRED_BLOCKED_ACTIONS,
    generate_mode_packet,
    load_json,
    write_json,
)


def valid_t455() -> dict:
    return {
        "ok": True,
        "phase_completion_status": "COMPLETED_READY_FOR_TESTNET_DRY_RUN_ONLY_MODE",
        "final_decision": "READY_FOR_TESTNET_DRY_RUN_ONLY_MODE",
        "safety_flags": {
            "testnet_dry_run_allowed": True,
            "submit_attempted": False,
            "cancel_attempted": False,
            "flatten_attempted": False,
        },
    }


def test_ready_t455_pass_and_allow_dry_run_only(tmp_path):
    t455_path = str(tmp_path / "t455.json")
    write_json(t455_path, valid_t455())

    report = generate_mode_packet(load_json(t455_path), t455_path)
    assert report["ok"] is True
    assert report["mode_packet_status"] == "READY_FOR_NO_SUBMIT_PAYLOAD_PLAN"
    assert "TESTNET_DRY_RUN_ONLY" in report["allowed_actions"]
    assert report["final_decision"] == "READY_FOR_TESTNET_DRY_RUN_NO_SUBMIT_PAYLOAD_PLAN"


def test_blocked_t455(tmp_path):
    t455 = valid_t455()
    t455["ok"] = False
    t455_path = str(tmp_path / "t455.json")
    write_json(t455_path, t455)

    report = generate_mode_packet(load_json(t455_path), t455_path)
    assert report["ok"] is False
    assert report["mode_packet_status"] == "BLOCKED"
    assert report["safety_flags"]["testnet_dry_run_allowed"] is False


def test_constraints_present(tmp_path):
    t455_path = str(tmp_path / "t455.json")
    write_json(t455_path, valid_t455())

    report = generate_mode_packet(load_json(t455_path), t455_path)
    for item in DRY_RUN_ONLY_CONSTRAINTS:
        assert item in report["dry_run_only_constraints"]


def test_never_allows_submit_cancel_flatten(tmp_path):
    t455_path = str(tmp_path / "t455.json")
    write_json(t455_path, valid_t455())

    report = generate_mode_packet(load_json(t455_path), t455_path)
    for blocked in REQUIRED_BLOCKED_ACTIONS:
        assert blocked not in report["allowed_actions"]
        assert blocked in report["blocked_actions"]


def test_invalid_json(tmp_path):
    p = str(tmp_path / "bad.json")
    with open(p, "w", encoding="utf-8") as f:
        f.write("invalid json")

    report = generate_mode_packet(load_json(p), p)
    assert report["ok"] is False


def test_missing_file(tmp_path):
    p = str(tmp_path / "missing.json")
    report = generate_mode_packet(load_json(p), p)
    assert report["ok"] is False


def test_cli_smoke(tmp_path):
    t455_path = str(tmp_path / "t455.json")
    out = str(tmp_path / "out.json")
    write_json(t455_path, valid_t455())

    proc = subprocess.Popen(
        [
            sys.executable,
            str(Path(__file__).parent.parent.parent / "scripts" / "generate_testnet_dry_run_only_mode_packet_v1.py"),
            "--enablement-phase-report",
            t455_path,
            "--output",
            out,
            "--json",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    proc.communicate()
    assert proc.returncode in [0, 1]
    assert os.path.exists(out)
