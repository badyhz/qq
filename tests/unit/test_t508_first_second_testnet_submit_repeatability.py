import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.compare_first_second_testnet_submit_repeatability_v1 import compare_repeatability


def ev_pass(symbol="BTCUSDT", env="testnet", tp=True, naked=False, orphan=False):
    return {
        "verdict": "PASS",
        "env": env,
        "symbol": symbol,
        "side": "BUY",
        "quantity": "0.01",
        "protective_orders_detected": True,
        "stop_market_detected": True,
        "take_profit_market_detected": tp,
        "naked_position_detected": naked,
        "orphan_protection_detected": orphan,
    }


def test_t508_repeatable_pass():
    r = compare_repeatability(ev_pass(), ev_pass())
    assert r["verdict"] == "PASS"
    assert r["repeatability_status"] == "REPEATABLE"


def test_t508_missing_second_tp_partial():
    r = compare_repeatability(ev_pass(), ev_pass(tp=False))
    assert r["verdict"] == "PARTIAL"
    assert r["repeatability_status"] in ["INCOMPLETE", "DRIFT_DETECTED"]


def test_t508_wrong_env_fail():
    r = compare_repeatability(ev_pass(), ev_pass(env="mainnet"))
    assert r["verdict"] == "FAIL"


def test_t508_naked_fail():
    r = compare_repeatability(ev_pass(), ev_pass(naked=True))
    assert r["verdict"] == "FAIL"


def test_t508_symbol_drift_warning_or_fail():
    r = compare_repeatability(ev_pass(symbol="BTCUSDT"), ev_pass(symbol="ETHUSDT"))
    assert r["verdict"] in ["PARTIAL", "FAIL"]
    assert any(item.get("field") == "symbol" for item in r["drift_items"])
