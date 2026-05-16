import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.classify_post_human_submit_readonly_incident_v1 import classify_incident


def evidence(none=False, stop=True, tp=True, naked=False, orphan=False, env="testnet", submit_executed=True):
    return {"verdict": "PASS", "env": env, "submit_executed": submit_executed, "position_detected": True, "protective_orders_detected": stop and tp, "stop_market_detected": stop, "take_profit_market_detected": tp, "naked_position_detected": naked, "orphan_protection_detected": orphan, "submit_allowed": False, "cancel_allowed": False, "flatten_allowed": False}


def phase():
    return {"verdict": "PASS", "decision": "VERIFIED_ONE_SHOT_TESTNET_SUBMIT", "submit_allowed": False, "cancel_allowed": False, "flatten_allowed": False, "max_submit_count": 0}


def test_none():
    r = classify_incident(evidence(none=True), phase())
    assert r["verdict"] == "PASS"
    assert r["incident_level"] == "NONE"
    assert len(r["incident_types"]) == 0
    assert r["submit_allowed"] is False
    assert r["cancel_allowed"] is False
    assert r["flatten_allowed"] is False


def test_missing_tp_high():
    r = classify_incident(evidence(stop=True, tp=False), phase())
    assert r["verdict"] == "FAIL"
    assert r["incident_level"] == "HIGH"
    assert "MISSING_TAKE_PROFIT_MARKET" in r["incident_types"]


def test_naked_critical():
    r = classify_incident(evidence(naked=True), phase())
    assert r["verdict"] == "FAIL"
    assert r["incident_level"] == "CRITICAL"
    assert "NAKED_POSITION" in r["incident_types"]


def test_orphan_critical():
    r = classify_incident(evidence(orphan=True), phase())
    assert r["verdict"] == "FAIL"
    assert r["incident_level"] == "CRITICAL"
    assert "ORPHAN_PROTECTION" in r["incident_types"]


def test_wrong_env_critical():
    r = classify_incident(evidence(env="mainnet"), phase())
    assert r["verdict"] == "FAIL"
    assert r["incident_level"] == "CRITICAL"
    assert "WRONG_ENV" in r["incident_types"]


def test_actions_always_false():
    r = classify_incident(evidence(naked=True), phase())
    assert r["submit_allowed"] is False
    assert r["cancel_allowed"] is False
    assert r["flatten_allowed"] is False
