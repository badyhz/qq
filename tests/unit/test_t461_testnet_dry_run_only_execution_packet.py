import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_testnet_dry_run_only_execution_packet_v1 import (
    EXECUTION_CONSTRAINTS,
    REQUIRED_BLOCKED_ACTIONS,
    generate_execution_packet,
    load_json,
    write_json,
)


def valid_t460() -> dict:
    return {
        "ok": True,
        "phase_completion_status": "COMPLETED_READY_FOR_TESTNET_DRY_RUN_ONLY_EXECUTION",
        "final_decision": "READY_FOR_TESTNET_DRY_RUN_ONLY_EXECUTION",
        "safety_flags": {
            "testnet_dry_run_allowed": True,
            "exchange_api_calls_allowed": False,
            "testnet_submit_allowed": False,
            "real_submit_allowed": False,
            "submit_order_allowed": False,
            "cancel_order_allowed": False,
            "flatten_position_allowed": False,
            "submit_attempted": False,
            "cancel_attempted": False,
            "flatten_attempted": False,
        },
    }


def test_ready_t460_pass(tmp_path):
    p = str(tmp_path / "t460.json")
    write_json(p, valid_t460())
    report = generate_execution_packet(load_json(p), p)
    assert report["ok"] is True
    assert report["execution_packet_status"] == "READY_FOR_NO_SUBMIT_PAYLOAD_MATERIALIZATION"
    assert report["final_decision"] == "READY_FOR_TESTNET_DRY_RUN_NO_SUBMIT_PAYLOAD_MATERIALIZATION"


def test_blocked_t460(tmp_path):
    t460 = valid_t460()
    t460["ok"] = False
    p = str(tmp_path / "t460.json")
    write_json(p, t460)
    report = generate_execution_packet(load_json(p), p)
    assert report["ok"] is False
    assert report["execution_packet_status"] == "BLOCKED"


def test_constraints_present(tmp_path):
    p = str(tmp_path / "t460.json")
    write_json(p, valid_t460())
    report = generate_execution_packet(load_json(p), p)
    for item in EXECUTION_CONSTRAINTS:
        assert item in report["execution_constraints"]


def test_never_allows_blocked_actions(tmp_path):
    p = str(tmp_path / "t460.json")
    write_json(p, valid_t460())
    report = generate_execution_packet(load_json(p), p)
    for b in REQUIRED_BLOCKED_ACTIONS:
        assert b not in report["allowed_actions"]
        assert b in report["blocked_actions"]


def test_invalid_json(tmp_path):
    p = str(tmp_path / "bad.json")
    with open(p, "w", encoding="utf-8") as f:
        f.write("invalid json")
    report = generate_execution_packet(load_json(p), p)
    assert report["ok"] is False


def test_missing_file(tmp_path):
    p = str(tmp_path / "missing.json")
    report = generate_execution_packet(load_json(p), p)
    assert report["ok"] is False


def test_cli_smoke(tmp_path):
    p = str(tmp_path / "t460.json")
    out = str(tmp_path / "out.json")
    write_json(p, valid_t460())
    proc = subprocess.Popen(
        [
            sys.executable,
            str(Path(__file__).parent.parent.parent / "scripts" / "generate_testnet_dry_run_only_execution_packet_v1.py"),
            "--dry-run-only-phase-report",
            p,
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
