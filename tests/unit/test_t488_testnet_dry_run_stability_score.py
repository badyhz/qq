import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_testnet_dry_run_stability_score_v1 import (
    REQUIRED_BLOCKED_ACTIONS,
    _grade,
    generate_stability_score,
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


def valid_t487():
    return {
        "ok": True,
        "final_decision": "READY_FOR_TESTNET_DRY_RUN_STABILITY_SCORE",
        "safety_flags": safe_flags(),
        "allowed_actions": allowed(),
        "blocked_actions": blocked(),
    }


def valid_t469():
    return {
        "review_score": 100,
        "safety_flags": safe_flags(),
        "allowed_actions": allowed(),
        "blocked_actions": blocked(),
    }


def valid_t484():
    return {
        "review_score": 100,
        "safety_flags": safe_flags(),
        "allowed_actions": allowed(),
        "blocked_actions": blocked(),
    }


def test_all_pass_score_100_grade_a(tmp_path):
    r = generate_stability_score(valid_t486(), valid_t487(), valid_t469(), valid_t484())
    assert r["ok"] is True
    assert r["stability_score"] == 100
    assert r["stability_grade"] == "A"


def test_each_component_fail_expected_blocker(tmp_path):
    t486 = valid_t486(); t486["ok"] = False
    r = generate_stability_score(t486, valid_t487(), valid_t469(), valid_t484())
    assert "STABILITY_REVIEW_PACKET_NOT_READY" in r["blockers"]

    t487 = valid_t487(); t487["ok"] = False
    r = generate_stability_score(valid_t486(), t487, valid_t469(), valid_t484())
    assert "REPEATABILITY_NOT_CONFIRMED" in r["blockers"]

    t469 = valid_t469(); t469["review_score"] = 90
    r = generate_stability_score(valid_t486(), valid_t487(), t469, valid_t484())
    assert "FIRST_DRY_RUN_SCORE_NOT_100" in r["blockers"]

    t484 = valid_t484(); t484["review_score"] = 90
    r = generate_stability_score(valid_t486(), valid_t487(), valid_t469(), t484)
    assert "SECOND_DRY_RUN_SCORE_NOT_100" in r["blockers"]


def test_no_submit_no_exchange_violation_blocker(tmp_path):
    t484 = valid_t484()
    t484["safety_flags"]["exchange_api_calls_allowed"] = True
    r = generate_stability_score(valid_t486(), valid_t487(), valid_t469(), t484)
    assert "NO_SUBMIT_NO_EXCHANGE_BLOCK_NOT_CONFIRMED" in r["blockers"]


def test_grade_mapping(tmp_path):
    assert _grade(99) == "B"
    assert _grade(74) == "C"
    assert _grade(49) == "D"
    assert _grade(0) == "F"


def test_never_allows_exchange_submit_cancel_flatten(tmp_path):
    r = generate_stability_score(valid_t486(), valid_t487(), valid_t469(), valid_t484())
    for b in REQUIRED_BLOCKED_ACTIONS:
        assert b not in r["allowed_actions"]
        assert b in r["blocked_actions"]


def test_invalid_json(tmp_path):
    p1 = str(tmp_path / "t486.json")
    p2 = str(tmp_path / "t487.json")
    p3 = str(tmp_path / "t469.json")
    p4 = str(tmp_path / "bad.json")
    write_json(p1, valid_t486())
    write_json(p2, valid_t487())
    write_json(p3, valid_t469())
    with open(p4, "w", encoding="utf-8") as f:
        f.write("bad")
    r = generate_stability_score(load_json(p1), load_json(p2), load_json(p3), load_json(p4))
    assert r["ok"] is False


def test_missing_file(tmp_path):
    p1 = str(tmp_path / "t486.json")
    p2 = str(tmp_path / "t487.json")
    p3 = str(tmp_path / "t469.json")
    p4 = str(tmp_path / "missing.json")
    write_json(p1, valid_t486())
    write_json(p2, valid_t487())
    write_json(p3, valid_t469())
    r = generate_stability_score(load_json(p1), load_json(p2), load_json(p3), load_json(p4))
    assert r["ok"] is False


def test_cli_smoke(tmp_path):
    p1 = str(tmp_path / "t486.json")
    p2 = str(tmp_path / "t487.json")
    p3 = str(tmp_path / "t469.json")
    p4 = str(tmp_path / "t484.json")
    out = str(tmp_path / "out.json")
    write_json(p1, valid_t486())
    write_json(p2, valid_t487())
    write_json(p3, valid_t469())
    write_json(p4, valid_t484())
    proc = subprocess.Popen([
        sys.executable,
        str(Path(__file__).parent.parent.parent / "scripts" / "generate_testnet_dry_run_stability_score_v1.py"),
        "--stability-review-packet", p1,
        "--repeatability-report", p2,
        "--first-result-score-report", p3,
        "--second-result-score-report", p4,
        "--output", out,
        "--json",
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    proc.communicate()
    assert proc.returncode in [0, 1]
    assert os.path.exists(out)
