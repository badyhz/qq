"""Tests for core/historical_ohlcv_chunked_reader.py — 20+ tests."""
from __future__ import annotations

import csv
from pathlib import Path

import pytest

from core.historical_ohlcv_chunked_reader import (
    deduplicate_bars,
    detect_gaps,
    read_ohlcv_chunks,
    summarize_dataset,
    validate_ohlcv_chunk,
)
from core.historical_ohlcv_schema import (
    HistoricalBar,
    IssueType,
    OHLCVColumnMapping,
)

FIX = Path(__file__).resolve().parent.parent / "fixtures" / "historical_backtest_lab"
MAPPING = OHLCVColumnMapping(
    timestamp_col="timestamp", open_col="open", high_col="high",
    low_col="low", close_col="close", volume_col="volume",
)


def _all_bars(path: Path, **kw) -> list:
    """Read all bars from a fixture."""
    kw.setdefault("symbol", "TEST")
    kw.setdefault("timeframe", "5m")
    return [bar for chunk in read_ohlcv_chunks(path, MAPPING, **kw) for bar in chunk]


# ── read_ohlcv_chunks ─────────────────────────────────────────────────────

class TestReadOhlcvChunks:
    def test_clean_btc_5m(self):
        bars = _all_bars(FIX / "btc_5m_clean.csv", symbol="BTC", timeframe="5m")
        assert len(bars) == 50
        assert all(b.symbol == "BTC" for b in bars)
        assert all(b.timeframe == "5m" for b in bars)

    def test_clean_eth_5m(self):
        bars = _all_bars(FIX / "eth_5m_clean.csv", symbol="ETH", timeframe="5m")
        assert len(bars) == 50

    def test_clean_btc_15m(self):
        bars = _all_bars(FIX / "btc_15m_clean.csv", symbol="BTC", timeframe="15m")
        assert len(bars) == 30

    def test_chunk_size_10(self):
        chunks = list(read_ohlcv_chunks(
            FIX / "btc_5m_clean.csv", MAPPING, chunk_size=10,
            symbol="BTC", timeframe="5m",
        ))
        assert len(chunks) == 5
        assert all(len(c) == 10 for c in chunks)

    def test_chunk_size_100(self):
        chunks = list(read_ohlcv_chunks(
            FIX / "btc_5m_clean.csv", MAPPING, chunk_size=100,
            symbol="BTC", timeframe="5m",
        ))
        assert len(chunks) == 1
        assert len(chunks[0]) == 50

    def test_missing_file_raises(self):
        with pytest.raises(FileNotFoundError):
            list(read_ohlcv_chunks("/nonexistent.csv", MAPPING))

    def test_invalid_chunk_size_raises(self):
        with pytest.raises(ValueError, match="positive"):
            list(read_ohlcv_chunks(FIX / "btc_5m_clean.csv", MAPPING, chunk_size=0))

    def test_missing_column_raises(self):
        bad = OHLCVColumnMapping(
            timestamp_col="timestamp", open_col="open", high_col="high",
            low_col="low", close_col="close", volume_col="NONEXISTENT",
        )
        with pytest.raises(ValueError, match="Missing columns"):
            list(read_ohlcv_chunks(FIX / "btc_5m_clean.csv", bad))

    def test_bars_sorted_by_timestamp(self):
        bars = _all_bars(FIX / "btc_5m_clean.csv")
        timestamps = [b.timestamp for b in bars]
        assert timestamps == sorted(timestamps)

    def test_empty_csv(self, tmp_path):
        p = tmp_path / "empty.csv"
        p.write_text("timestamp,open,high,low,close,volume\n")
        bars = _all_bars(p)
        assert len(bars) == 0

    def test_skips_unparseable_rows(self, tmp_path):
        p = tmp_path / "bad.csv"
        p.write_text(
            "timestamp,open,high,low,close,volume\n"
            "abc,100,110,90,105,1.5\n"
            "1704067200,100,110,90,105,1.5\n"
        )
        bars = _all_bars(p, symbol="BTC", timeframe="5m")
        assert len(bars) == 1


# ── validate_ohlcv_chunk ──────────────────────────────────────────────────

class TestValidateOhlcvChunk:
    def _bar(self, **kw):
        defaults = dict(
            timestamp=1704067200.0, open=100, high=110, low=90,
            close=105, volume=1.5, symbol="BTC", timeframe="5m",
        )
        defaults.update(kw)
        return HistoricalBar(**defaults)

    def test_clean_chunk_no_issues(self):
        issues = validate_ohlcv_chunk([self._bar()])
        assert len(issues) == 0

    def test_zero_range_detected(self):
        bar = self._bar(open=100, high=100, low=100, close=100, volume=1)
        issues = validate_ohlcv_chunk([bar])
        assert any(i.issue_type == IssueType.ZERO_RANGE for i in issues)

    def test_multiple_bars(self):
        bars = [self._bar(timestamp=float(i)) for i in range(10)]
        issues = validate_ohlcv_chunk(bars)
        assert len(issues) == 0


# ── deduplicate_bars ──────────────────────────────────────────────────────

class TestDeduplicateBars:
    def _bar(self, ts):
        return HistoricalBar(
            timestamp=ts, open=100, high=110, low=90,
            close=105, volume=1.5, symbol="BTC", timeframe="5m",
        )

    def test_no_duplicates(self):
        bars = [self._bar(float(i)) for i in range(5)]
        result = deduplicate_bars(bars)
        assert len(result) == 5

    def test_duplicates_removed(self):
        bars = [self._bar(1.0), self._bar(1.0), self._bar(2.0)]
        result = deduplicate_bars(bars)
        assert len(result) == 2
        assert result[0].timestamp == 1.0
        assert result[1].timestamp == 2.0

    def test_keeps_first_occurrence(self):
        b1 = self._bar(1.0)
        b2 = HistoricalBar(
            timestamp=1.0, open=200, high=210, low=190,
            close=205, volume=5.0, symbol="BTC", timeframe="5m",
        )
        result = deduplicate_bars([b1, b2])
        assert len(result) == 1
        assert result[0].open == 100  # first occurrence kept

    def test_empty_list(self):
        assert deduplicate_bars([]) == []


# ── detect_gaps ───────────────────────────────────────────────────────────

class TestDetectGaps:
    def _bar(self, ts):
        return HistoricalBar(
            timestamp=ts, open=100, high=110, low=90,
            close=105, volume=1.5, symbol="BTC", timeframe="5m",
        )

    def test_no_gaps(self):
        bars = [self._bar(float(i * 300)) for i in range(5)]
        issues = detect_gaps(bars, 300.0)
        assert len(issues) == 0

    def test_gap_detected(self):
        bars = [self._bar(0.0), self._bar(300.0), self._bar(2000.0)]
        issues = detect_gaps(bars, 300.0)
        assert len(issues) == 1
        assert issues[0].issue_type == IssueType.GAP

    def test_unsorted_bars_handled(self):
        bars = [self._bar(2000.0), self._bar(0.0), self._bar(300.0)]
        issues = detect_gaps(bars, 300.0)
        assert len(issues) == 1

    def test_single_bar_no_gaps(self):
        issues = detect_gaps([self._bar(0.0)], 300.0)
        assert len(issues) == 0

    def test_empty_list(self):
        assert detect_gaps([], 300.0) == []


# ── summarize_dataset ─────────────────────────────────────────────────────

class TestSummarizeDataset:
    def test_clean_report(self):
        report = summarize_dataset(
            FIX / "btc_5m_clean.csv", MAPPING,
            symbol="BTC", timeframe="5m",
            expected_interval_seconds=300.0,
        )
        assert report.total_rows == 50
        assert report.valid_rows == 50
        assert report.duplicate_count == 0
        assert report.gap_count == 0
        assert report.is_clean is True

    def test_duplicates_detected(self):
        report = summarize_dataset(
            FIX / "btc_5m_with_duplicates.csv", MAPPING,
            symbol="BTC", timeframe="5m",
            expected_interval_seconds=300.0,
        )
        assert report.duplicate_count == 5
        assert report.is_clean is False

    def test_gaps_detected(self):
        report = summarize_dataset(
            FIX / "btc_5m_with_gaps.csv", MAPPING,
            symbol="BTC", timeframe="5m",
            expected_interval_seconds=300.0,
        )
        assert report.gap_count == 3
        assert report.is_clean is False

    def test_invalid_rows_detected(self):
        report = summarize_dataset(
            FIX / "btc_5m_invalid_ohlcv.csv", MAPPING,
            symbol="BTC", timeframe="5m",
            expected_interval_seconds=300.0,
        )
        # high<low and negative volume rows are skipped by reader
        # zero-range row is accepted but flagged
        assert report.invalid_ohlcv_count >= 1  # at least zero-range
        assert report.is_clean is False

    def test_chunk_size_affects_not_result(self):
        r1 = summarize_dataset(FIX / "btc_5m_clean.csv", MAPPING, chunk_size=10,
                               symbol="BTC", timeframe="5m")
        r2 = summarize_dataset(FIX / "btc_5m_clean.csv", MAPPING, chunk_size=100,
                               symbol="BTC", timeframe="5m")
        assert r1.total_rows == r2.total_rows
        assert r1.is_clean == r2.is_clean
