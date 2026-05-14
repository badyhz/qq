import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.summarize_two_round_testnet_dry_run_repeatability_v1 import (
    REQUIRED_BLOCKED_ACTIONS,
    load_json,
    summarize_repeatability,
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
    return ["READ_REPORTS", "TESTNET_DRY_RUN_ONLY", "REVIEW_DRY_RUN_STABILITY"]


def blocked():
    return list(REQUIRED_BLOCKED_ACTIONS)


def valid_t486():
    return {
        "ok": True,
        "final_decision": "READY_FOR_TWO_ROUND_DRY_RUN_REPEATABILITY_SUMMARY",
        "safety_flags": safe_flags(),
        "allowed_actions": allowed(),
        "blocked_actions": blocked(),
    }


def valid_t469():
    return {
        "ok": True,
        "review_score": 100,
        "safety_flags": safe_flags(),
        "allowed_actions": allowed(),
        "blocked_actions": blocked(),
    }


def valid_t484():
    return {
        "ok": True,
        "review_score": 100,
        "safety_flags": safe_flags(),
        "allowed_actions": allowed(),
        "blocked_actions": blocked(),
    }


def test_two_score_100_reports_pass(tmp_path):
    r = summarize_repeatability(valid_t486(), valid_t469(), valid_t484())
    assert r["ok"] is True
    assert r["repeatability_status"] == "TWO_ROUND_DRY_RUN_REPEATABILITY_CONFIRMED"
    assert r["repeatability_summary"]["rounds_reviewed"] == 2
    assert r["repeatability_summary"]["all_scores_100"] is True


def test_t486_blocked_fail(tmp_path):
    t486 = valid_t486()
    t486["ok"] = False
    r = summarize_repeatability(t486, valid_t469(), valid_t484())
    assert r["ok"] is False


def test_first_score_below_100_fail(tmp_path):
    t469 = valid_t469()
    t469["review_score"] = 99
    r = summarize_repeatability(valid_t486(), t469, valid_t484())
    assert r["ok"] is False


def test_second_score_below_100_fail(tmp_path):
    t484 = valid_t484()
    t484["review_score"] = 99
    r = summarize_repeatability(valid_t486(), valid_t469(), t484)
    assert r["ok"] is False


def test_missing_review_score_fail(tmp_path):
    t469 = valid_t469()
    del t469["review_score"]
    r = summarize_repeatability(valid_t486(), t469, valid_t484())
    assert r["ok"] is False


def test_submit_attempted_true_fail(tmp_path):
    t484 = valid_t484()
    t484["safety_flags"]["submit_attempted"] = True
    r = summarize_repeatability(valid_t486(), valid_t469(), t484)
    assert r["ok"] is False


def test_never_allows_exchange_submit_cancel_flatten(tmp_path):
    r = summarize_repeatability(valid_t486(), valid_t469(), valid_t484())
    for b in REQUIRED_BLOCKED_ACTIONS:
        assert b not in r["allowed_actions"]
        assert b in r["blocked_actions"]


def test_invalid_json(tmp_path):
    p1 = str(tmp_path / "t486.json")
    p2 = str(tmp_path / "t469.json")
    p3 = str(tmp_path / "bad.json")
    write_json(p1, valid_t486())
    write_json(p2, valid_t469())
    with open(p3, "w", encoding="utf-8") as f:
        f.write("bad")
    r = summarize_repeatability(load_json(p1), load_json(p2), load_json(p3))
    assert r["ok"] is False


def test_missing_file(tmp_path):
    p1 = str(tmp_path / "t486.json")
    p2 = str(tmp_path / "t469.json")
    p3 = str(tmp_path / "missing.json")
    write_json(p1, valid_t486())
    write_json(p2, valid_t469())
    r = summarize_repeatability(load_json(p1), load_json(p2), load_json(p3))
    assert r["ok"] is False


def test_cli_smoke(tmp_path):
    p1 = str(tmp_path / "t486.json")
    p2 = str(tmp_path / "t469.json")
    p3 = str(tmp_path / "t484.json")
    out = str(tmp_path / "out.json")
    write_json(p1, valid_t486())
    write_json(p2, valid_t469())
    write_json(p3, valid_t484())
    proc = subprocess.Popen([
        sys.executable,
        str(Path(__file__).parent.parent.parent / "scripts" / "summarize_two_round_testnet_dry_run_repeatability_v1.py"),
        "--stability-review-packet", p1,
        "--first-result-score-report", p2,
        "--second-result-score-report", p3,
        "--output", out,
        "--json",
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    proc.communicate()
    assert proc.returncode in [0, 1]
    assert os.path.exists(out)
