import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.classify_first_testnet_submit_safety_incident_v1 import classify_incident


def base_evidence():
    return {
        "verdict": "PASS",
        "env": "testnet",
        "symbol": "BTCUSDT",
        "side": "BUY",
        "quantity": "0.01",
        "submit_executed": True,
        "position_detected": True,
        "stop_market_detected": True,
        "take_profit_market_detected": True,
        "naked_position_detected": False,
        "orphan_protection_detected": False,
    }


def test_t502_none_pass():
    r = classify_incident(base_evidence())
    assert r["ok"] is True
    assert r["verdict"] == "PASS"
    assert r["incident_level"] == "NONE"


def test_t502_missing_sl_high():
    e = base_evidence()
    e["stop_market_detected"] = False
    r = classify_incident(e)
    assert r["verdict"] == "FAIL"
    assert r["incident_level"] == "HIGH"
    assert "MISSING_STOP_MARKET" in r["incident_types"]


def test_t502_naked_critical():
    e = base_evidence()
    e["naked_position_detected"] = True
    r = classify_incident(e)
    assert r["verdict"] == "FAIL"
    assert r["incident_level"] == "CRITICAL"


def test_t502_wrong_env_critical():
    e = base_evidence()
    e["env"] = "mainnet"
    r = classify_incident(e)
    assert r["verdict"] == "FAIL"
    assert r["incident_level"] == "CRITICAL"


def test_t502_unknown_state_medium():
    e = base_evidence()
    e["verdict"] = "UNKNOWN"
    e["submit_executed"] = True
    e["position_detected"] = False
    r = classify_incident(e)
    assert r["incident_level"] == "MEDIUM"
