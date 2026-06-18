"""Tests for market data quality validator."""
from __future__ import annotations

import pytest

from core.paper_trading.data_source import MarketBar
from core.paper_trading.market_data_quality import validate_bars, QualityReport


def _good_bar(**overrides) -> MarketBar:
    defaults = dict(
        timestamp=1000.0, open=50000.0, high=51000.0,
        low=49000.0, close=50500.0, volume=100.0,
        symbol="BTCUSDT", timeframe="1h",
    )
    defaults.update(overrides)
    return MarketBar(**defaults)


class TestQualityReport:
    def test_ok_no_issues(self):
        r = QualityReport(symbol="BTCUSDT", timeframe="1h",
                          total_bars=5, valid_bars=5, invalid_bars=0, issues=[])
        assert r.ok is True
        assert r.valid_ratio == 1.0

    def test_not_ok_with_issues(self):
        r = QualityReport(symbol="BTCUSDT", timeframe="1h",
                          total_bars=5, valid_bars=3, invalid_bars=2,
                          issues=["bar[0]:open<=0"])
        assert r.ok is False
        assert r.valid_ratio == 0.6

    def test_empty_bars_ratio(self):
        r = QualityReport(symbol="", timeframe="",
                          total_bars=0, valid_bars=0, invalid_bars=0, issues=[])
        assert r.valid_ratio == 0.0


class TestValidateBars:
    def test_empty_bars(self):
        r = validate_bars([])
        assert r.ok is False
        assert "empty_bars" in r.issues

    def test_valid_bars(self):
        bars = [_good_bar() for _ in range(10)]
        r = validate_bars(bars)
        assert r.ok is True
        assert r.total_bars == 10
        assert r.valid_bars == 10

    def test_negative_open(self):
        bars = [_good_bar(), _good_bar(open=-1.0)]
        r = validate_bars(bars)
        assert r.ok is False
        assert r.invalid_bars == 1

    def test_zero_close(self):
        bars = [_good_bar(close=0.0)]
        r = validate_bars(bars)
        assert r.ok is False

    def test_high_less_than_low(self):
        bars = [_good_bar(high=48000.0, low=49000.0)]
        r = validate_bars(bars)
        assert r.ok is False

    def test_open_above_high(self):
        bars = [_good_bar(open=52000.0)]
        r = validate_bars(bars)
        assert r.ok is False

    def test_close_below_low(self):
        bars = [_good_bar(close=48000.0)]
        r = validate_bars(bars)
        assert r.ok is False

    def test_negative_volume(self):
        bars = [_good_bar(volume=-10.0)]
        r = validate_bars(bars)
        assert r.ok is False

    def test_mixed_valid_invalid(self):
        bars = [_good_bar(), _good_bar(open=-1.0), _good_bar()]
        r = validate_bars(bars)
        assert r.total_bars == 3
        assert r.valid_bars == 2
        assert r.invalid_bars == 1
