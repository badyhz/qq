"""Test sandbox risk controls."""
import pytest
from src.runtime_integrations.testnet_sandbox.sandbox_risk_controls import (
    check_max_notional, check_symbol_allowed, check_symbol_not_blocked,
    check_daily_order_count, check_price_sanity, check_duplicate_intent,
    check_approval_required, check_kill_switch, run_all_checks,
    MAX_NOTIONAL, ALLOWED_SYMBOLS, BLOCKED_SYMBOLS,
)


def test_max_notional_pass():
    r = check_max_notional(0.001, 50000.0)
    assert r.passed is True


def test_max_notional_fail():
    r = check_max_notional(1.0, 50000.0)
    assert r.passed is False


def test_symbol_allowed():
    for sym in ALLOWED_SYMBOLS:
        r = check_symbol_allowed(sym)
        assert r.passed is True


def test_symbol_not_allowed():
    r = check_symbol_allowed("FAKECOINUSDT")
    assert r.passed is False


def test_symbol_blocked():
    for sym in BLOCKED_SYMBOLS:
        r = check_symbol_not_blocked(sym)
        assert r.passed is False


def test_symbol_not_blocked():
    r = check_symbol_not_blocked("BTCUSDT")
    assert r.passed is True


def test_daily_count_pass():
    r = check_daily_order_count(5)
    assert r.passed is True


def test_daily_count_fail():
    r = check_daily_order_count(100)
    assert r.passed is False


def test_price_sanity_pass():
    r = check_price_sanity(50000.0, 50000.0)
    assert r.passed is True


def test_price_sanity_fail():
    r = check_price_sanity(100000.0, 50000.0)
    assert r.passed is False


def test_duplicate_intent_pass():
    r = check_duplicate_intent("INT_NEW", {"INT_OLD"})
    assert r.passed is True


def test_duplicate_intent_fail():
    r = check_duplicate_intent("INT_EXISTS", {"INT_EXISTS"})
    assert r.passed is False


def test_approval_required_pass():
    r = check_approval_required("DENIED")
    assert r.passed is True


def test_approval_required_fail():
    r = check_approval_required("APPROVED")
    assert r.passed is False


def test_kill_switch_pass():
    r = check_kill_switch(True)
    assert r.passed is True


def test_kill_switch_fail():
    r = check_kill_switch(False)
    assert r.passed is False


def test_run_all_checks_pass():
    checks = run_all_checks("BTCUSDT", 0.001, 50000.0, "INT_NEW", set(), "DENIED", True, 5, 50000.0, "2026-06-14")
    assert all(c.passed for c in checks)
