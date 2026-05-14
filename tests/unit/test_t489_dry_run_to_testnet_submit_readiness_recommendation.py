import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_dry_run_to_testnet_submit_readiness_recommendation_v1 import (
    REQUIRED_BLOCKED_ACTIONS,
    REQUIRED_NEXT_REVIEWS,
    generate_recommendation,
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


def valid_t488():
    return {
        "ok": True,
        "stability_score": 100,
        "stability_status": "TESTNET_DRY_RUN_STABILITY_CONFIRMED",
        "final_decision": "READY_FOR_DRY_RUN_TO_TESTNET_SUBMIT_READINESS_RECOMMENDATION",
        "safety_flags": safe_flags(),
        "allowed_actions": allowed(),
        "blocked_actions": blocked(),
    }


def test_valid_t488_recommendation_pass(tmp_path):
    r = generate_recommendation(valid_t488())
    assert r["ok"] is True
    assert r["recommendation"] == "PROCEED_TO_TESTNET_SUBMIT_READINESS_REVIEW"


def test_blocked_t488(tmp_path):
    t488 = valid_t488()
    t488["ok"] = False
    r = generate_recommendation(t488)
    assert r["ok"] is False


def test_recommendation_scope_review_only(tmp_path):
    r = generate_recommendation(valid_t488())
    assert r["recommendation_scope"] == "REVIEW_ONLY_NOT_APPROVAL_TO_SUBMIT"


def test_required_next_reviews_present(tmp_path):
    r = generate_recommendation(valid_t488())
    for item in REQUIRED_NEXT_REVIEWS:
        assert item in r["required_next_reviews"]


def test_never_allows_exchange_submit_cancel_flatten(tmp_path):
    r = generate_recommendation(valid_t488())
    for b in REQUIRED_BLOCKED_ACTIONS:
        assert b not in r["allowed_actions"]
        assert b in r["blocked_actions"]


def test_invalid_json(tmp_path):
    p = str(tmp_path / "bad.json")
    with open(p, "w", encoding="utf-8") as f:
        f.write("bad")
    r = generate_recommendation(load_json(p))
    assert r["ok"] is False


def test_missing_file(tmp_path):
    p = str(tmp_path / "missing.json")
    r = generate_recommendation(load_json(p))
    assert r["ok"] is False


def test_cli_smoke(tmp_path):
    p = str(tmp_path / "t488.json")
    out = str(tmp_path / "out.json")
    write_json(p, valid_t488())
    proc = subprocess.Popen([
        sys.executable,
        str(Path(__file__).parent.parent.parent / "scripts" / "generate_dry_run_to_testnet_submit_readiness_recommendation_v1.py"),
        "--stability-score-report", p,
        "--output", out,
        "--json",
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    proc.communicate()
    assert proc.returncode in [0, 1]
    assert os.path.exists(out)
