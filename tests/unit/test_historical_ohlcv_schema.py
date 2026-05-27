"""Tests for core/historical_ohlcv_schema.py — 20+ tests."""
from __future__ import annotations

import pytest

from core.historical_ohlcv_schema import (
    HistoricalBar,
    HistoricalDataIssue,
    HistoricalDataQualityReport,
    HistoricalSymbolDataset,
    HistoricalTimeframe,
    IssueType,
    OHLCVColumnMapping,
    Severity,
)


# ── HistoricalTimeframe ──────────────────────────────────────────────────

class TestHistoricalTimeframe:
    def test_valid(self):
        tf = HistoricalTimeframe(label="5m", minutes=5)
        assert tf.label == "5m"
        assert tf.minutes == 5

    def test_empty_label_rejected(self):
        with pytest.raises(ValueError, match="non-empty string"):
            HistoricalTimeframe(label="", minutes=5)

    def test_zero_minutes_rejected(self):
        with pytest.raises(ValueError, match="positive integer"):
            HistoricalTimeframe(label="5m", minutes=0)

    def test_negative_minutes_rejected(self):
        with pytest.raises(ValueError, match="positive integer"):
            HistoricalTimeframe(label="5m", minutes=-1)

    def test_frozen(self):
        tf = HistoricalTimeframe(label="1h", minutes=60)
        with pytest.raises(AttributeError):
            tf.label = "2h"  # type: ignore[misc]


# ── HistoricalBar ─────────────────────────────────────────────────────────

class TestHistoricalBar:
    def _make(self, **kw):
        defaults = dict(
            timestamp=1700000000.0, open=100.0, high=110.0, low=90.0,
            close=105.0, volume=500.0, symbol="BTC", timeframe="5m",
        )
        defaults.update(kw)
        return HistoricalBar(**defaults)

    def test_valid(self):
        bar = self._make()
        assert bar.symbol == "BTC"
        assert bar.high >= bar.low

    def test_high_less_than_low_rejected(self):
        with pytest.raises(ValueError, match="high.*low"):
            self._make(high=80.0, low=90.0)

    def test_negative_volume_rejected(self):
        with pytest.raises(ValueError, match="non-negative"):
            self._make(volume=-1.0)

    def test_empty_symbol_rejected(self):
        with pytest.raises(ValueError, match="non-empty"):
            self._make(symbol="")

    def test_empty_timeframe_rejected(self):
        with pytest.raises(ValueError, match="non-empty"):
            self._make(timeframe="")

    def test_frozen(self):
        bar = self._make()
        with pytest.raises(AttributeError):
            bar.close = 0.0  # type: ignore[misc]

    def test_high_equals_low_allowed(self):
        bar = self._make(high=100.0, low=100.0)
        assert bar.high == bar.low

    def test_zero_volume_allowed(self):
        bar = self._make(volume=0.0)
        assert bar.volume == 0.0


# ── HistoricalDataIssue ──────────────────────────────────────────────────

class TestHistoricalDataIssue:
    def test_valid(self):
        issue = HistoricalDataIssue(
            issue_type=IssueType.GAP,
            severity=Severity.WARNING,
            timestamp=1700000000.0,
            detail="missing bar",
        )
        assert issue.issue_type == IssueType.GAP

    def test_empty_detail_rejected(self):
        with pytest.raises(ValueError, match="non-empty"):
            HistoricalDataIssue(
                issue_type=IssueType.GAP,
                severity=Severity.WARNING,
                timestamp=0.0,
                detail="",
            )

    def test_frozen(self):
        issue = HistoricalDataIssue(
            issue_type=IssueType.DUPLICATE,
            severity=Severity.ERROR,
            timestamp=0.0,
            detail="dup",
        )
        with pytest.raises(AttributeError):
            issue.detail = "x"  # type: ignore[misc]


# ── OHLCVColumnMapping ────────────────────────────────────────────────────

class TestOHLCVColumnMapping:
    def test_valid(self):
        m = OHLCVColumnMapping(
            timestamp_col="ts", open_col="o", high_col="h",
            low_col="l", close_col="c", volume_col="v",
        )
        assert m.timestamp_col == "ts"

    def test_empty_col_rejected(self):
        with pytest.raises(ValueError, match="non-empty string"):
            OHLCVColumnMapping(
                timestamp_col="", open_col="o", high_col="h",
                low_col="l", close_col="c", volume_col="v",
            )


# ── HistoricalDataQualityReport ──────────────────────────────────────────

class TestHistoricalDataQualityReport:
    def test_clean_report(self):
        r = HistoricalDataQualityReport(
            symbol="BTC", timeframe="5m", total_rows=50, valid_rows=50,
            duplicate_count=0, gap_count=0, invalid_ohlcv_count=0,
            issues=(), is_clean=True,
        )
        assert r.is_clean is True

    def test_dirty_report(self):
        r = HistoricalDataQualityReport(
            symbol="BTC", timeframe="5m", total_rows=50, valid_rows=48,
            duplicate_count=1, gap_count=1, invalid_ohlcv_count=0,
            issues=(), is_clean=False,
        )
        assert r.is_clean is False

    def test_is_clean_inconsistency_rejected(self):
        with pytest.raises(ValueError, match="inconsistent"):
            HistoricalDataQualityReport(
                symbol="BTC", timeframe="5m", total_rows=50, valid_rows=50,
                duplicate_count=1, gap_count=0, invalid_ohlcv_count=0,
                issues=(), is_clean=True,
            )

    def test_valid_rows_exceeds_total_rejected(self):
        with pytest.raises(ValueError, match="cannot exceed"):
            HistoricalDataQualityReport(
                symbol="BTC", timeframe="5m", total_rows=10, valid_rows=20,
                duplicate_count=0, gap_count=0, invalid_ohlcv_count=0,
                issues=(), is_clean=True,
            )


# ── HistoricalSymbolDataset ──────────────────────────────────────────────

class TestHistoricalSymbolDataset:
    def test_valid(self):
        bars = (
            HistoricalBar(1.0, 10, 11, 9, 10, 1, "BTC", "5m"),
            HistoricalBar(2.0, 10, 11, 9, 10, 1, "BTC", "5m"),
        )
        ds = HistoricalSymbolDataset(
            symbol="BTC", timeframe="5m", bars=bars, bar_count=2,
        )
        assert ds.bar_count == 2

    def test_bar_count_mismatch_rejected(self):
        bars = (HistoricalBar(1.0, 10, 11, 9, 10, 1, "BTC", "5m"),)
        with pytest.raises(ValueError, match="bar_count"):
            HistoricalSymbolDataset(
                symbol="BTC", timeframe="5m", bars=bars, bar_count=5,
            )
