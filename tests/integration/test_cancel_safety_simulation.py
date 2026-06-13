"""Test cancel safety simulation."""
import pytest
from src.runtime_integrations.testnet_presubmit.cancel_safety_simulator import run_cancel_safety_suite

def test_all_records_simulated():
    records = run_cancel_safety_suite()
    for r in records:
        assert r.simulated is True
        assert r.real_cancel is False
        assert r.network_called is False
        assert r.no_submit_enforced is True

def test_valid_cancel_passes():
    records = run_cancel_safety_suite()
    valid = [r for r in records if r.validation.valid]
    assert len(valid) >= 2

def test_unknown_order_blocked():
    records = run_cancel_safety_suite()
    unknown = [r for r in records if r.order_id == "ORD_999"]
    assert len(unknown) == 1
    assert not unknown[0].validation.valid

def test_terminal_order_blocked():
    records = run_cancel_safety_suite()
    terminal = [r for r in records if r.order_id == "ORD_003" and "terminal" in str(r.validation.checks)]
    assert len(terminal) >= 1
    assert not terminal[0].validation.valid

def test_not_approved_blocked():
    records = run_cancel_safety_suite()
    not_approved = [r for r in records if "not_approved" in r.cancel_id or "CANCEL_NOT_APPROVED" in str(r.validation.checks)]
    assert len(not_approved) >= 1

def test_kill_switch_blocks():
    records = run_cancel_safety_suite()
    ks = [r for r in records if "kill" in r.cancel_id or "KILL_SWITCH" in str(r.validation.checks)]
    assert len(ks) >= 1
