import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_post_human_submit_final_operator_summary_report_v1 import generate_operator_summary


def health_score(verdict="PASS", decision="HEALTHY_SESSION_CLOSED", score=100, level="NONE"):
    return {"verdict": verdict, "decision": decision, "health_score": score, "incident_level": level, "submit_allowed": False, "cancel_allowed": False, "flatten_allowed": False}


def evidence(env="testnet", symbol="BTCUSDT", side="SELL", qty="0.01", submit=True, pos=True, stop=True, tp=True):
    return {"verdict": "PASS", "env": env, "symbol": symbol, "side": side, "quantity": qty, "submit_executed": submit, "position_detected": pos, "stop_market_detected": stop, "take_profit_market_detected": tp, "naked_position_detected": False, "orphan_protection_detected": False, "submit_allowed": False, "cancel_allowed": False, "flatten_allowed": False}


def phase():
    return {"verdict": "PASS", "submit_allowed": False, "cancel_allowed": False, "flatten_allowed": False}


def audit(verdict="PASS"):
    return {"verdict": verdict, "submit_allowed": False, "cancel_allowed": False, "flatten_allowed": False}


def test_closed_healthy():
    r = generate_operator_summary(health_score(), evidence(), phase(), audit())
    assert r["ok"] is True
    assert r["verdict"] == "PASS"
    assert r["session_status"] == "CLOSED_HEALTHY"
    assert r["summary_items"]["final_health_score"] == 100
    assert r["summary_items"]["incident_level"] == "NONE"


def test_monitor():
    r = generate_operator_summary(health_score("PARTIAL", "MONITOR", 85, "LOW"), evidence(), phase(), audit())
    assert r["ok"] is False
    assert r["verdict"] == "PARTIAL"
    assert r["session_status"] == "MONITOR"


def test_review_required():
    r = generate_operator_summary(health_score("PARTIAL", "REVIEW_REQUIRED", 70, "MEDIUM"), evidence(), phase(), audit())
    assert r["ok"] is False
    assert r["verdict"] == "PARTIAL"
    assert r["session_status"] == "REVIEW_REQUIRED"


def test_rollback_review():
    r = generate_operator_summary(health_score("FAIL", "ROLLBACK_REVIEW_REQUIRED", 40, "HIGH"), evidence(), phase(), audit())
    assert r["ok"] is False
    assert r["verdict"] == "FAIL"
    assert r["session_status"] == "ROLLBACK_REVIEW_REQUIRED"


def test_actions_always_false():
    r = generate_operator_summary(health_score(), evidence(), phase(), audit())
    assert r["submit_allowed"] is False
    assert r["cancel_allowed"] is False
    assert r["flatten_allowed"] is False


def test_summary_items_present():
    r = generate_operator_summary(health_score(), evidence(), phase(), audit())
    assert "submit_executed" in r["summary_items"]
    assert "env" in r["summary_items"]
    assert "symbol" in r["summary_items"]
    assert "position_detected" in r["summary_items"]
    assert "stop_market_detected" in r["summary_items"]
    assert "take_profit_market_detected" in r["summary_items"]
    assert "incident_level" in r["summary_items"]
    assert "final_health_score" in r["summary_items"]
