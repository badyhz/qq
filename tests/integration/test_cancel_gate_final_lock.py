"""Test cancel gate final lock."""
import pytest
from src.runtime_integrations.testnet_final_gate.cancel_gate_final_lock import default_locked, validate_gate

def test_default_locked():
    s = default_locked()
    assert s.cancel_gate_state == "LOCKED"
    assert s.simulated_cancel_only is True
    assert s.real_cancel_allowed is False

def test_gate_valid():
    s = default_locked()
    valid, errors = validate_gate(s)
    assert valid is True
