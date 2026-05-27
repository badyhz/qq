"""Tests for momentum continuation strategy adapter — T4351-T4380."""
from __future__ import annotations

import pytest

from core.strategy_research_momentum import (
    MomentumParams,
    generate_momentum_signals,
)


def _make_strong_uptrend(n: int = 100) -> list:
    """Generate bars with strong upward momentum."""
    bars = []
    price = 100.0
    for i in range(n):
        price *= 1.004  # ~0.4% per bar
        bars.append({
            "timestamp": 1700000000.0 + i * 300,
            "open": price * 0.999,
            "high": price * 1.001,
            "low": price * 0.998,
            "close": price,
            "volume": 1000.0,
        })
    return bars


def _make_flat_bars(n: int = 100) -> list:
    """Generate flat bars."""
    bars = []
    for i in range(n):
        bars.append({
            "timestamp": 1700000000.0 + i * 300,
            "open": 100.0,
            "high": 100.02,
            "low": 99.98,
            "close": 100.0 + (0.001 if i % 2 == 0 else -0.001),
            "volume": 1000.0,
        })
    return bars


class TestMomentumSignals:
    def test_empty_bars(self):
        signals = generate_momentum_signals([], MomentumParams())
        assert signals == []

    def test_strong_uptrend_generates_long(self):
        bars = _make_strong_uptrend(150)
        params = MomentumParams(
            momentum_lookback_bars=20,
            min_return_pct=0.01,
            ema_fast=5,
            ema_slow=30,
            min_slope_pct=0.0,
        )
        signals = generate_momentum_signals(bars, params)
        assert len(signals) > 0
        assert all(s.side == "LONG" for s in signals)

    def test_flat_no_signals(self):
        bars = _make_flat_bars(100)
        signals = generate_momentum_signals(bars, MomentumParams())
        assert signals == []

    def test_signal_fields(self):
        bars = _make_strong_uptrend(150)
        params = MomentumParams(momentum_lookback_bars=15, min_return_pct=0.01, ema_fast=5, ema_slow=20)
        signals = generate_momentum_signals(bars, params, symbol="BTCUSDT", timeframe="15m")
        if signals:
            sig = signals[0]
            assert sig.strategy_id == "momentum"
            assert sig.symbol == "BTCUSDT"
            assert sig.timeframe == "15m"
            assert sig.entry_reference_price > 0
            assert 0.0 <= sig.confidence <= 1.0
            assert "recent_return_pct" in sig.metadata
            assert "ema_fast" in sig.metadata


class TestMomentumDeterminism:
    def test_deterministic(self):
        bars = _make_strong_uptrend(100)
        params = MomentumParams(momentum_lookback_bars=15, min_return_pct=0.01, ema_fast=5, ema_slow=20)
        s1 = generate_momentum_signals(bars, params)
        s2 = generate_momentum_signals(bars, params)
        assert len(s1) == len(s2)
        for a, b in zip(s1, s2):
            assert a.signal_id == b.signal_id

    def test_no_mutation(self):
        bars = _make_strong_uptrend(80)
        original = [dict(b) for b in bars]
        generate_momentum_signals(bars, MomentumParams())
        for o, b in zip(original, bars):
            assert o == b


class TestMomentumCooldown:
    def test_cooldown_reduces_signals(self):
        bars = _make_strong_uptrend(150)
        base = MomentumParams(momentum_lookback_bars=15, min_return_pct=0.01, ema_fast=5, ema_slow=20)
        with_cd = MomentumParams(momentum_lookback_bars=15, min_return_pct=0.01, ema_fast=5, ema_slow=20, cooldown_bars=10)
        s1 = generate_momentum_signals(bars, base)
        s2 = generate_momentum_signals(bars, with_cd)
        assert len(s2) <= len(s1)
