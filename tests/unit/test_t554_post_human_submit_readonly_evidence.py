import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.aggregate_post_human_submit_readonly_evidence_v1 import aggregate_evidence


def parser(v="PASS"):
    return {"verdict": v, "env": "testnet", "symbol": "BTCUSDT", "side": "BUY", "quantity": "0.01", "submit_executed": True, "order_id_present": True, "submit_allowed": False, "cancel_allowed": False, "flatten_allowed": False}


def protection(v="PASS", stop=True, tp=True, orphan=False, naked=False):
    return {"verdict": v, "position_detected": True, "protective_orders_detected": stop and tp, "stop_market_detected": stop, "take_profit_market_detected": tp, "orphan_protection_detected": orphan, "naked_position_detected": naked, "submit_allowed": False, "cancel_allowed": False, "flatten_allowed": False}


def test_pass():
    r = aggregate_evidence(parser("PASS"), protection("PASS"))
    assert r["verdict"] == "PASS"
    assert r["readonly"] is True
    assert r["submit_executed"] is True
    assert r["stop_market_detected"] is True
    assert r["take_profit_market_detected"] is True
    assert r["orphan_protection_detected"] is False
    assert r["naked_position_detected"] is False
    assert r["submit_allowed"] is False
    assert r["cancel_allowed"] is False
    assert r["flatten_allowed"] is False


def test_partial_missing_tp():
    r = aggregate_evidence(parser("PASS"), protection("PASS", stop=True, tp=False))
    assert r["verdict"] == "PARTIAL"


def test_fail_wrong_env():
    p = parser("PASS")
    p["env"] = "mainnet"
    r = aggregate_evidence(p, protection("PASS"))
    assert r["verdict"] == "FAIL"


def test_fail_naked():
    r = aggregate_evidence(parser("PASS"), protection("PASS", naked=True))
    assert r["verdict"] == "FAIL"
    assert "NAKED_POSITION_DETECTED" in r["blockers"]


def test_fail_orphan():
    r = aggregate_evidence(parser("PASS"), protection("PASS", orphan=True))
    assert r["verdict"] == "FAIL"
    assert "ORPHAN_PROTECTION_DETECTED" in r["blockers"]
