"""Tests for core.adapter_safety — adapter safety boundary enforcement."""

import pytest

from core.adapter_safety import AdapterSafetyBoundary, SafetyViolation, TaskCategory


# --- Allowed / blocked categories ---


def test_safe_readonly_allowed():
    boundary = AdapterSafetyBoundary()
    assert boundary.is_allowed(TaskCategory.SAFE_READONLY)


def test_simulation_allowed():
    boundary = AdapterSafetyBoundary()
    assert boundary.is_allowed(TaskCategory.SIMULATION)


def test_guard_injection_allowed():
    boundary = AdapterSafetyBoundary()
    assert boundary.is_allowed(TaskCategory.GUARD_INJECTION)


def test_high_risk_write_blocked():
    boundary = AdapterSafetyBoundary()
    assert not boundary.is_allowed(TaskCategory.HIGH_RISK_WRITE)


def test_live_trading_blocked():
    boundary = AdapterSafetyBoundary()
    assert not boundary.is_allowed(TaskCategory.LIVE_TRADING)


def test_runtime_orchestration_blocked():
    boundary = AdapterSafetyBoundary()
    assert not boundary.is_allowed(TaskCategory.RUNTIME_ORCHESTRATION)


# --- Frozen pattern detection ---


def test_frozen_pattern_detected():
    boundary = AdapterSafetyBoundary()
    assert boundary.check_frozen_exclusion("T1_live_runner_init")
    assert boundary.check_frozen_exclusion("T2_submit_replayed_order")
    assert boundary.check_frozen_exclusion("T3_safe_flatten_all")
    assert boundary.check_frozen_exclusion("T4_run_spot_testnet")


def test_frozen_pattern_not_detected():
    boundary = AdapterSafetyBoundary()
    assert not boundary.check_frozen_exclusion("T1_run_daily_report")
    assert not boundary.check_frozen_exclusion("T2_analyze_signals")


# --- Pattern blocking in validate_request ---


def test_submit_order_pattern_blocked():
    boundary = AdapterSafetyBoundary()
    with pytest.raises(SafetyViolation):
        boundary.validate_request("T1", "submit_order for BTC")


def test_cancel_order_pattern_blocked():
    boundary = AdapterSafetyBoundary()
    with pytest.raises(SafetyViolation):
        boundary.validate_request("T1", "cancel_order on ETHUSDT")


def test_place_order_pattern_blocked():
    boundary = AdapterSafetyBoundary()
    with pytest.raises(SafetyViolation):
        boundary.validate_request("T1", "place_order limit buy")


def test_open_position_pattern_blocked():
    boundary = AdapterSafetyBoundary()
    with pytest.raises(SafetyViolation):
        boundary.validate_request("T1", "open_position long BTC")


def test_close_position_pattern_blocked():
    boundary = AdapterSafetyBoundary()
    with pytest.raises(SafetyViolation):
        boundary.validate_request("T1", "close_position short ETH")


def test_binance_api_pattern_blocked():
    boundary = AdapterSafetyBoundary()
    with pytest.raises(SafetyViolation):
        boundary.validate_request("T1", "call binance_api spot")


def test_exchange_prefix_blocked():
    boundary = AdapterSafetyBoundary()
    with pytest.raises(SafetyViolation):
        boundary.validate_request("T1", "exchange_submit order")


# --- Classification ---


def test_classify_readonly_task():
    boundary = AdapterSafetyBoundary()
    cat = boundary.classify_task("T1", "generate daily report")
    assert cat == TaskCategory.SAFE_READONLY


def test_classify_simulation_task():
    boundary = AdapterSafetyBoundary()
    cat = boundary.classify_task("T1", "run dry_run simulation")
    assert cat == TaskCategory.SIMULATION


def test_classify_trading_task():
    boundary = AdapterSafetyBoundary()
    cat = boundary.classify_task("T1", "submit_order BTCUSDT")
    assert cat == TaskCategory.HIGH_RISK_WRITE


def test_classify_frozen_task():
    boundary = AdapterSafetyBoundary()
    cat = boundary.classify_task("T1_live_runner_start")
    assert cat == TaskCategory.HIGH_RISK_WRITE


def test_classify_unknown_defaults_readonly():
    boundary = AdapterSafetyBoundary()
    cat = boundary.classify_task("T99", "do something unclear")
    assert cat == TaskCategory.SAFE_READONLY


# --- validate_request success / failure ---


def test_validate_clean_request():
    boundary = AdapterSafetyBoundary()
    result = boundary.validate_request("T1", "read market summary")
    assert result["allowed"] is True
    assert result["category"] == "safe_readonly"


def test_validate_forbidden_request_raises():
    boundary = AdapterSafetyBoundary()
    with pytest.raises(SafetyViolation):
        boundary.validate_request("T1", "submit_order for BTC")


def test_validate_frozen_request_raises():
    boundary = AdapterSafetyBoundary()
    with pytest.raises(SafetyViolation):
        boundary.validate_request("T1_live_runner_boot")


def test_validate_disallowed_category_raises():
    boundary = AdapterSafetyBoundary()
    with pytest.raises(SafetyViolation):
        boundary.validate_request("T1", "start live trading session")


# --- add / remove allowed ---


def test_add_remove_allowed():
    boundary = AdapterSafetyBoundary()
    assert not boundary.is_allowed(TaskCategory.LIVE_TRADING)
    boundary.add_allowed(TaskCategory.LIVE_TRADING)
    assert boundary.is_allowed(TaskCategory.LIVE_TRADING)
    boundary.remove_allowed(TaskCategory.LIVE_TRADING)
    assert not boundary.is_allowed(TaskCategory.LIVE_TRADING)


def test_remove_allowed_is_idempotent():
    boundary = AdapterSafetyBoundary()
    boundary.remove_allowed(TaskCategory.SIMULATION)
    boundary.remove_allowed(TaskCategory.SIMULATION)  # no error
    assert not boundary.is_allowed(TaskCategory.SIMULATION)


# --- summary ---


def test_summary_stats():
    boundary = AdapterSafetyBoundary()
    s = boundary.summary()
    assert "safe_readonly" in s["allowed_categories"]
    assert "simulation" in s["allowed_categories"]
    assert "guard_injection" in s["allowed_categories"]
    assert "live_trading" not in s["allowed_categories"]
    assert "high_risk_write" not in s["allowed_categories"]
    assert "runtime" not in s["allowed_categories"]
    assert isinstance(s["forbidden_patterns"], list)
    assert isinstance(s["frozen_patterns"], list)
    assert len(s["frozen_patterns"]) > 0
