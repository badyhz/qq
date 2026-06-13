"""Test human approval gate."""
import pytest
from src.runtime_integrations.testnet_sandbox.human_approval_gate import create_request, default_decision, deny_stale, deny_incomplete


def test_default_decision_denies():
    req = create_request("INT_001", "BTCUSDT", "BUY", 0.001)
    d = default_decision(req)
    assert d.approved is False
    assert d.submit_allowed is False
    assert d.human_approval_required is True


def test_stale_decision_denies():
    req = create_request("INT_002", "BTCUSDT", "BUY", 0.001)
    d = deny_stale(req)
    assert d.approved is False
    assert d.submit_allowed is False


def test_incomplete_decision_denies():
    req = create_request("INT_003", "BTCUSDT", "BUY", 0.001)
    d = deny_incomplete(req, ("price", "risk_summary"))
    assert d.approved is False
    assert "INCOMPLETE" in d.reason


def test_request_has_required_fields():
    req = create_request("INT_004", "ETHUSDT", "SELL", 0.01)
    assert req.request_id == "APR_INT_004"
    assert req.symbol == "ETHUSDT"
    assert req.side == "SELL"
