import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_next_testnet_dry_run_result_review_score_v1 import (
    REQUIRED_BLOCKED_ACTIONS,
    _grade,
    generate_review_score,
    load_json,
    write_json,
)


def safe_flags():
    return {
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
    return ["READ_REPORTS", "TESTNET_DRY_RUN_ONLY", "REVIEW_NEXT_DRY_RUN_ARTIFACTS"]


def blocked():
    return list(REQUIRED_BLOCKED_ACTIONS)


def valid_t481():
    return {"ok": True, "final_decision": "READY_FOR_NEXT_TESTNET_DRY_RUN_PAYLOAD_MATERIALIZATION_CONSISTENCY_REVIEW", "safety_flags": safe_flags(), "allowed_actions": allowed(), "blocked_actions": blocked()}


def valid_t482():
    return {"ok": True, "consistency_status": "NEXT_PAYLOAD_MATERIALIZATION_CONSISTENCY_VERIFIED", "safety_flags": safe_flags(), "allowed_actions": allowed(), "blocked_actions": blocked()}


def valid_t483():
    return {"ok": True, "safety_evidence_status": "NEXT_DRY_RUN_NO_SUBMIT_SAFETY_EVIDENCE_VERIFIED", "safety_flags": safe_flags(), "allowed_actions": allowed(), "blocked_actions": blocked()}


def test_all_pass_score_100_grade_a(tmp_path):
    r = generate_review_score(valid_t481(), valid_t482(), valid_t483())
    assert r["ok"] is True
    assert r["review_score"] == 100
    assert r["review_grade"] == "A"


def test_each_component_fail_score_75_exact_blocker(tmp_path):
    t481 = valid_t481(); t481["ok"] = False
    r = generate_review_score(t481, valid_t482(), valid_t483())
    assert r["review_score"] == 75 and "REVIEW_PACKET_NOT_READY" in r["blockers"]

    t482 = valid_t482(); t482["ok"] = False
    r = generate_review_score(valid_t481(), t482, valid_t483())
    assert r["review_score"] == 75 and "PAYLOAD_CONSISTENCY_NOT_VERIFIED" in r["blockers"]

    t483 = valid_t483(); t483["ok"] = False
    r = generate_review_score(valid_t481(), valid_t482(), t483)
    assert r["review_score"] == 75 and "SAFETY_EVIDENCE_NOT_VERIFIED" in r["blockers"]


def test_no_submit_no_exchange_violation_blocker(tmp_path):
    t483 = valid_t483(); t483["safety_flags"]["exchange_api_calls_allowed"] = True
    r = generate_review_score(valid_t481(), valid_t482(), t483)
    assert "NO_SUBMIT_NO_EXCHANGE_BLOCK_NOT_CONFIRMED" in r["blockers"]


def test_grade_mapping(tmp_path):
    assert _grade(99) == "B"
    assert _grade(74) == "C"
    assert _grade(49) == "D"
    assert _grade(0) == "F"


def test_never_allows_blocked_actions(tmp_path):
    r = generate_review_score(valid_t481(), valid_t482(), valid_t483())
    for b in REQUIRED_BLOCKED_ACTIONS:
        assert b not in r["allowed_actions"]
        assert b in r["blocked_actions"]


def test_invalid_json(tmp_path):
    p1 = str(tmp_path / "t481.json")
    p2 = str(tmp_path / "t482.json")
    p3 = str(tmp_path / "t483.json")
    write_json(p1, valid_t481())
    write_json(p2, valid_t482())
    with open(p3, "w", encoding="utf-8") as f:
        f.write("bad")
    r = generate_review_score(load_json(p1), load_json(p2), load_json(p3))
    assert r["ok"] is False


def test_missing_file(tmp_path):
    p1 = str(tmp_path / "t481.json")
    p2 = str(tmp_path / "t482.json")
    p3 = str(tmp_path / "missing.json")
    write_json(p1, valid_t481())
    write_json(p2, valid_t482())
    r = generate_review_score(load_json(p1), load_json(p2), load_json(p3))
    assert r["ok"] is False


def test_cli_smoke(tmp_path):
    p1 = str(tmp_path / "t481.json")
    p2 = str(tmp_path / "t482.json")
    p3 = str(tmp_path / "t483.json")
    out = str(tmp_path / "out.json")
    write_json(p1, valid_t481())
    write_json(p2, valid_t482())
    write_json(p3, valid_t483())
    proc = subprocess.Popen([
        sys.executable,
        str(Path(__file__).parent.parent.parent / "scripts" / "generate_next_testnet_dry_run_result_review_score_v1.py"),
        "--review-packet", p1,
        "--consistency-report", p2,
        "--safety-evidence-report", p3,
        "--output", out,
        "--json",
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    proc.communicate()
    assert proc.returncode in [0, 1]
    assert os.path.exists(out)
