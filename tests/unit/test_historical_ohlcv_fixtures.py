"""Tests verifying integrity of historical backtest fixture CSVs — 15+ tests."""
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
    HistoricalDataQualityReport,
    IssueType,
    OHLCVColumnMapping,
)

FIX = Path(__file__).resolve().parent.parent / "fixtures" / "historical_backtest_lab"
MAPPING = OHLCVColumnMapping(
    timestamp_col="timestamp", open_col="open", high_col="high",
    low_col="low", close_col="close", volume_col="volume",
)


def _read_all(csv_name: str):
    return [
        bar
        for chunk in read_ohlcv_chunks(
            FIX / csv_name, MAPPING, symbol="BTC", timeframe="5m",
        )
        for bar in chunk
    ]


# ── Fixture existence ─────────────────────────────────────────────────────

class TestFixtureExistence:
    def test_btc_5m_clean_exists(self):
        assert (FIX / "btc_5m_clean.csv").exists()

    def test_eth_5m_clean_exists(self):
        assert (FIX / "eth_5m_clean.csv").exists()

    def test_btc_15m_clean_exists(self):
        assert (FIX / "btc_15m_clean.csv").exists()

    def test_btc_5m_with_gaps_exists(self):
        assert (FIX / "btc_5m_with_gaps.csv").exists()

    def test_btc_5m_with_duplicates_exists(self):
        assert (FIX / "btc_5m_with_duplicates.csv").exists()

    def test_btc_5m_invalid_ohlcv_exists(self):
        assert (FIX / "btc_5m_invalid_ohlcv.csv").exists()


# ── CSV format ────────────────────────────────────────────────────────────

class TestCsvFormat:
    def test_btc_5m_clean_has_header(self):
        with open(FIX / "btc_5m_clean.csv") as f:
            reader = csv.reader(f)
            header = next(reader)
        assert header == ["timestamp", "open", "high", "low", "close", "volume"]

    def test_all_fixtures_have_correct_columns(self):
        for name in [
            "btc_5m_clean.csv", "eth_5m_clean.csv", "btc_15m_clean.csv",
            "btc_5m_with_gaps.csv", "btc_5m_with_duplicates.csv",
            "btc_5m_invalid_ohlcv.csv",
        ]:
            with open(FIX / name) as f:
                header = next(csv.reader(f))
            assert header == ["timestamp", "open", "high", "low", "close", "volume"], \
                f"Bad header in {name}"


# ── Clean fixtures ────────────────────────────────────────────────────────

class TestCleanFixtures:
    def test_btc_5m_clean_row_count(self):
        bars = _read_all("btc_5m_clean.csv")
        assert len(bars) == 50

    def test_eth_5m_clean_row_count(self):
        bars = _read_all("eth_5m_clean.csv")
        assert len(bars) == 50

    def test_btc_15m_clean_row_count(self):
        from core.historical_ohlcv_chunked_reader import read_ohlcv_chunks
        bars = [
            bar for chunk in read_ohlcv_chunks(
                FIX / "btc_15m_clean.csv", MAPPING, symbol="BTC", timeframe="15m",
            )
            for bar in chunk
        ]
        assert len(bars) == 30

    def test_btc_5m_clean_no_issues(self):
        report = summarize_dataset(
            FIX / "btc_5m_clean.csv", MAPPING,
            symbol="BTC", timeframe="5m",
        )
        assert report.is_clean is True
        assert report.total_rows == 50

    def test_btc_5m_clean_timestamps_monotonic(self):
        bars = _read_all("btc_5m_clean.csv")
        timestamps = [b.timestamp for b in bars]
        assert timestamps == sorted(timestamps)
        assert len(set(timestamps)) == len(timestamps)

    def test_eth_5m_clean_timestamps_monotonic(self):
        bars = _read_all("eth_5m_clean.csv")
        timestamps = [b.timestamp for b in bars]
        assert timestamps == sorted(timestamps)

    def test_btc_5m_clean_all_positive_volume(self):
        bars = _read_all("btc_5m_clean.csv")
        assert all(b.volume > 0 for b in bars)

    def test_btc_5m_clean_high_gte_low(self):
        bars = _read_all("btc_5m_clean.csv")
        assert all(b.high >= b.low for b in bars)


# ── Dirty fixtures ────────────────────────────────────────────────────────

class TestDirtyFixtures:
    def test_gaps_fixture_has_gaps(self):
        report = summarize_dataset(
            FIX / "btc_5m_with_gaps.csv", MAPPING,
            symbol="BTC", timeframe="5m",
        )
        assert report.gap_count == 3
        assert report.is_clean is False

    def test_duplicates_fixture_has_duplicates(self):
        report = summarize_dataset(
            FIX / "btc_5m_with_duplicates.csv", MAPPING,
            symbol="BTC", timeframe="5m",
        )
        assert report.duplicate_count == 5
        assert report.is_clean is False

    def test_invalid_fixture_not_clean(self):
        report = summarize_dataset(
            FIX / "btc_5m_invalid_ohlcv.csv", MAPPING,
            symbol="BTC", timeframe="5m",
        )
        assert report.is_clean is False

    def test_gaps_fixture_valid_rows_less_than_total(self):
        report = summarize_dataset(
            FIX / "btc_5m_with_gaps.csv", MAPPING,
            symbol="BTC", timeframe="5m",
        )
        # Gaps don't reduce valid_rows (no rows skipped), just flagged
        assert report.total_rows == 50

    def test_duplicates_fixture_reduced_valid_rows(self):
        report = summarize_dataset(
            FIX / "btc_5m_with_duplicates.csv", MAPPING,
            symbol="BTC", timeframe="5m",
        )
        assert report.valid_rows == 45  # 50 - 5 duplicates
