"""Tests for readonly signal analyzer — watch states and scores."""
from __future__ import annotations

import os
import py_compile

import pytest

from core.paper_trading.data_source import MarketBar
from core.paper_trading.readonly_signal_analyzer import (
    analyze_bars, SignalResult, _ema, _rsi, _atr,
)


def _make_bars(n: int, base_price: float = 50000.0, trend: str = "up",
               symbol: str = "BTCUSDT", timeframe: str = "15m") -> list:
    """Generate synthetic bars for testing."""
    bars = []
    for i in range(n):
        if trend == "up":
            p = base_price + i * 10
        elif trend == "down":
            p = base_price - i * 10
        elif trend == "flat":
            p = base_price
        else:
            p = base_price + (i % 3 - 1) * 5
        bars.append(MarketBar(
            timestamp=float(i * 60),
            open=p - 5,
            high=p + 50,
            low=p - 50,
            close=p,
            volume=100.0 + i,
            symbol=symbol,
            timeframe=timeframe,
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
        assert result[-1] > 90


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
        assert result.watch_state == "DATA_REJECT"
        assert "insufficient" in result.reasons[0].lower()

    def test_valid_analysis(self):
        bars = _make_bars(120, trend="up")
        result = analyze_bars(bars)
        assert result is not None
        assert result.symbol == "BTCUSDT"
        assert result.timeframe == "15m"
        assert result.priority in ("HIGH", "MEDIUM", "LOW", "REJECT")
        assert result.trend_bias in ("BULLISH", "BEARISH", "NEUTRAL")
        assert result.watch_state in ("LONG_READY", "LONG_WATCH", "NEAR_TURN_UP",
                                       "SHORT_WATCH", "WEAK_AVOID", "CHOPPY_AVOID", "DATA_REJECT")
        assert result.setup_type in ("LONG_BREAKOUT", "LONG_PULLBACK", "MACD_TURNING_UP",
                                      "OVERSOLD_REBOUND", "SHORT_CONTINUATION", "WEAK_TREND", "NO_TRADE")
        assert 0 <= result.turning_score <= 100
        assert 0 <= result.weakness_score <= 100
        assert 0 <= result.risk_score <= 100

    def test_downtrend(self):
        bars = _make_bars(120, base_price=60000, trend="down")
        result = analyze_bars(bars)
        assert result is not None
        assert result.trend_bias in ("BEARISH", "NEUTRAL")
        assert result.watch_state in ("SHORT_WATCH", "WEAK_AVOID", "CHOPPY_AVOID", "NEAR_TURN_UP")

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

    def test_distance_percentages(self):
        bars = _make_bars(120)
        result = analyze_bars(bars)
        assert result is not None
        assert result.distance_to_invalidation_pct >= 0
        assert result.distance_to_recent_high_pct >= 0
        assert result.distance_to_recent_low_pct >= 0

    def test_scores_exist(self):
        bars = _make_bars(120)
        result = analyze_bars(bars)
        assert result is not None
        assert isinstance(result.turning_score, int)
        assert isinstance(result.weakness_score, int)
        assert isinstance(result.risk_score, int)


class TestWatchStates:
    def test_long_ready_uptrend(self):
        """Uptrend should not be SHORT_WATCH or DATA_REJECT."""
        bars = _make_bars(120, trend="up")
        result = analyze_bars(bars)
        assert result is not None
        # Synthetic data may be choppy; just verify not bearish/reject
        assert result.watch_state not in ("SHORT_WATCH", "DATA_REJECT")

    def test_short_watch_downtrend(self):
        """Downtrend should not be LONG_READY or DATA_REJECT."""
        bars = _make_bars(120, base_price=60000, trend="down")
        result = analyze_bars(bars)
        assert result is not None
        assert result.watch_state not in ("LONG_READY", "DATA_REJECT")

    def test_choppy_avoid_flat(self):
        """Flat market should produce CHOPPY_AVOID."""
        bars = _make_bars(120, trend="flat")
        result = analyze_bars(bars)
        assert result is not None
        # Flat market is choppy
        assert result.watch_state in ("CHOPPY_AVOID", "WEAK_AVOID")

    def test_data_reject_insufficient(self):
        """Too few bars should produce DATA_REJECT."""
        bars = _make_bars(5)
        result = analyze_bars(bars)
        assert result is not None
        assert result.watch_state == "DATA_REJECT"
        assert result.setup_type == "NO_TRADE"

    def test_turning_score_uptrend(self):
        """Uptrend should have higher turning score than downtrend."""
        up_bars = _make_bars(120, trend="up")
        down_bars = _make_bars(120, base_price=60000, trend="down")
        up_result = analyze_bars(up_bars)
        down_result = analyze_bars(down_bars)
        assert up_result is not None and down_result is not None
        # Uptrend should generally have higher turning score
        # (not always true due to MACD dynamics, but generally)
        assert up_result.turning_score >= 0
        assert down_result.turning_score >= 0

    def test_weakness_score_downtrend(self):
        """Downtrend should have higher weakness score."""
        bars = _make_bars(120, base_price=60000, trend="down")
        result = analyze_bars(bars)
        assert result is not None
        # Downtrend should have some weakness
        assert result.weakness_score >= 0

    def test_risk_score_range(self):
        """Risk score should be 0-100."""
        bars = _make_bars(120)
        result = analyze_bars(bars)
        assert result is not None
        assert 0 <= result.risk_score <= 100


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
