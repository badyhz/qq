"""Tests for breakout strategy research adapter — T4291-T4320."""
from __future__ import annotations

import pytest

from core.strategy_research_breakout import (
    BreakoutResearchParams,
    generate_breakout_signals,
)
from core.strategy_research_interface import StrategySignal


# --- Helpers ---

def _make_uptrend_bars(n: int = 60, start_price: float = 100.0) -> list:
    """Generate bars with a strong breakout move after flat consolidation."""
    bars = []
    price = start_price
    # First half: flat consolidation range
    for i in range(n // 2):
        bars.append({
            "timestamp": 1700000000.0 + i * 300,
            "open": price - 0.1,
            "high": price + 0.5,
            "low": price - 0.5,
            "close": price,
            "volume": 1000.0,
        })
    # Second half: strong breakout candles
    for i in range(n // 2, n):
        price += 2.0  # big move up
        bars.append({
            "timestamp": 1700000000.0 + i * 300,
            "open": price - 1.5,
            "high": price + 0.5,
            "low": price - 0.5,
            "close": price,
            "volume": 3000.0,
        })
    return bars


def _make_downtrend_bars(n: int = 60, start_price: float = 200.0) -> list:
    """Generate bars with a strong breakdown move after flat consolidation."""
    bars = []
    price = start_price
    # First half: flat consolidation
    for i in range(n // 2):
        bars.append({
            "timestamp": 1700000000.0 + i * 300,
            "open": price + 0.1,
            "high": price + 0.5,
            "low": price - 0.5,
            "close": price,
            "volume": 1000.0,
        })
    # Second half: strong breakdown candles
    for i in range(n // 2, n):
        price -= 2.0  # big move down
        bars.append({
            "timestamp": 1700000000.0 + i * 300,
            "open": price + 1.5,
            "high": price + 0.5,
            "low": price - 0.5,
            "close": price,
            "volume": 3000.0,
        })
    return bars


def _make_flat_bars(n: int = 60, price: float = 100.0) -> list:
    """Generate flat bars (no breakout)."""
    bars = []
    for i in range(n):
        bars.append({
            "timestamp": 1700000000.0 + i * 300,
            "open": price - 0.01,
            "high": price + 0.02,
            "low": price - 0.02,
            "close": price,
            "volume": 1000.0,
        })
    return bars


# --- Signal generation ---

class TestBreakoutSignalGeneration:
    def test_empty_bars_no_signals(self):
        params = BreakoutResearchParams()
        signals = generate_breakout_signals([], params)
        assert signals == []

    def test_uptrend_generates_long_signals(self):
        bars = _make_uptrend_bars(100)
        params = BreakoutResearchParams(lookback_bars=10, breakout_buffer_pct=0.001)
        signals = generate_breakout_signals(bars, params)
        assert len(signals) > 0
        long_signals = [s for s in signals if s.side == "LONG"]
        assert len(long_signals) > 0

    def test_downtrend_generates_short_signals(self):
        bars = _make_downtrend_bars(100)
        params = BreakoutResearchParams(lookback_bars=10, breakout_buffer_pct=0.001)
        signals = generate_breakout_signals(bars, params)
        short_signals = [s for s in signals if s.side == "SHORT"]
        assert len(short_signals) > 0

    def test_flat_bars_no_signals(self):
        bars = _make_flat_bars(100)
        params = BreakoutResearchParams(lookback_bars=10, breakout_buffer_pct=0.005)
        signals = generate_breakout_signals(bars, params)
        assert signals == []

    def test_signal_has_required_fields(self):
        bars = _make_uptrend_bars(60)
        params = BreakoutResearchParams(lookback_bars=5, breakout_buffer_pct=0.001)
        signals = generate_breakout_signals(bars, params, symbol="BTCUSDT", timeframe="5m")
        assert len(signals) > 0
        sig = signals[0]
        assert sig.signal_id
        assert sig.strategy_id == "breakout"
        assert sig.symbol == "BTCUSDT"
        assert sig.timeframe == "5m"
        assert sig.timestamp > 0
        assert sig.side in ("LONG", "SHORT")
        assert sig.entry_reference_price > 0
        assert 0.0 <= sig.confidence <= 1.0


# --- Cooldown ---

class TestBreakoutCooldown:
    def test_cooldown_prevents_consecutive_signals(self):
        bars = _make_uptrend_bars(100)
        params = BreakoutResearchParams(lookback_bars=5, breakout_buffer_pct=0.001, cooldown_bars=10)
        signals = generate_breakout_signals(bars, params)
        # With high cooldown, fewer signals
        params_no_cooldown = BreakoutResearchParams(lookback_bars=5, breakout_buffer_pct=0.001, cooldown_bars=0)
        signals_no_cd = generate_breakout_signals(bars, params_no_cooldown)
        assert len(signals) <= len(signals_no_cd)


# --- Determinism ---

class TestBreakoutDeterminism:
    def test_deterministic_output(self):
        bars = _make_uptrend_bars(80)
        params = BreakoutResearchParams(lookback_bars=10, breakout_buffer_pct=0.001)
        s1 = generate_breakout_signals(bars, params)
        s2 = generate_breakout_signals(bars, params)
        assert len(s1) == len(s2)
        for a, b in zip(s1, s2):
            assert a.signal_id == b.signal_id
            assert a.timestamp == b.timestamp
            assert a.side == b.side
            assert a.entry_reference_price == b.entry_reference_price

    def test_no_mutation_of_input(self):
        bars = _make_uptrend_bars(60)
        original_first = dict(bars[0])
        params = BreakoutResearchParams(lookback_bars=5, breakout_buffer_pct=0.001)
        generate_breakout_signals(bars, params)
        assert bars[0] == original_first
