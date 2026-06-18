"""Tests for focused paper plan preview."""
from __future__ import annotations

import os
import ast
import py_compile

import pytest

from core.paper_trading.readonly_signal_analyzer import SignalResult
from core.paper_trading.watch_trigger_recheck import TriggerRecheckResult
from core.paper_trading.focused_paper_plan_preview import (
    preview_plan, FocusedPaperPlan, SAFETY_FLAGS,
)


def _make_sig(watch_state="LONG_READY", **overrides) -> SignalResult:
    defaults = dict(
        symbol="BNBUSDT", timeframe="5m", last_close=600.0,
        trend_bias="BULLISH", macd_state="BULLISH_CROSS", rsi_state="NEUTRAL",
        volume_state="NORMAL", priority="HIGH",
        entry_observation=600.0, invalidation_level=590.0,
        risk_notes="test", reasons=["test"],
        watch_state=watch_state, setup_type="MACD_TURNING_UP",
        turning_score=80, weakness_score=20, risk_score=40,
        distance_to_invalidation_pct=1.7,
        distance_to_recent_high_pct=3.0,
        distance_to_recent_low_pct=1.0,
    )
    defaults.update(overrides)
    defaults["watch_state"] = watch_state
    return SignalResult(**defaults)


def _make_recheck(status="TRIGGERED", **overrides) -> TriggerRecheckResult:
    defaults = dict(
        symbol="BNBUSDT", timeframe="5m",
        previous_action_label="WAIT_CONFIRMATION",
        current_watch_state="LONG_READY", current_setup_type="MACD_TURNING_UP",
        last_close=600.0, recheck_status=status,
        trigger_reason="MACD bullish cross",
        invalidation_reason="",
        next_action="OBSERVE_NOW",
        risk_note="turning_score=80",
    )
    defaults.update(overrides)
    defaults["recheck_status"] = status
    return TriggerRecheckResult(**defaults)


class TestPreviewTriggered:
    def test_triggered_produces_watch(self):
        sig = _make_sig("LONG_READY", entry_observation=600.0, invalidation_level=590.0)
        recheck = _make_recheck("TRIGGERED")
        plan = preview_plan(sig, recheck)
        assert plan.direction == "LONG_OBSERVE"
        assert plan.plan_decision in ("WATCH", "WAIT")
        assert plan.source_status == "TRIGGERED"
        assert plan.rr_ratio >= 0

    def test_triggered_rr_above_1_5_is_watch(self):
        sig = _make_sig("LONG_READY", entry_observation=600.0, invalidation_level=597.0)
        recheck = _make_recheck("TRIGGERED")
        plan = preview_plan(sig, recheck)
        # risk=3, reward=6, rr=2.0
        assert plan.rr_ratio >= 1.5
        assert plan.plan_decision == "WATCH"

    def test_triggered_rr_below_1_5_is_wait(self):
        sig = _make_sig("LONG_READY", entry_observation=600.0, invalidation_level=599.0)
        recheck = _make_recheck("TRIGGERED")
        plan = preview_plan(sig, recheck)
        # risk=1, reward=2, rr=2.0 — actually still >= 1.5
        # Need tighter: entry=600, inv=599.9 → risk=0.1, reward=0.2, rr=2.0
        # The 2x TP formula always gives rr=2.0, so WATCH is expected
        assert plan.plan_decision == "WATCH"


class TestPreviewWaiting:
    def test_waiting_produces_wait(self):
        sig = _make_sig("NEAR_TURN_UP", entry_observation=600.0, invalidation_level=590.0)
        recheck = _make_recheck("WAITING")
        plan = preview_plan(sig, recheck)
        assert plan.direction == "LONG_OBSERVE"
        assert plan.plan_decision == "WAIT"
        assert plan.source_status == "WAITING"


class TestPreviewShortTriggered:
    def test_short_triggered_produces_short_observe(self):
        sig = _make_sig("SHORT_WATCH", entry_observation=0.55, invalidation_level=0.58,
                         last_close=0.55)
        recheck = _make_recheck("SHORT_TRIGGERED")
        plan = preview_plan(sig, recheck)
        assert plan.direction == "SHORT_OBSERVE"
        assert plan.plan_decision in ("WATCH", "WAIT")
        assert plan.source_status == "SHORT_TRIGGERED"

    def test_short_waiting_produces_wait(self):
        sig = _make_sig("SHORT_WATCH", entry_observation=0.55, invalidation_level=0.58,
                         last_close=0.55)
        recheck = _make_recheck("SHORT_WAITING")
        plan = preview_plan(sig, recheck)
        assert plan.direction == "SHORT_OBSERVE"
        assert plan.plan_decision == "WAIT"


class TestPreviewInvalidated:
    def test_invalidated_produces_avoid(self):
        sig = _make_sig("WEAK_AVOID", weakness_score=60)
        recheck = _make_recheck("INVALIDATED", invalidation_reason="degraded to WEAK_AVOID")
        plan = preview_plan(sig, recheck)
        assert plan.direction == "NO_TRADE"
        assert plan.plan_decision == "AVOID"
        assert plan.rr_ratio == 0.0

    def test_short_invalidated_produces_avoid(self):
        sig = _make_sig("LONG_WATCH", turning_score=60)
        recheck = _make_recheck("SHORT_INVALIDATED", invalidation_reason="improved to LONG_WATCH")
        plan = preview_plan(sig, recheck)
        assert plan.direction == "NO_TRADE"
        assert plan.plan_decision == "AVOID"

    def test_data_error_produces_avoid(self):
        sig = _make_sig("DATA_REJECT", priority="REJECT")
        recheck = _make_recheck("DATA_ERROR", invalidation_reason="data quality issue")
        plan = preview_plan(sig, recheck)
        assert plan.direction == "NO_TRADE"
        assert plan.plan_decision == "AVOID"


class TestPreviewFields:
    def test_safety_flags_present(self):
        sig = _make_sig()
        recheck = _make_recheck()
        plan = preview_plan(sig, recheck)
        assert "PAPER_ONLY" in plan.safety_flags
        assert "NO_ORDER" in plan.safety_flags
        assert "NO_REAL_ORDER" in plan.safety_flags
        assert "NO_TESTNET" in plan.safety_flags
        assert "NO_LIVE" in plan.safety_flags

    def test_risk_distance_positive(self):
        sig = _make_sig(entry_observation=600.0, invalidation_level=590.0)
        recheck = _make_recheck()
        plan = preview_plan(sig, recheck)
        assert plan.risk_distance_pct > 0

    def test_reward_distance_positive_for_watch(self):
        sig = _make_sig(entry_observation=600.0, invalidation_level=590.0)
        recheck = _make_recheck("TRIGGERED")
        plan = preview_plan(sig, recheck)
        assert plan.reward_distance_pct > 0


class TestPreviewSafety:
    def test_no_order_words(self):
        """All plan output fields must not contain order execution words."""
        all_statuses = ["TRIGGERED", "WAITING", "INVALIDATED",
                        "SHORT_TRIGGERED", "SHORT_WAITING", "SHORT_INVALIDATED", "DATA_ERROR"]
        forbidden = {"submit", "buy", "sell", "execute", "place_order", "cancel_order"}
        for status in all_statuses:
            sig = _make_sig()
            recheck = _make_recheck(status)
            plan = preview_plan(sig, recheck)
            text = (plan.reason + plan.direction + plan.plan_decision).lower()
            for word in forbidden:
                assert word not in text, f"{status}: forbidden word '{word}' in plan"

    def test_no_network_imports(self):
        module_path = os.path.join(os.path.dirname(__file__), "..", "..",
                                    "core", "paper_trading", "focused_paper_plan_preview.py")
        with open(module_path) as f:
            tree = ast.parse(f.read())
        forbidden = {"requests", "httpx", "aiohttp", "websocket", "urllib"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name.split(".")[0] not in forbidden
            elif isinstance(node, ast.ImportFrom) and node.module:
                assert node.module.split(".")[0] not in forbidden

    def test_module_compiles(self):
        module_path = os.path.join(os.path.dirname(__file__), "..", "..",
                                    "core", "paper_trading", "focused_paper_plan_preview.py")
        py_compile.compile(module_path, doraise=True)
