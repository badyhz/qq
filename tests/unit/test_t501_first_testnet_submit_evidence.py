import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.collect_first_testnet_submit_evidence_v1 import collect_evidence


def _submit_result(env="testnet", executed=True):
    return {
        "submit_attempted": True,
        "submit_executed": executed,
        "request_plan": {
            "env": env,
            "symbol": "BTCUSDT",
            "side": "BUY",
            "quantity": "0.01",
        },
        "submit_result": {"orderId": 123456},
    }


def _post_verification(stop=True, tp=True, orphan=False, naked=False):
    return {
        "readonly_checks": {
            "has_position_snapshot": True,
            "has_protection_snapshot": True,
            "stop_market_detected": stop,
            "take_profit_market_detected": tp,
        },
        "orphan_protection_detected": orphan,
        "naked_position_detected": naked,
    }


def test_t501_pass():
    r = collect_evidence(_submit_result(), _post_verification())
    assert r["ok"] is True
    assert r["verdict"] == "PASS"


def test_t501_partial_missing_tp():
    r = collect_evidence(_submit_result(), _post_verification(tp=False))
    assert r["ok"] is True
    assert r["verdict"] == "PARTIAL"


def test_t501_fail_wrong_env():
    r = collect_evidence(_submit_result(env="mainnet"), _post_verification())
    assert r["ok"] is False
    assert r["verdict"] == "FAIL"
    assert "WRONG_ENV" in r["blockers"]


def test_t501_fail_naked_position():
    r = collect_evidence(_submit_result(), _post_verification(naked=True))
    assert r["ok"] is False
    assert r["verdict"] == "FAIL"
    assert "NAKED_POSITION_DETECTED" in r["blockers"]


def test_t501_fail_malformed_input():
    r = collect_evidence(None, _post_verification())
    assert r["ok"] is False
    assert r["verdict"] == "FAIL"
