"""Test audit log design validation."""
import pytest
from src.runtime_integrations.testnet_presubmit.audit_log_design import build_sample_chain
from src.runtime_integrations.testnet_presubmit.audit_log_validator import validate_chain

def test_chain_valid():
    events = build_sample_chain()
    dicts = [e.to_dict() for e in events]
    val = validate_chain(dicts)
    assert val.chain_valid is True
    assert val.tampering_detected is False

def test_events_no_submit():
    events = build_sample_chain()
    for e in events:
        assert e.no_submit_enforced is True

def test_tampering_detected():
    events = build_sample_chain()
    dicts = [e.to_dict() for e in events]
    dicts[2]["event_type"] = "TAMPERED"
    val = validate_chain(dicts)
    assert val.tampering_detected is True
