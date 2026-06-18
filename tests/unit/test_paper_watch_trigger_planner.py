"""Tests for watch trigger planner."""
from __future__ import annotations

import os
import py_compile

import pytest

from core.paper_trading.readonly_signal_analyzer import SignalResult
from core.paper_trading.watch_trigger_planner import plan_trigger, WatchTriggerPlan


def _make_sig(watch_state, **overrides) -> SignalResult:
    defaults = dict(
        symbol="BTCUSDT", timeframe="1h", last_close=64000.0,
        trend_bias="NEUTRAL", macd_state="NEUTRAL", rsi_state="NEUTRAL",
        volume_state="NORMAL", priority="LOW",
        entry_observation=64000.0, invalidation_level=63000.0,
        risk_notes="test", reasons=["test"],
        watch_state=watch_state, setup_type="NO_TRADE",
        turning_score=30, weakness_score=30, risk_score=50,
        distance_to_invalidation_pct=1.5,
        distance_to_recent_high_pct=3.0,
        distance_to_recent_low_pct=1.0,
    )
    defaults.update(overrides)
    defaults["watch_state"] = watch_state
    return SignalResult(**defaults)


class TestPlanTrigger:
    def test_long_ready(self):
        sig = _make_sig("LONG_READY", priority="HIGH", turning_score=80,
                        trend_bias="BULLISH", macd_state="BULLISH_CROSS")
        plan = plan_trigger(sig)
        assert plan.action_label == "WATCH_NOW"
        assert plan.trigger_type == "BREAKOUT_CONFIRM"
        assert plan.shadow_record_type == "WATCH_TRIGGER"
        assert "holds above" in plan.trigger_condition.lower() or "breaks" in plan.trigger_condition.lower()

    def test_long_watch(self):
        sig = _make_sig("LONG_WATCH", priority="MEDIUM", turning_score=60)
        plan = plan_trigger(sig)
        assert plan.action_label == "WAIT_CONFIRMATION"
        assert plan.trigger_type == "PULLBACK_HOLD"
        assert plan.shadow_record_type == "WATCH_TRIGGER"

    def test_near_turn_up(self):
        sig = _make_sig("NEAR_TURN_UP", priority="MEDIUM", turning_score=55,
                        macd_state="HIST_SHRINKING_RED")
        plan = plan_trigger(sig)
        assert plan.action_label == "WAIT_CONFIRMATION"
        assert plan.trigger_type == "MACD_TURN_CONFIRM"
        assert plan.shadow_record_type == "WATCH_TRIGGER"
        assert "MACD" in plan.trigger_condition

    def test_short_watch(self):
        sig = _make_sig("SHORT_WATCH", priority="LOW", weakness_score=60,
                        trend_bias="BEARISH")
        plan = plan_trigger(sig)
        assert plan.action_label == "SHORT_OBSERVE"
        assert plan.trigger_type == "WEAKNESS_CONTINUATION"
        assert plan.shadow_record_type == "OBSERVATION"

    def test_weak_avoid(self):
        sig = _make_sig("WEAK_AVOID", priority="LOW", weakness_score=50)
        plan = plan_trigger(sig)
        assert plan.action_label == "AVOID"
        assert plan.trigger_type == "AVOID"
        assert plan.shadow_record_type == "SKIP"

    def test_choppy_avoid(self):
        sig = _make_sig("CHOPPY_AVOID", priority="LOW")
        plan = plan_trigger(sig)
        assert plan.action_label == "AVOID"
        assert plan.trigger_type == "AVOID"
        assert plan.shadow_record_type == "SKIP"
        assert "choppy" in plan.risk_note.lower() or "chop" in plan.invalidation_condition.lower()

    def test_data_reject(self):
        sig = _make_sig("DATA_REJECT", priority="REJECT")
        plan = plan_trigger(sig)
        assert plan.action_label == "DATA_SKIP"
        assert plan.trigger_type == "DATA_REJECT"
        assert plan.shadow_record_type == "SKIP"


class TestTriggerPlannerSafety:
    def test_no_order_words(self):
        """Trigger plans must not contain order/buy/sell execution words."""
        all_states = ["LONG_READY", "LONG_WATCH", "NEAR_TURN_UP",
                      "SHORT_WATCH", "WEAK_AVOID", "CHOPPY_AVOID", "DATA_REJECT"]
        forbidden = {"submit", "buy", "sell", "execute", "order", "cancel"}
        for ws in all_states:
            sig = _make_sig(ws)
            plan = plan_trigger(sig)
            text = (plan.trigger_condition + plan.confirmation_condition +
                    plan.invalidation_condition + plan.risk_note + plan.wait_note).lower()
            for word in forbidden:
                assert word not in text, f"{ws}: forbidden word '{word}' in plan text"

    def test_no_network_imports(self):
        module_path = os.path.join(os.path.dirname(__file__), "..", "..",
                                    "core", "paper_trading", "watch_trigger_planner.py")
        import ast
        with open(module_path) as f:
            tree = ast.parse(f.read())
        forbidden = {"requests", "httpx", "aiohttp", "websocket", "urllib"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name.split(".")[0] not in forbidden
            elif isinstance(node, ast.ImportFrom) and node.module:
                assert node.module.split(".")[0] not in forbidden
