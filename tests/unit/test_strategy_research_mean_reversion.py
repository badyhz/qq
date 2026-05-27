"""Tests for mean reversion strategy research adapter — T4321-T4350."""
from __future__ import annotations

import pytest

from core.strategy_research_mean_reversion import (
    MeanReversionParams,
    generate_mean_reversion_signals,
)


def _make_bars_with_dip(n: int = 80, base_price: float = 100.0) -> list:
    """Generate bars: stable, then sharp dip, then recovery."""
    bars = []
    for i in range(n):
        if i < n // 3:
            price = base_price
        elif i < 2 * n // 3:
            # Sharp dip
            price = base_price - (i - n // 3) * 0.5
        else:
            # Recovery
            price = base_price * 0.8 + (i - 2 * n // 3) * 0.3
        bars.append({
            "timestamp": 1700000000.0 + i * 300,
            "open": price + 0.1,
            "high": price + 0.5,
            "low": price - 0.5,
            "close": price,
            "volume": 1000.0,
        })
    return bars


def _make_flat_bars(n: int = 80, price: float = 100.0) -> list:
    """Flat bars with minimal variance."""
    bars = []
    for i in range(n):
        bars.append({
            "timestamp": 1700000000.0 + i * 300,
            "open": price + 0.01,
            "high": price + 0.02,
            "low": price - 0.02,
            "close": price + (0.001 if i % 2 == 0 else -0.001),
            "volume": 1000.0,
        })
    return bars


class TestMeanReversionSignals:
    def test_empty_bars(self):
        signals = generate_mean_reversion_signals([], MeanReversionParams())
        assert signals == []

    def test_dip_generates_long_signals(self):
        bars = _make_bars_with_dip(120)
        params = MeanReversionParams(lookback_bars=20, zscore_entry=1.5)
        signals = generate_mean_reversion_signals(bars, params)
        assert len(signals) > 0
        assert all(s.side == "LONG" for s in signals)

    def test_flat_no_signals(self):
        bars = _make_flat_bars(100)
        params = MeanReversionParams(lookback_bars=10, zscore_entry=1.5)
        signals = generate_mean_reversion_signals(bars, params)
        assert signals == []

    def test_signal_fields(self):
        bars = _make_bars_with_dip(120)
        params = MeanReversionParams(lookback_bars=15, zscore_entry=1.0)
        signals = generate_mean_reversion_signals(bars, params, symbol="ETHUSDT", timeframe="15m")
        if signals:
            sig = signals[0]
            assert sig.strategy_id == "mean_reversion"
            assert sig.symbol == "ETHUSDT"
            assert sig.timeframe == "15m"
            assert sig.entry_reference_price > 0
            assert 0.0 <= sig.confidence <= 1.0
            assert "zscore" in sig.metadata


class TestMeanReversionDeterminism:
    def test_deterministic(self):
        bars = _make_bars_with_dip(100)
        params = MeanReversionParams(lookback_bars=20, zscore_entry=1.5)
        s1 = generate_mean_reversion_signals(bars, params)
        s2 = generate_mean_reversion_signals(bars, params)
        assert len(s1) == len(s2)
        for a, b in zip(s1, s2):
            assert a.signal_id == b.signal_id
            assert a.timestamp == b.timestamp

    def test_no_mutation(self):
        bars = _make_bars_with_dip(80)
        original = [dict(b) for b in bars]
        generate_mean_reversion_signals(bars, MeanReversionParams())
        for o, b in zip(original, bars):
            assert o == b


class TestMeanReversionCooldown:
    def test_cooldown_reduces_signals(self):
        bars = _make_bars_with_dip(120)
        p1 = MeanReversionParams(lookback_bars=15, zscore_entry=1.0, cooldown_bars=0)
        p2 = MeanReversionParams(lookback_bars=15, zscore_entry=1.0, cooldown_bars=20)
        s1 = generate_mean_reversion_signals(bars, p1)
        s2 = generate_mean_reversion_signals(bars, p2)
        assert len(s2) <= len(s1)


class TestStdZeroSafety:
    def test_std_zero_no_crash(self):
        """When all closes identical, std=0, should not crash."""
        bars = []
        for i in range(80):
            bars.append({
                "timestamp": 1700000000.0 + i * 300,
                "open": 100.0,
                "high": 100.0,
                "low": 100.0,
                "close": 100.0,
                "volume": 1000.0,
            })
        signals = generate_mean_reversion_signals(bars, MeanReversionParams(lookback_bars=10))
        assert signals == []
