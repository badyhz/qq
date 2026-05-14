import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_next_testnet_dry_run_only_iteration_execution_packet_v1 import (
    ITERATION_CONSTRAINTS,
    REQUIRED_BLOCKED_ACTIONS,
    generate_execution_packet,
    load_json,
    write_json,
)


def valid_t475():
    return {
        "ok": True,
        "phase_completion_status": "COMPLETED_TESTNET_DRY_RUN_ITERATION_REVIEW",
        "final_decision": "READY_FOR_NEXT_TESTNET_DRY_RUN_ONLY_ITERATION",
        "safety_flags": {
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


def test_ready_t475_pass(tmp_path):
    r = generate_execution_packet(valid_t475(), "x")
    assert r["ok"] is True
    assert r["execution_packet_status"] == "READY_FOR_NEXT_DRY_RUN_CANDIDATE_INPUT_ARTIFACT"


def test_blocked_t475(tmp_path):
    t475 = valid_t475(); t475["ok"] = False
    r = generate_execution_packet(t475, "x")
    assert r["ok"] is False


def test_constraints_present(tmp_path):
    r = generate_execution_packet(valid_t475(), "x")
    for c in ITERATION_CONSTRAINTS:
        assert c in r["iteration_constraints"]


def test_never_allows_blocked_actions(tmp_path):
    r = generate_execution_packet(valid_t475(), "x")
    for b in REQUIRED_BLOCKED_ACTIONS:
        assert b not in r["allowed_actions"]
        assert b in r["blocked_actions"]


def test_invalid_json(tmp_path):
    p = str(tmp_path / "bad.json")
    with open(p, "w", encoding="utf-8") as f:
        f.write("bad")
    r = generate_execution_packet(load_json(p), p)
    assert r["ok"] is False


def test_missing_file(tmp_path):
    p = str(tmp_path / "missing.json")
    r = generate_execution_packet(load_json(p), p)
    assert r["ok"] is False


def test_cli_smoke(tmp_path):
    p = str(tmp_path / "t475.json")
    out = str(tmp_path / "out.json")
    write_json(p, valid_t475())
    proc = subprocess.Popen([
        sys.executable,
        str(Path(__file__).parent.parent.parent / "scripts" / "generate_next_testnet_dry_run_only_iteration_execution_packet_v1.py"),
        "--iteration-review-phase-report", p,
        "--output", out,
        "--json",
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    proc.communicate()
    assert proc.returncode in [0, 1]
    assert os.path.exists(out)
