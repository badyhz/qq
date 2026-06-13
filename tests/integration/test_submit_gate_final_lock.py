"""Test submit gate final lock."""
import pytest
from src.runtime_integrations.testnet_final_gate.submit_gate_final_lock import default_locked, validate_gate

def test_default_locked():
    s = default_locked()
    assert s.submit_gate_state == "LOCKED"
    assert s.real_submit_allowed is False
    assert s.testnet_submit_allowed is False

def test_gate_valid():
    s = default_locked()
    valid, errors = validate_gate(s)
    assert valid is True
    assert len(errors) == 0

def test_gate_has_blocking_reasons():
    s = default_locked()
    assert len(s.blocking_reasons) > 0
