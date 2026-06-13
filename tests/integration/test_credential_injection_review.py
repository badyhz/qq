"""Test credential injection review."""
import pytest
from src.runtime_integrations.testnet_final_gate.credential_injection_review import run_review

def test_review_stub_only():
    r = run_review()
    assert r.credential_source == "STUB_ONLY"

def test_review_no_env():
    r = run_review()
    assert r.env_secret_read is False

def test_review_injection_disabled():
    r = run_review()
    assert r.credential_injection_allowed is False

def test_review_submit_blocked():
    r = run_review()
    assert r.submit_allowed is False

def test_review_least_privilege():
    r = run_review()
    assert r.permissions_least_privilege is True
    assert r.withdraw_forbidden is True
    assert r.trading_not_enabled is True
