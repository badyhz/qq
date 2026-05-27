"""Tests for volatility compression breakout adapter — T4381-T4410."""
from __future__ import annotations

import pytest

from core.strategy_research_volatility_compression import (
    VolatilityCompressionParams,
    generate_volatility_compression_signals,
)


def _make_compression_then_breakout(n: int = 100) -> list:
    """Low volatility compression followed by breakout."""
    bars = []
    price = 100.0
    # Compression phase
    for i in range(2 * n // 3):
        bars.append({
            "timestamp": 1700000000.0 + i * 300,
            "open": price - 0.05,
            "high": price + 0.1,
            "low": price - 0.1,
            "close": price + (0.01 if i % 2 == 0 else -0.01),
            "volume": 1000.0,
        })
    # Breakout phase
    for i in range(2 * n // 3, n):
        price += 1.5
        bars.append({
            "timestamp": 1700000000.0 + i * 300,
            "open": price - 0.5,
            "high": price + 0.3,
            "low": price - 0.2,
            "close": price,
            "volume": 3000.0,
        })
    return bars


def _make_high_volatility_bars(n: int = 100) -> list:
    """High volatility — no compression."""
    bars = []
    price = 100.0
    for i in range(n):
        price += (2.0 if i % 2 == 0 else -2.0)
        bars.append({
            "timestamp": 1700000000.0 + i * 300,
            "open": price - 1.5,
            "high": price + 2.0,
            "low": price - 2.0,
            "close": price,
            "volume": 1000.0,
        })
    return bars


class TestVolatilityCompressionSignals:
    def test_empty_bars(self):
        signals = generate_volatility_compression_signals([], VolatilityCompressionParams())
        assert signals == []

    def test_compression_then_breakout(self):
        bars = _make_compression_then_breakout(100)
        params = VolatilityCompressionParams(
            compression_lookback_bars=15,
            max_range_pct=0.005,
            breakout_lookback_bars=10,
            breakout_buffer_pct=0.002,
            volume_expansion_ratio=1.0,
        )
        signals = generate_volatility_compression_signals(bars, params)
        assert len(signals) > 0

    def test_no_signal_in_high_volatility(self):
        bars = _make_high_volatility_bars(100)
        params = VolatilityCompressionParams(
            compression_lookback_bars=15,
            max_range_pct=0.005,
            breakout_lookback_bars=10,
            breakout_buffer_pct=0.002,
        )
        signals = generate_volatility_compression_signals(bars, params)
        assert signals == []

    def test_signal_fields(self):
        bars = _make_compression_then_breakout(100)
        params = VolatilityCompressionParams(
            compression_lookback_bars=15,
            max_range_pct=0.005,
            breakout_lookback_bars=10,
            breakout_buffer_pct=0.002,
            volume_expansion_ratio=1.0,
        )
        signals = generate_volatility_compression_signals(bars, params, symbol="BTCUSDT", timeframe="5m")
        if signals:
            sig = signals[0]
            assert sig.strategy_id == "volatility_compression"
            assert sig.symbol == "BTCUSDT"
            assert sig.entry_reference_price > 0
            assert 0.0 <= sig.confidence <= 1.0
            assert "volume_expanding" in sig.metadata


class TestVolCompressionDeterminism:
    def test_deterministic(self):
        bars = _make_compression_then_breakout(100)
        params = VolatilityCompressionParams(
            compression_lookback_bars=15, max_range_pct=0.005,
            breakout_lookback_bars=10, breakout_buffer_pct=0.002,
            volume_expansion_ratio=1.0,
        )
        s1 = generate_volatility_compression_signals(bars, params)
        s2 = generate_volatility_compression_signals(bars, params)
        assert len(s1) == len(s2)
        for a, b in zip(s1, s2):
            assert a.signal_id == b.signal_id

    def test_no_mutation(self):
        bars = _make_compression_then_breakout(80)
        original = [dict(b) for b in bars]
        generate_volatility_compression_signals(bars, VolatilityCompressionParams())
        for o, b in zip(original, bars):
            assert o == b
