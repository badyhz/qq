"""Test submit intent review packet."""
import pytest
from src.runtime_integrations.testnet_sandbox.submit_intent_packet import build_intent_packet
from src.runtime_integrations.testnet_sandbox.submit_intent_validator import validate_intent


def test_intent_packet_safety_flags():
    p = build_intent_packet("BTCUSDT", "BUY", "LIMIT", 0.001, "LIMIT", "low risk", "SIG_001")
    assert p.simulated is True
    assert p.real_submit is False
    assert p.testnet_submit is False
    assert p.no_submit_enforced is True
    assert p.approval_status == "DENIED"


def test_intent_packet_has_required_fields():
    p = build_intent_packet("BTCUSDT", "BUY", "LIMIT", 0.001, "LIMIT", "low risk", "SIG_001")
    assert p.intent_id.startswith("INT_")
    assert p.symbol == "BTCUSDT"
    assert p.side == "BUY"
    assert p.quantity == 0.001


def test_validate_intent_passes():
    p = build_intent_packet("BTCUSDT", "BUY", "LIMIT", 0.001, "LIMIT", "low risk", "SIG_001")
    v = validate_intent(p.to_dict())
    assert v.valid is True


def test_validate_intent_fails_real_submit():
    p = build_intent_packet("BTCUSDT", "BUY", "LIMIT", 0.001, "LIMIT", "low risk", "SIG_001")
    d = p.to_dict()
    d["real_submit"] = True
    v = validate_intent(d)
    assert v.valid is False


def test_validate_intent_fails_not_simulated():
    p = build_intent_packet("BTCUSDT", "BUY", "LIMIT", 0.001, "LIMIT", "low risk", "SIG_001")
    d = p.to_dict()
    d["simulated"] = False
    v = validate_intent(d)
    assert v.valid is False
