import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.compare_three_testnet_submit_consistency_v1 import compare_consistency


def ev(verdict="PASS", env="testnet", symbol="BTCUSDT", side="BUY", tp=True, naked=False):
    return {
        "verdict": verdict,
        "env": env,
        "symbol": symbol,
        "side": side,
        "quantity": "0.01",
        "protective_orders_detected": True,
        "stop_market_detected": True,
        "take_profit_market_detected": tp,
        "naked_position_detected": naked,
        "orphan_protection_detected": False,
    }


def incident(level="NONE"):
    return {"incident_level": level}


def test_t513_consistent_pass():
    r = compare_consistency(ev(), ev(), ev(), incident(), incident(), incident())
    assert r["verdict"] == "PASS"
    assert r["consistency_status"] == "CONSISTENT"


def test_t513_third_missing_tp_partial():
    r = compare_consistency(ev(), ev(), ev(tp=False), incident(), incident(), incident())
    assert r["verdict"] == "PARTIAL"


def test_t513_wrong_env_fail():
    r = compare_consistency(ev(), ev(), ev(env="mainnet"), incident(), incident(), incident())
    assert r["verdict"] == "FAIL"


def test_t513_naked_fail():
    r = compare_consistency(ev(), ev(), ev(naked=True), incident(), incident(), incident())
    assert r["verdict"] == "FAIL"


def test_t513_side_or_symbol_drift_warning():
    r = compare_consistency(ev(symbol="BTCUSDT"), ev(symbol="BTCUSDT"), ev(symbol="ETHUSDT"), incident(), incident(), incident())
    assert r["verdict"] in ["PARTIAL", "FAIL"]
    assert any(d.get("field") == "symbol" for d in r["drift_items"])
