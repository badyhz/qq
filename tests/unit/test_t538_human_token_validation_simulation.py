import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.simulate_human_token_validation_v1 import generate_validation


def token_packet():
    return {
        "token_required": True,
        "token_scope": {
            "env": "testnet",
            "symbol": "BTCUSDT",
            "side": "BUY",
            "quantity": "0.01",
            "max_submit_count": 1,
        },
        "token_phrase_template": "CONFIRM_TESTNET_SUBMIT:testnet:BTCUSDT:BUY:0.01:COUNT_1",
        "submit_allowed": False,
    }


def test_no_token_partial():
    r = generate_validation(token_packet(), None)
    assert r["verdict"] == "PARTIAL"
    assert r["token_provided"] is False
    assert r["token_matches"] is False
    assert r["submit_allowed"] is False
    assert "NO_TOKEN_PROVIDED" in r["warnings"]


def test_wrong_token_fail():
    r = generate_validation(token_packet(), "WRONG_TOKEN")
    assert r["verdict"] == "FAIL"
    assert r["token_provided"] is True
    assert r["token_matches"] is False
    assert r["submit_allowed"] is False
    assert "TOKEN_MISMATCH" in r["blockers"]


def test_correct_token_pass():
    r = generate_validation(token_packet(), "CONFIRM_TESTNET_SUBMIT:testnet:BTCUSDT:BUY:0.01:COUNT_1")
    assert r["verdict"] == "PASS"
    assert r["token_provided"] is True
    assert r["token_matches"] is True
    assert r["submit_allowed"] is False


def test_token_scope_mismatch_fail():
    tp = token_packet()
    tp["token_scope"]["symbol"] = "ETHUSDT"
    r = generate_validation(tp, "CONFIRM_TESTNET_SUBMIT:testnet:BTCUSDT:BUY:0.01:COUNT_1")
    assert r["verdict"] == "FAIL"
    assert "TOKEN_SCOPE_MISMATCH" in r["blockers"]


def test_submit_allowed_remains_false_always():
    r = generate_validation(token_packet(), "CONFIRM_TESTNET_SUBMIT:testnet:BTCUSDT:BUY:0.01:COUNT_1")
    assert r["submit_allowed"] is False

    r = generate_validation(token_packet(), None)
    assert r["submit_allowed"] is False

    r = generate_validation(token_packet(), "WRONG")
    assert r["submit_allowed"] is False


def test_max_submit_count_remains_1():
    r = generate_validation(token_packet(), "CONFIRM_TESTNET_SUBMIT:testnet:BTCUSDT:BUY:0.01:COUNT_1")
    assert r["max_submit_count"] == 1
