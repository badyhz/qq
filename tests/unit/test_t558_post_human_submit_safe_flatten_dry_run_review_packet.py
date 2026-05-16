import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_post_human_submit_safe_flatten_dry_run_review_packet_v1 import generate_safe_flatten_review


def eligibility(eligible=True):
    return {"verdict": "FAIL" if eligible else "PASS", "eligible_for_rollback_review": eligible, "required_action": "HUMAN_ROLLBACK_DECISION_REQUIRED" if eligible else "NONE", "submit_allowed": False, "cancel_allowed": False, "flatten_allowed": False}


def evidence(env="testnet", symbol="BTCUSDT", side="BUY", quantity="0.01"):
    return {"verdict": "FAIL", "env": env, "symbol": symbol, "side": side, "quantity": quantity, "naked_position_detected": True, "submit_allowed": False, "cancel_allowed": False, "flatten_allowed": False}


def test_pass_dry_run_template():
    r = generate_safe_flatten_review(eligibility(True), evidence())
    assert r["verdict"] == "PASS"
    assert r["packet_type"] == "SAFE_FLATTEN_DRY_RUN_REVIEW_ONLY"
    assert r["readonly"] is True
    assert "--dry-run" in r["dry_run_flatten_command_template"]
    assert r["submit_allowed"] is False
    assert r["cancel_allowed"] is False
    assert r["flatten_allowed"] is False


def test_missing_symbol_partial():
    r = generate_safe_flatten_review(eligibility(True), evidence(symbol=""))
    assert r["verdict"] == "PARTIAL"


def test_wrong_env_fail():
    r = generate_safe_flatten_review(eligibility(True), evidence(env="mainnet"))
    assert r["verdict"] == "FAIL"


def test_no_confirm_command():
    r = generate_safe_flatten_review(eligibility(True), evidence())
    assert "confirm" not in r["dry_run_flatten_command_template"].lower()


def test_actions_false():
    r = generate_safe_flatten_review(eligibility(True), evidence())
    assert r["submit_allowed"] is False
    assert r["cancel_allowed"] is False
    assert r["flatten_allowed"] is False
