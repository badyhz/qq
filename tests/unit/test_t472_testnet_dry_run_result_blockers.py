import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.analyze_testnet_dry_run_result_blockers_v1 import (
    REQUIRED_BLOCKED_ACTIONS,
    analyze_blockers,
    load_json,
    write_json,
)


def safe_flags():
    return {
        "exchange_api_calls_allowed": False,
        "submit_attempted": False,
        "cancel_attempted": False,
        "flatten_attempted": False,
    }


def valid_t471():
    return {"ok": True, "safety_flags": safe_flags()}


def valid_t469(score=100):
    return {"review_score": score, "safety_flags": safe_flags()}


def valid_t464(ok=True):
    return {"ok": ok, "artifact_verification_status": "TESTNET_DRY_RUN_ONLY_ARTIFACTS_VERIFIED", "safety_flags": safe_flags()}


def test_clean_score_100_pass_with_warning_and_improvement(tmp_path):
    r = analyze_blockers(valid_t471(), valid_t469(100), valid_t464(True))
    assert r["ok"] is True
    assert "NO_REAL_MARKET_EXECUTION_YET" in r["warnings"]
    assert "RUN_NEXT_ARTIFACT_ONLY_DRY_RUN_SAMPLE" in r["improvement_items"]


def test_t471_blocked_fail(tmp_path):
    t471 = valid_t471(); t471["ok"] = False
    r = analyze_blockers(t471, valid_t469(100), valid_t464(True))
    assert r["ok"] is False
    assert "ITERATION_REVIEW_PACKET_NOT_READY" in r["blockers"]


def test_score_below_100_fail(tmp_path):
    r = analyze_blockers(valid_t471(), valid_t469(99), valid_t464(True))
    assert r["ok"] is False
    assert "DRY_RUN_RESULT_SCORE_BELOW_100" in r["blockers"]


def test_t464_blocked_fail(tmp_path):
    r = analyze_blockers(valid_t471(), valid_t469(100), valid_t464(False))
    assert r["ok"] is False
    assert "ARTIFACT_VERIFICATION_NOT_READY" in r["blockers"]


def test_submit_attempted_true_fail(tmp_path):
    t469 = valid_t469(100)
    t469["safety_flags"]["submit_attempted"] = True
    r = analyze_blockers(valid_t471(), t469, valid_t464(True))
    assert r["ok"] is False
    assert "SUBMIT_CANCEL_FLATTEN_ATTEMPT_DETECTED" in r["blockers"]


def test_never_allows_blocked_actions(tmp_path):
    r = analyze_blockers(valid_t471(), valid_t469(100), valid_t464(True))
    for b in REQUIRED_BLOCKED_ACTIONS:
        assert b not in r["allowed_actions"]
        assert b in r["blocked_actions"]


def test_invalid_json(tmp_path):
    p1 = str(tmp_path / "t471.json")
    p2 = str(tmp_path / "t469.json")
    p3 = str(tmp_path / "t464.json")
    write_json(p1, valid_t471())
    write_json(p2, valid_t469())
    with open(p3, "w", encoding="utf-8") as f:
        f.write("bad")
    r = analyze_blockers(load_json(p1), load_json(p2), load_json(p3))
    assert r["ok"] is False


def test_missing_file(tmp_path):
    p1 = str(tmp_path / "t471.json")
    p2 = str(tmp_path / "t469.json")
    p3 = str(tmp_path / "missing.json")
    write_json(p1, valid_t471())
    write_json(p2, valid_t469())
    r = analyze_blockers(load_json(p1), load_json(p2), load_json(p3))
    assert r["ok"] is False


def test_cli_smoke(tmp_path):
    p1 = str(tmp_path / "t471.json")
    p2 = str(tmp_path / "t469.json")
    p3 = str(tmp_path / "t464.json")
    out = str(tmp_path / "out.json")
    write_json(p1, valid_t471())
    write_json(p2, valid_t469())
    write_json(p3, valid_t464(True))
    proc = subprocess.Popen([
        sys.executable,
        str(Path(__file__).parent.parent.parent / "scripts" / "analyze_testnet_dry_run_result_blockers_v1.py"),
        "--iteration-review-packet", p1,
        "--result-review-score-report", p2,
        "--artifact-verification-report", p3,
        "--output", out,
        "--json",
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    proc.communicate()
    assert proc.returncode in [0, 1]
    assert os.path.exists(out)
