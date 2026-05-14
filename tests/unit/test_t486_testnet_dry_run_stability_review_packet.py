import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_testnet_dry_run_stability_review_packet_v1 import (
    REQUIRED_BLOCKED_ACTIONS,
    REQUIRED_STABILITY_ITEMS,
    generate_stability_review_packet,
    load_json,
    write_json,
)


def safe_flags():
    return {
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
    }


def allowed():
    return ["READ_REPORTS", "TESTNET_DRY_RUN_ONLY", "REVIEW_DRY_RUN_ARTIFACTS"]


def blocked():
    return list(REQUIRED_BLOCKED_ACTIONS)


def valid_t470():
    return {
        "ok": True,
        "phase_completion_status": "COMPLETED_TESTNET_DRY_RUN_RESULT_REVIEW",
        "final_decision": "READY_FOR_TESTNET_DRY_RUN_ITERATION_REVIEW",
        "safety_flags": safe_flags(),
        "allowed_actions": allowed(),
        "blocked_actions": blocked(),
    }


def valid_t485():
    return {
        "ok": True,
        "phase_completion_status": "COMPLETED_NEXT_TESTNET_DRY_RUN_RESULT_REVIEW",
        "final_decision": "READY_FOR_TESTNET_DRY_RUN_STABILITY_REVIEW",
        "safety_flags": safe_flags(),
        "allowed_actions": allowed(),
        "blocked_actions": blocked(),
    }


def test_ready_t470_t485_pass(tmp_path):
    r = generate_stability_review_packet(valid_t470(), valid_t485(), "a", "b")
    assert r["ok"] is True
    assert r["stability_review_packet_status"] == "READY_FOR_TWO_ROUND_DRY_RUN_REPEATABILITY_SUMMARY"


def test_blocked_t470(tmp_path):
    t470 = valid_t470()
    t470["ok"] = False
    r = generate_stability_review_packet(t470, valid_t485(), "a", "b")
    assert r["ok"] is False


def test_blocked_t485(tmp_path):
    t485 = valid_t485()
    t485["ok"] = False
    r = generate_stability_review_packet(valid_t470(), t485, "a", "b")
    assert r["ok"] is False


def test_required_items_present(tmp_path):
    r = generate_stability_review_packet(valid_t470(), valid_t485(), "a", "b")
    for item in REQUIRED_STABILITY_ITEMS:
        assert item in r["required_stability_items"]


def test_never_allows_exchange_submit_cancel_flatten(tmp_path):
    r = generate_stability_review_packet(valid_t470(), valid_t485(), "a", "b")
    for b in REQUIRED_BLOCKED_ACTIONS:
        assert b not in r["allowed_actions"]
        assert b in r["blocked_actions"]


def test_invalid_json(tmp_path):
    p1 = str(tmp_path / "bad1.json")
    p2 = str(tmp_path / "bad2.json")
    with open(p1, "w", encoding="utf-8") as f:
        f.write("bad")
    with open(p2, "w", encoding="utf-8") as f:
        f.write("bad")
    r = generate_stability_review_packet(load_json(p1), load_json(p2), p1, p2)
    assert r["ok"] is False


def test_missing_file(tmp_path):
    p1 = str(tmp_path / "missing1.json")
    p2 = str(tmp_path / "missing2.json")
    r = generate_stability_review_packet(load_json(p1), load_json(p2), p1, p2)
    assert r["ok"] is False


def test_cli_smoke(tmp_path):
    p1 = str(tmp_path / "t470.json")
    p2 = str(tmp_path / "t485.json")
    out = str(tmp_path / "out.json")
    write_json(p1, valid_t470())
    write_json(p2, valid_t485())
    proc = subprocess.Popen([
        sys.executable,
        str(Path(__file__).parent.parent.parent / "scripts" / "generate_testnet_dry_run_stability_review_packet_v1.py"),
        "--first-result-review-phase-report", p1,
        "--second-result-review-phase-report", p2,
        "--output", out,
        "--json",
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    proc.communicate()
    assert proc.returncode in [0, 1]
    assert os.path.exists(out)
