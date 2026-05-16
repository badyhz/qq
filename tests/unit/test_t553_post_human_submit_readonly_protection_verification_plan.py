import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_post_human_submit_readonly_protection_verification_plan_v1 import generate_plan


def parser(v="PASS"):
    return {"verdict": v, "env": "testnet", "symbol": "BTCUSDT", "side": "BUY", "quantity": "0.01", "submit_allowed": False, "cancel_allowed": False, "flatten_allowed": False}


def test_pass():
    r = generate_plan(parser("PASS"))
    assert r["verdict"] == "PASS"
    assert r["plan_type"] == "POST_HUMAN_SUBMIT_PROTECTION_READONLY_CHECK"
    assert r["readonly"] is True
    assert r["submit_allowed"] is False
    assert r["cancel_allowed"] is False
    assert r["flatten_allowed"] is False


def test_partial():
    r = generate_plan(parser("PARTIAL"))
    assert r["verdict"] == "PARTIAL"


def test_fail():
    r = generate_plan(parser("FAIL"))
    assert r["verdict"] == "FAIL"


def test_forbidden_actions_present():
    r = generate_plan(parser("PASS"))
    forbidden = r["forbidden_actions"]
    assert "SUBMIT" in forbidden
    assert "CANCEL" in forbidden
    assert "FLATTEN" in forbidden
    assert "LIVE" in forbidden
    assert "MAINNET" in forbidden
    assert "REPEAT_SUBMIT" in forbidden


def test_readonly_true():
    r = generate_plan(parser("PASS"))
    assert r["readonly"] is True
