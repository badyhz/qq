"""Tests for trade intent risk gate — validation rules."""
from __future__ import annotations

import os
import py_compile

import pytest

from core.paper_trading.trade_intent_risk_gate import (
    validate_trade_intent, RiskGateResult, FORBIDDEN_FIELDS,
)

MODULE_PATH = os.path.join(os.path.dirname(__file__), "..", "..",
                           "core", "paper_trading", "trade_intent_risk_gate.py")


def _make_intent(**overrides):
    intent = {
        "intent_id": "TI_test",
        "side": "LONG",
        "execution_mode": "shadow_only",
        "intent_status": "SHADOW_READY",
        "entry_price": 60000.0,
        "stop_loss": 59000.0,
        "take_profit": 62000.0,
        "rr_ratio": 2.0,
        "risk_distance_pct": 1.67,
        "reward_distance_pct": 3.33,
        "max_risk_pct": 0.5,
    }
    intent.update(overrides)
    return intent


class TestModuleCompiles:
    def test_compiles(self):
        py_compile.compile(MODULE_PATH, doraise=True)


class TestValidateLongIntent:
    def test_valid_long_passes(self):
        result = validate_trade_intent(_make_intent())
        assert result.passed is True
        assert result.status == "PASS"

    def test_long_sl_must_be_below_entry(self):
        result = validate_trade_intent(_make_intent(stop_loss=61000.0))
        assert result.passed is False
        assert "LONG stop_loss must be below entry_price" in result.reasons

    def test_long_tp_must_be_above_entry(self):
        result = validate_trade_intent(_make_intent(take_profit=59000.0))
        assert result.passed is False
        assert "LONG take_profit must be above entry_price" in result.reasons


class TestValidateShortIntent:
    def test_valid_short_passes(self):
        intent = _make_intent(
            side="SHORT", entry_price=100.0,
            stop_loss=105.0, take_profit=90.0,
        )
        result = validate_trade_intent(intent)
        assert result.passed is True

    def test_short_sl_must_be_above_entry(self):
        intent = _make_intent(
            side="SHORT", entry_price=100.0,
            stop_loss=95.0, take_profit=90.0,
        )
        result = validate_trade_intent(intent)
        assert result.passed is False
        assert "SHORT stop_loss must be above entry_price" in result.reasons

    def test_short_tp_must_be_below_entry(self):
        intent = _make_intent(
            side="SHORT", entry_price=100.0,
            stop_loss=105.0, take_profit=110.0,
        )
        result = validate_trade_intent(intent)
        assert result.passed is False
        assert "SHORT take_profit must be below entry_price" in result.reasons


class TestRRatio:
    def test_rr_below_1_5_blocked(self):
        result = validate_trade_intent(_make_intent(rr_ratio=1.2))
        assert result.passed is False
        assert any("rr_ratio" in r for r in result.reasons)

    def test_rr_exactly_1_5_passes(self):
        result = validate_trade_intent(_make_intent(rr_ratio=1.5))
        assert result.passed is True


class TestRiskDistance:
    def test_zero_risk_blocked(self):
        result = validate_trade_intent(_make_intent(risk_distance_pct=0))
        assert result.passed is False

    def test_over_5pct_blocked(self):
        result = validate_trade_intent(_make_intent(risk_distance_pct=6.0))
        assert result.passed is False

    def test_exactly_5pct_passes(self):
        result = validate_trade_intent(_make_intent(risk_distance_pct=5.0, reward_distance_pct=10.0))
        assert result.passed is True


class TestMaxRisk:
    def test_over_0_5_blocked(self):
        result = validate_trade_intent(_make_intent(max_risk_pct=1.0))
        assert result.passed is False
        assert any("max_risk_pct" in r for r in result.reasons)

    def test_exactly_0_5_passes(self):
        result = validate_trade_intent(_make_intent(max_risk_pct=0.5))
        assert result.passed is True


class TestForbiddenFields:
    def test_account_id_forbidden(self):
        result = validate_trade_intent(_make_intent(account_id="123"))
        assert result.passed is False
        assert any("account_id" in r for r in result.reasons)

    def test_api_key_forbidden(self):
        result = validate_trade_intent(_make_intent(api_key="xxx"))
        assert result.passed is False


class TestExecutionMode:
    def test_must_be_shadow_only(self):
        result = validate_trade_intent(_make_intent(execution_mode="live"))
        assert result.passed is False
        assert any("shadow_only" in r for r in result.reasons)


class TestInvalidSide:
    def test_invalid_side(self):
        result = validate_trade_intent(_make_intent(side="BUY"))
        assert result.passed is False
        assert any("invalid side" in r for r in result.reasons)


class TestInvalidStatus:
    def test_already_invalid(self):
        result = validate_trade_intent(_make_intent(intent_status="INVALID"))
        assert result.passed is False
        assert result.status == "INVALID"


class TestNoTrade:
    def test_no_trade_short_circuits(self):
        intent = _make_intent(side="NO_TRADE", intent_status="INVALID")
        result = validate_trade_intent(intent)
        assert result.passed is False
        assert result.status == "INVALID"


class TestGateResult:
    def test_to_dict(self):
        result = validate_trade_intent(_make_intent())
        d = result.to_dict()
        assert "passed" in d
        assert "status" in d
        assert "reasons" in d
        assert "severity" in d


class TestNoForbiddenPatterns:
    def test_no_order_words(self):
        with open(MODULE_PATH) as f:
            content = f.read()
        for word in ["submit_order", "place_order", "cancel_order", "execute_trade"]:
            assert word not in content

    def test_no_env_reads(self):
        with open(MODULE_PATH) as f:
            content = f.read()
        assert "os.environ" not in content
        assert "os.getenv" not in content
