from __future__ import annotations

import pytest

from core.historical_ohlcv_schema import HistoricalBar
from core.paper_trading.higher_timeframe_trend import (
    align_higher_timeframe_trends,
    timeframe_seconds,
)
from core.paper_trading.indicator_composite_strategy import HigherTimeframeTrend


def _bar(index: int, timeframe: str, seconds: int, close: float) -> HistoricalBar:
    return HistoricalBar(
        timestamp=float(index * seconds),
        open=close - 0.5,
        high=close + 1.0,
        low=close - 1.0,
        close=close,
        volume=1000.0,
        symbol="BTCUSDT",
        timeframe=timeframe,
    )


def test_timeframe_seconds_contract():
    assert timeframe_seconds("15m") == 900
    assert timeframe_seconds("1h") == 3600
    assert timeframe_seconds("4h") == 14400
    with pytest.raises(ValueError, match="unsupported"):
        timeframe_seconds("7m")


def test_empty_higher_series_maps_to_neutral():
    lower = [_bar(i, "15m", 900, 100.0) for i in range(3)]
    trends = align_higher_timeframe_trends(lower, [])
    assert trends == (
        HigherTimeframeTrend.NEUTRAL,
        HigherTimeframeTrend.NEUTRAL,
        HigherTimeframeTrend.NEUTRAL,
    )


def test_unclosed_higher_bar_cannot_change_lower_decision():
    # 30 fully closed rising 1h bars are enough for the existing analyzer.
    higher_closed = [_bar(i, "1h", 3600, 100.0 + i) for i in range(30)]
    # This next 1h bar is intentionally absurdly bearish but does not close
    # until 31h. It must not influence the lower decision at exactly 30h.
    future_unclosed = _bar(30, "1h", 3600, 1.0)

    decision_lower = HistoricalBar(
        timestamp=float(30 * 3600 - 900),  # 15m bar closes exactly at 30h
        open=130.0,
        high=131.0,
        low=129.0,
        close=130.0,
        volume=1000.0,
        symbol="BTCUSDT",
        timeframe="15m",
    )

    without_future = align_higher_timeframe_trends(
        [decision_lower], higher_closed
    )
    with_future = align_higher_timeframe_trends(
        [decision_lower], higher_closed + [future_unclosed]
    )

    assert without_future == with_future
    assert without_future[0] == HigherTimeframeTrend.UP


def test_higher_timeframe_must_really_be_higher():
    lower = [_bar(i, "1h", 3600, 100.0) for i in range(2)]
    same = [_bar(i, "1h", 3600, 100.0) for i in range(2)]
    with pytest.raises(ValueError, match="strictly larger"):
        align_higher_timeframe_trends(lower, same)


def test_mixed_higher_timeframes_fail_closed():
    lower = [_bar(i, "15m", 900, 100.0) for i in range(2)]
    higher = [
        _bar(0, "1h", 3600, 100.0),
        _bar(1, "4h", 14400, 101.0),
    ]
    with pytest.raises(ValueError, match="mixed timeframes"):
        align_higher_timeframe_trends(lower, higher)


def test_analyzer_limit_below_existing_minimum_is_rejected():
    lower = [_bar(0, "15m", 900, 100.0)]
    higher = [_bar(0, "1h", 3600, 100.0)]
    with pytest.raises(ValueError, match=">= 30"):
        align_higher_timeframe_trends(lower, higher, analyzer_limit=20)
