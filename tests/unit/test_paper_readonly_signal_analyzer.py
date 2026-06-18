"""Tests for readonly signal analyzer."""
from __future__ import annotations

import os
import py_compile

import pytest

from core.paper_trading.data_source import MarketBar
from core.paper_trading.readonly_signal_analyzer import (
    analyze_bars, SignalResult, _ema, _rsi, _atr,
)


def _make_bars(n: int, base_price: float = 50000.0, trend: str = "up") -> list:
    """Generate synthetic bars for testing."""
    bars = []
    for i in range(n):
        if trend == "up":
            p = base_price + i * 10
        elif trend == "down":
            p = base_price - i * 10
        else:
            p = base_price + (i % 3 - 1) * 5
        bars.append(MarketBar(
            timestamp=float(i * 60),
            open=p - 5,
            high=p + 50,
            low=p - 50,
            close=p,
            volume=100.0 + i,
            symbol="BTCUSDT",
            timeframe="15m",
        ))
    return bars


class TestEMA:
    def test_short_input(self):
        result = _ema([1.0, 2.0, 3.0], 12)
        assert all(v is None for v in result)

    def test_exact_period(self):
        values = [float(i) for i in range(12)]
        result = _ema(values, 12)
        assert result[10] is None
        assert result[11] is not None

    def test_ema_values(self):
        values = [float(i) for i in range(20)]
        result = _ema(values, 12)
        assert result[-1] is not None
        assert result[-1] > 0


class TestRSI:
    def test_short_input(self):
        result = _rsi([1.0, 2.0], 14)
        assert all(v is None for v in result)

    def test_rsi_range(self):
        closes = [float(50000 + i * 10) for i in range(30)]
        result = _rsi(closes, 14)
        last = result[-1]
        assert last is not None
        assert 0 <= last <= 100

    def test_all_up(self):
        closes = [float(i) for i in range(1, 31)]
        result = _rsi(closes, 14)
        assert result[-1] is not None
        assert result[-1] > 90  # Strong uptrend


class TestATR:
    def test_short_input(self):
        result = _atr([1.0], [0.5], [0.8], 14)
        assert all(v is None for v in result)

    def test_atr_positive(self):
        n = 30
        highs = [float(50000 + i * 10 + 50) for i in range(n)]
        lows = [float(50000 + i * 10 - 50) for i in range(n)]
        closes = [float(50000 + i * 10) for i in range(n)]
        result = _atr(highs, lows, closes, 14)
        assert result[-1] is not None
        assert result[-1] > 0


class TestAnalyzeBars:
    def test_too_few_bars(self):
        bars = _make_bars(5)
        result = analyze_bars(bars)
        assert result is not None
        assert result.priority == "REJECT"
        assert "insufficient" in result.reasons[0].lower()

    def test_valid_analysis(self):
        bars = _make_bars(120, trend="up")
        result = analyze_bars(bars)
        assert result is not None
        assert result.symbol == "BTCUSDT"
        assert result.timeframe == "15m"
        assert result.priority in ("HIGH", "MEDIUM", "LOW", "REJECT")
        assert result.trend_bias in ("BULLISH", "BEARISH", "NEUTRAL")
        assert result.macd_state in ("BULLISH_CROSS", "BEARISH_CROSS",
                                      "HIST_EXPANDING_GREEN", "HIST_EXPANDING_RED", "NEUTRAL")
        assert result.rsi_state in ("OVERSOLD", "NEUTRAL", "OVERBOUGHT")
        assert result.volume_state in ("NORMAL", "SPIKE")

    def test_downtrend(self):
        bars = _make_bars(120, base_price=60000, trend="down")
        result = analyze_bars(bars)
        assert result is not None
        assert result.trend_bias in ("BEARISH", "NEUTRAL")

    def test_has_reasons(self):
        bars = _make_bars(120)
        result = analyze_bars(bars)
        assert result is not None
        assert len(result.reasons) > 0

    def test_invalidation_level(self):
        bars = _make_bars(120)
        result = analyze_bars(bars)
        assert result is not None
        assert result.invalidation_level < result.last_close


class TestSignalAnalyzerSafety:
    def test_no_network_imports(self):
        module_path = os.path.join(os.path.dirname(__file__), "..", "..",
                                    "core", "paper_trading", "readonly_signal_analyzer.py")
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
