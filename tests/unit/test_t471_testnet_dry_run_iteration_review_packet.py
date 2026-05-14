import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_testnet_dry_run_iteration_review_packet_v1 import (
    REQUIRED_BLOCKED_ACTIONS,
    REQUIRED_ITERATION_REVIEW_ITEMS,
    generate_iteration_review_packet,
    load_json,
    write_json,
)


def valid_t470():
    return {
        "ok": True,
        "phase_completion_status": "COMPLETED_TESTNET_DRY_RUN_RESULT_REVIEW",
        "final_decision": "READY_FOR_TESTNET_DRY_RUN_ITERATION_REVIEW",
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


def test_ready_t470_pass(tmp_path):
    report = generate_iteration_review_packet(valid_t470(), "x")
    assert report["ok"] is True
    assert report["final_decision"] == "READY_FOR_DRY_RUN_RESULT_BLOCKER_ANALYSIS"


def test_blocked_t470(tmp_path):
    t470 = valid_t470(); t470["ok"] = False
    report = generate_iteration_review_packet(t470, "x")
    assert report["ok"] is False


def test_required_items_present(tmp_path):
    report = generate_iteration_review_packet(valid_t470(), "x")
    for item in REQUIRED_ITERATION_REVIEW_ITEMS:
        assert item in report["required_iteration_review_items"]


def test_never_allows_blocked_actions(tmp_path):
    report = generate_iteration_review_packet(valid_t470(), "x")
    for b in REQUIRED_BLOCKED_ACTIONS:
        assert b not in report["allowed_actions"]
        assert b in report["blocked_actions"]


def test_invalid_json(tmp_path):
    p = str(tmp_path / "bad.json")
    with open(p, "w", encoding="utf-8") as f:
        f.write("bad")
    report = generate_iteration_review_packet(load_json(p), p)
    assert report["ok"] is False


def test_missing_file(tmp_path):
    p = str(tmp_path / "missing.json")
    report = generate_iteration_review_packet(load_json(p), p)
    assert report["ok"] is False


def test_cli_smoke(tmp_path):
    p = str(tmp_path / "t470.json")
    out = str(tmp_path / "out.json")
    write_json(p, valid_t470())
    proc = subprocess.Popen([
        sys.executable,
        str(Path(__file__).parent.parent.parent / "scripts" / "generate_testnet_dry_run_iteration_review_packet_v1.py"),
        "--result-review-phase-report", p,
        "--output", out,
        "--json",
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    proc.communicate()
    assert proc.returncode in [0, 1]
    assert os.path.exists(out)
