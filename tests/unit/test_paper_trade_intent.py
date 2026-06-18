"""Tests for trade intent model — shadow-only, position sizing, direction mapping."""
from __future__ import annotations

import os
import py_compile

import pytest

from core.paper_trading.trade_intent import (
    build_trade_intent, TradeIntent, SIDE_MAP,
    TRADE_INTENT_SAFETY_FLAGS, DEFAULT_PAPER_EQUITY, DEFAULT_MAX_RISK_PCT,
)

MODULE_PATH = os.path.join(os.path.dirname(__file__), "..", "..",
                           "core", "paper_trading", "trade_intent.py")


def _make_plan(**overrides):
    plan = {
        "symbol": "BTCUSDT",
        "timeframe": "15m",
        "direction": "LONG_OBSERVE",
        "source_status": "LONG_READY",
        "last_close": 60000.0,
        "entry_observation": 60000.0,
        "invalidation_level": 59000.0,
        "take_profit_observation": 62000.0,
        "rr_ratio": 2.0,
        "risk_distance_pct": 1.67,
        "reward_distance_pct": 3.33,
        "plan_decision": "WATCH",
        "reason": "macd_rebound_watch: BULLISH_CROSS, LONG_READY",
    }
    plan.update(overrides)
    return plan


class TestModuleCompiles:
    def test_compiles(self):
        py_compile.compile(MODULE_PATH, doraise=True)


class TestBuildTradeIntent:
    def test_long_observe_to_long(self):
        intent = build_trade_intent(_make_plan(), "2026-06-18")
        assert intent.side == "LONG"
        assert intent.execution_mode == "shadow_only"

    def test_short_observe_to_short(self):
        intent = build_trade_intent(_make_plan(direction="SHORT_OBSERVE"), "2026-06-18")
        assert intent.side == "SHORT"

    def test_no_trade_to_invalid(self):
        intent = build_trade_intent(_make_plan(direction="NO_TRADE"), "2026-06-18")
        assert intent.side == "NO_TRADE"
        assert intent.intent_status == "INVALID"

    def test_shadow_ready_for_valid_long(self):
        intent = build_trade_intent(_make_plan(), "2026-06-18")
        assert intent.intent_status == "SHADOW_READY"

    def test_shadow_ready_for_valid_short(self):
        plan = _make_plan(
            direction="SHORT_OBSERVE",
            entry_observation=100.0,
            invalidation_level=105.0,
            take_profit_observation=90.0,
            rr_ratio=2.0,
        )
        intent = build_trade_intent(plan, "2026-06-18")
        assert intent.intent_status == "SHADOW_READY"

    def test_blocked_rr_too_low(self):
        intent = build_trade_intent(_make_plan(rr_ratio=1.0), "2026-06-18")
        assert intent.intent_status == "BLOCKED_BY_RISK_GATE"

    def test_blocked_zero_stop_loss(self):
        intent = build_trade_intent(_make_plan(invalidation_level=0), "2026-06-18")
        assert intent.intent_status == "BLOCKED_BY_RISK_GATE"

    def test_blocked_zero_take_profit(self):
        intent = build_trade_intent(_make_plan(take_profit_observation=0), "2026-06-18")
        assert intent.intent_status == "BLOCKED_BY_RISK_GATE"

    def test_invalid_zero_entry(self):
        intent = build_trade_intent(_make_plan(entry_observation=0), "2026-06-18")
        assert intent.intent_status == "INVALID"

    def test_position_size_positive(self):
        intent = build_trade_intent(_make_plan(), "2026-06-18")
        assert intent.position_size_preview > 0

    def test_position_size_zero_when_blocked(self):
        intent = build_trade_intent(_make_plan(rr_ratio=1.0), "2026-06-18")
        assert intent.position_size_preview == 0.0

    def test_safety_flags_present(self):
        intent = build_trade_intent(_make_plan(), "2026-06-18")
        for flag in ["PAPER_ONLY", "SHADOW_ONLY", "NO_ORDER", "NO_REAL_ORDER", "NO_SECRET"]:
            assert flag in intent.safety_flags

    def test_execution_mode_always_shadow(self):
        intent = build_trade_intent(_make_plan(), "2026-06-18")
        assert intent.execution_mode == "shadow_only"

    def test_notional_mode_fixed_risk(self):
        intent = build_trade_intent(_make_plan(), "2026-06-18")
        assert intent.notional_mode == "fixed_risk_pct"

    def test_intent_has_id(self):
        intent = build_trade_intent(_make_plan(), "2026-06-18")
        assert intent.intent_id.startswith("TI_")

    def test_to_dict(self):
        intent = build_trade_intent(_make_plan(), "2026-06-18")
        d = intent.to_dict()
        assert d["side"] == "LONG"
        assert d["execution_mode"] == "shadow_only"


class TestSideMap:
    def test_long_observe(self):
        assert SIDE_MAP["LONG_OBSERVE"] == "LONG"

    def test_short_observe(self):
        assert SIDE_MAP["SHORT_OBSERVE"] == "SHORT"

    def test_no_trade(self):
        assert SIDE_MAP["NO_TRADE"] == "NO_TRADE"


class TestPositionSizing:
    def test_formula_correct(self):
        plan = _make_plan(entry_observation=60000.0, invalidation_level=59000.0)
        intent = build_trade_intent(plan, "2026-06-18")
        risk_amount = 10000.0 * 0.5 / 100.0  # 50
        risk_per_unit = 1000.0
        expected = risk_amount / risk_per_unit  # 0.05
        assert abs(intent.position_size_preview - expected) < 0.0001

    def test_custom_equity(self):
        plan = _make_plan(entry_observation=60000.0, invalidation_level=59000.0)
        intent = build_trade_intent(plan, "2026-06-18", paper_equity=20000.0)
        risk_amount = 20000.0 * 0.5 / 100.0  # 100
        risk_per_unit = 1000.0
        expected = risk_amount / risk_per_unit  # 0.1
        assert abs(intent.position_size_preview - expected) < 0.0001


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
