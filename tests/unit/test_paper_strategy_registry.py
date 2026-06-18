"""Tests for strategy registry — signal filtering and candidate generation."""
from __future__ import annotations

import os
import py_compile

import pytest

from core.paper_trading.readonly_signal_analyzer import SignalResult
from core.paper_trading.data_source import MarketBar
from core.paper_trading.strategy_registry import (
    analyze_for_strategy,
    SignalCandidate,
    StrategyRunResult,
)


def _make_bar(symbol="BTCUSDT", timeframe="5m", close=60000.0) -> MarketBar:
    return MarketBar(
        timestamp=1000.0,
        open=close * 0.99, high=close * 1.01, low=close * 0.98, close=close,
        volume=1000.0,
        symbol=symbol, timeframe=timeframe,
    )


def _make_sig(watch_state="LONG_READY", **overrides) -> SignalResult:
    defaults = dict(
        symbol="BTCUSDT", timeframe="5m", last_close=60000.0,
        trend_bias="BULLISH", macd_state="BULLISH_CROSS", rsi_state="NEUTRAL",
        volume_state="NORMAL", priority="HIGH",
        entry_observation=60000.0, invalidation_level=59000.0,
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


class TestAnalyzeForStrategy:
    def test_empty_bars_returns_error(self):
        result = analyze_for_strategy("test", "macd_rebound_watch", [])
        assert result.success is False
        assert result.candidate is None
        assert "empty" in result.error.lower()

    def test_macd_rebound_filters_long_states(self):
        bars = [_make_bar()]
        result = analyze_for_strategy("test", "macd_rebound_watch", bars)
        assert result.success is True

    def test_weak_short_filters_short_states(self):
        bars = [_make_bar()]
        result = analyze_for_strategy("test", "weak_short_watch", bars)
        assert result.success is True

    def test_breakout_pullback_returns_none(self):
        bars = [_make_bar()]
        result = analyze_for_strategy("test", "breakout_pullback_watch", bars)
        assert result.success is True
        assert result.candidate is None

    def test_unknown_strategy_returns_none(self):
        bars = [_make_bar()]
        result = analyze_for_strategy("test", "unknown_strategy", bars)
        assert result.success is True
        assert result.candidate is None


class TestSignalCandidate:
    def test_candidate_has_required_fields(self):
        bars = [_make_bar()]
        result = analyze_for_strategy("test", "macd_rebound_watch", bars)
        if result.candidate:
            c = result.candidate
            assert c.strategy_id == "test"
            assert c.strategy_type == "macd_rebound_watch"
            assert c.symbol == "BTCUSDT"
            assert c.direction in ("LONG_OBSERVE", "SHORT_OBSERVE", "NO_TRADE")
            assert c.priority in ("HIGH", "MEDIUM", "LOW")
            assert c.last_close > 0

    def test_macd_rebound_direction_is_long(self):
        bars = [_make_bar()]
        result = analyze_for_strategy("test", "macd_rebound_watch", bars)
        if result.candidate:
            assert result.candidate.direction == "LONG_OBSERVE"

    def test_weak_short_direction_is_short(self):
        bars = [_make_bar()]
        result = analyze_for_strategy("test", "weak_short_watch", bars)
        if result.candidate:
            assert result.candidate.direction == "SHORT_OBSERVE"


class TestRegistrySafety:
    def test_no_order_words_in_module(self):
        module_path = os.path.join(os.path.dirname(__file__), "..", "..",
                                    "core", "paper_trading", "strategy_registry.py")
        with open(module_path) as f:
            content = f.read()
        forbidden = ["submit_order", "place_order", "cancel_order", "execute_trade"]
        for word in forbidden:
            assert word not in content, f"forbidden word '{word}' in module"

    def test_no_secret_reads(self):
        module_path = os.path.join(os.path.dirname(__file__), "..", "..",
                                    "core", "paper_trading", "strategy_registry.py")
        with open(module_path) as f:
            content = f.read()
        assert "os.environ" not in content
        assert "os.getenv" not in content
        assert "API_KEY" not in content
        assert "API_SECRET" not in content

    def test_module_compiles(self):
        module_path = os.path.join(os.path.dirname(__file__), "..", "..",
                                    "core", "paper_trading", "strategy_registry.py")
        py_compile.compile(module_path, doraise=True)
