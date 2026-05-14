import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_testnet_dry_run_result_review_packet_v1 import (
    REQUIRED_BLOCKED_ACTIONS,
    REQUIRED_REVIEW_ITEMS,
    generate_result_review_packet,
    load_json,
    write_json,
)


def valid_t465():
    return {
        "ok": True,
        "phase_completion_status": "COMPLETED_TESTNET_DRY_RUN_ONLY_EXECUTION",
        "final_decision": "READY_FOR_TESTNET_DRY_RUN_RESULT_REVIEW",
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


def test_ready_t465_pass(tmp_path):
    p = str(tmp_path / "t465.json")
    write_json(p, valid_t465())
    r = generate_result_review_packet(load_json(p), p)
    assert r["ok"] is True
    assert r["review_packet_status"] == "READY_FOR_MATERIALIZED_PAYLOAD_CONSISTENCY_REVIEW"


def test_blocked_t465(tmp_path):
    t = valid_t465(); t["ok"] = False
    p = str(tmp_path / "t465.json")
    write_json(p, t)
    r = generate_result_review_packet(load_json(p), p)
    assert r["ok"] is False


def test_required_review_items_present(tmp_path):
    r = generate_result_review_packet(valid_t465(), "x")
    for item in REQUIRED_REVIEW_ITEMS:
        assert item in r["required_review_items"]


def test_never_allows_blocked_actions(tmp_path):
    r = generate_result_review_packet(valid_t465(), "x")
    for b in REQUIRED_BLOCKED_ACTIONS:
        assert b not in r["allowed_actions"]
        assert b in r["blocked_actions"]


def test_invalid_json(tmp_path):
    p = str(tmp_path / "bad.json")
    with open(p, "w", encoding="utf-8") as f:
        f.write("bad")
    r = generate_result_review_packet(load_json(p), p)
    assert r["ok"] is False


def test_missing_file(tmp_path):
    p = str(tmp_path / "missing.json")
    r = generate_result_review_packet(load_json(p), p)
    assert r["ok"] is False


def test_cli_smoke(tmp_path):
    p = str(tmp_path / "t465.json")
    out = str(tmp_path / "out.json")
    write_json(p, valid_t465())
    proc = subprocess.Popen([
        sys.executable,
        str(Path(__file__).parent.parent.parent / "scripts" / "generate_testnet_dry_run_result_review_packet_v1.py"),
        "--execution-phase-report", p,
        "--output", out,
        "--json",
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    proc.communicate()
    assert proc.returncode in [0, 1]
    assert os.path.exists(out)
