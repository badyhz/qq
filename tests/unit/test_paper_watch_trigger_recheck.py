"""Tests for watch trigger recheck."""
from __future__ import annotations

import os
import py_compile

import pytest

from core.paper_trading.readonly_signal_analyzer import SignalResult
from core.paper_trading.watch_trigger_planner import WatchTriggerPlan, plan_trigger
from core.paper_trading.watch_trigger_recheck import recheck_trigger, TriggerRecheckResult


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


def _make_plan(action_label, **overrides) -> WatchTriggerPlan:
    defaults = dict(
        symbol="BTCUSDT", timeframe="1h", watch_state="NEAR_TURN_UP",
        setup_type="MACD_TURNING_UP", priority="MEDIUM", last_close=64000.0,
        trigger_type="MACD_TURN_CONFIRM",
        trigger_condition="MACD turns green",
        confirmation_condition="RSI < 70",
        invalidation_condition="breaks 63000",
        risk_note="test", wait_note="wait",
        action_label=action_label, shadow_record_type="WATCH_TRIGGER",
    )
    defaults.update(overrides)
    defaults["action_label"] = action_label
    return WatchTriggerPlan(**defaults)


class TestRecheckTriggered:
    def test_near_turn_up_to_long_ready(self):
        sig = _make_sig("LONG_READY", macd_state="BULLISH_CROSS", turning_score=80)
        plan = _make_plan("WAIT_CONFIRMATION")
        result = recheck_trigger(sig, plan)
        assert result.recheck_status == "TRIGGERED"
        assert result.next_action == "OBSERVE_NOW"

    def test_near_turn_up_to_long_watch_bullish_macd(self):
        sig = _make_sig("LONG_WATCH", macd_state="HIST_EXPANDING_GREEN")
        plan = _make_plan("WAIT_CONFIRMATION")
        result = recheck_trigger(sig, plan)
        assert result.recheck_status == "TRIGGERED"
        assert result.next_action == "OBSERVE_NOW"

    def test_long_ready_still_long_ready(self):
        sig = _make_sig("LONG_READY", macd_state="HIST_EXPANDING_GREEN")
        plan = _make_plan("WATCH_NOW")
        result = recheck_trigger(sig, plan)
        assert result.recheck_status == "TRIGGERED"
        assert result.next_action == "OBSERVE_NOW"


class TestRecheckWaiting:
    def test_still_near_turn_up(self):
        sig = _make_sig("NEAR_TURN_UP", macd_state="HIST_SHRINKING_RED")
        plan = _make_plan("WAIT_CONFIRMATION")
        result = recheck_trigger(sig, plan)
        assert result.recheck_status == "WAITING"
        assert result.next_action == "KEEP_WAITING"

    def test_still_long_watch(self):
        sig = _make_sig("LONG_WATCH", macd_state="NEUTRAL")
        plan = _make_plan("WAIT_CONFIRMATION")
        result = recheck_trigger(sig, plan)
        assert result.recheck_status == "WAITING"
        assert result.next_action == "KEEP_WAITING"


class TestRecheckInvalidated:
    def test_degraded_to_weak_avoid(self):
        sig = _make_sig("WEAK_AVOID", weakness_score=60)
        plan = _make_plan("WAIT_CONFIRMATION")
        result = recheck_trigger(sig, plan)
        assert result.recheck_status == "INVALIDATED"
        assert result.next_action == "DROP_FROM_WATCH"

    def test_degraded_to_short_watch(self):
        sig = _make_sig("SHORT_WATCH", weakness_score=50)
        plan = _make_plan("WAIT_CONFIRMATION")
        result = recheck_trigger(sig, plan)
        assert result.recheck_status == "INVALIDATED"
        assert result.next_action == "DROP_FROM_WATCH"


class TestRecheckShortObserve:
    def test_short_still_bearish(self):
        sig = _make_sig("SHORT_WATCH", weakness_score=60)
        plan = _make_plan("SHORT_OBSERVE")
        result = recheck_trigger(sig, plan)
        assert result.recheck_status == "SHORT_TRIGGERED"
        assert result.next_action == "SHORT_OBSERVE"

    def test_short_weak_avoid(self):
        sig = _make_sig("WEAK_AVOID", weakness_score=50)
        plan = _make_plan("SHORT_OBSERVE")
        result = recheck_trigger(sig, plan)
        assert result.recheck_status == "SHORT_TRIGGERED"
        assert result.next_action == "SHORT_OBSERVE"

    def test_short_improved_to_long(self):
        sig = _make_sig("LONG_WATCH", turning_score=60)
        plan = _make_plan("SHORT_OBSERVE")
        result = recheck_trigger(sig, plan)
        assert result.recheck_status == "SHORT_INVALIDATED"
        assert result.next_action == "DROP_FROM_WATCH"


class TestRecheckDataReject:
    def test_data_reject(self):
        sig = _make_sig("DATA_REJECT", priority="REJECT")
        plan = _make_plan("WAIT_CONFIRMATION")
        result = recheck_trigger(sig, plan)
        assert result.recheck_status == "DATA_ERROR"
        assert result.next_action == "DATA_SKIP"


class TestRecheckNoPlan:
    def test_no_previous_plan_generates_one(self):
        sig = _make_sig("NEAR_TURN_UP")
        result = recheck_trigger(sig, None)
        assert result.recheck_status == "WAITING"
        assert result.next_action == "KEEP_WAITING"


class TestRecheckSafety:
    def test_no_order_words(self):
        """Recheck results must not contain order execution words."""
        all_states = ["LONG_READY", "LONG_WATCH", "NEAR_TURN_UP",
                      "SHORT_WATCH", "WEAK_AVOID", "CHOPPY_AVOID", "DATA_REJECT"]
        forbidden = {"submit", "buy", "sell", "execute", "place_order", "cancel_order"}
        for ws in all_states:
            sig = _make_sig(ws)
            result = recheck_trigger(sig)
            text = (result.trigger_reason + result.invalidation_reason +
                    result.risk_note).lower()
            for word in forbidden:
                assert word not in text, f"{ws}: forbidden word '{word}' in result"

    def test_no_network_imports(self):
        module_path = os.path.join(os.path.dirname(__file__), "..", "..",
                                    "core", "paper_trading", "watch_trigger_recheck.py")
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
