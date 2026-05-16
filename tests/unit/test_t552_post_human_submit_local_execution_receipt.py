import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.parse_post_human_submit_local_execution_receipt_v1 import parse_receipt


def eligibility(v="PASS"):
    return {"verdict": v, "submit_allowed": False, "cancel_allowed": False, "flatten_allowed": False}


def receipt(v="TEST", env="testnet", submit_attempted=True, submit_executed=True, order_id="123456"):
    return {"env": env, "submit_attempted": submit_attempted, "submit_executed": submit_executed, "order_id": order_id, "client_order_id": "test-789", "symbol": "BTCUSDT", "side": "BUY", "quantity": "0.01"}


def test_pass():
    r = parse_receipt(eligibility("PASS"), receipt())
    assert r["verdict"] == "PASS"
    assert r["receipt_status"] == "ACCEPTED"
    assert r["env"] == "testnet"
    assert r["submit_allowed"] is False
    assert r["cancel_allowed"] is False
    assert r["flatten_allowed"] is False
    assert r["order_id_present"] is True


def test_partial_missing_order_id():
    r = parse_receipt(eligibility("PASS"), receipt(submit_attempted=True, submit_executed=False, order_id=""))
    assert r["verdict"] == "PARTIAL"


def test_fail_wrong_env():
    r = parse_receipt(eligibility("PASS"), receipt(env="mainnet"))
    assert r["verdict"] == "FAIL"


def test_fail_mainnet_marker():
    bad = receipt(env="testnet")
    bad["something"] = "api.binance.com"
    r = parse_receipt(eligibility("PASS"), bad)
    assert r["verdict"] == "FAIL"


def test_fail_nested_mainnet_marker():
    bad = receipt(env="testnet")
    bad["nested"] = {"url": "https://api.binance.com/fapi/v1/order"}
    r = parse_receipt(eligibility("PASS"), bad)
    assert r["verdict"] == "FAIL"


def test_fail_eligibility_fail():
    r = parse_receipt(eligibility("FAIL"), receipt())
    assert r["verdict"] == "FAIL"
