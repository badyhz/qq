"""Test kill switch validation."""
import pytest
from src.runtime_integrations.testnet_sandbox.kill_switch import default_state, unlocked_sim_only, validate_kill_switch


def test_default_state_is_blocking():
    s = default_state()
    assert s.kill_switch_enabled is True
    assert s.submit_blocked is True
    assert s.real_trading_allowed is False
    assert s.testnet_submit_allowed is False
    assert s.state == "ENABLED_BLOCKING"


def test_default_state_valid():
    s = default_state()
    valid, errors = validate_kill_switch(s)
    assert valid is True
    assert len(errors) == 0


def test_unlocked_still_blocks():
    s = unlocked_sim_only()
    assert s.submit_blocked is True
    assert s.real_trading_allowed is False
    assert s.testnet_submit_allowed is False


def test_unlocked_valid():
    s = unlocked_sim_only()
    valid, errors = validate_kill_switch(s)
    assert valid is True
