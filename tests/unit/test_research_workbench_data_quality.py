"""Tests for research workbench data quality — T4591-T4620."""
from __future__ import annotations

import pytest

from core.research_workbench_data_quality import (
    DataQualityReport,
    check_data_quality,
    data_quality_to_dict,
)


def _make_good_bars(n=50):
    return [{"timestamp": 1700000000.0 + i * 300, "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.5, "volume": 1000.0} for i in range(n)]


def _make_bars_with_duplicates():
    bars = _make_good_bars(10)
    bars.append(dict(bars[0]))  # duplicate timestamp
    return bars


def _make_bars_with_gaps():
    bars = _make_good_bars(10)
    bars.insert(5, {"timestamp": 1700000000.0 + 2 * 300, "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.5, "volume": 1000.0})
    return bars


class TestDataQuality:
    def test_empty_fixture(self):
        report = check_data_quality([])
        assert report.row_count == 0
        assert report.coverage_status == "EMPTY"
        assert any("EMPTY" in w for w in report.warnings)

    def test_good_fixture(self):
        report = check_data_quality(_make_good_bars(50))
        assert report.row_count == 50
        assert report.coverage_status == "OK"
        assert report.missing_required_fields == 0
        assert report.duplicate_timestamps == 0
        assert report.null_ohlcv_count == 0

    def test_duplicate_timestamps(self):
        report = check_data_quality(_make_bars_with_duplicates())
        assert report.duplicate_timestamps == 1
        assert any("DUPLICATE" in w for w in report.warnings)

    def test_missing_fields(self):
        bars = [{"timestamp": 1.0, "open": 1.0}]  # missing high, low, close, volume
        report = check_data_quality(bars)
        assert report.missing_required_fields > 0
        assert report.coverage_status == "PARTIAL"

    def test_null_ohlcv(self):
        bars = [{"timestamp": 1.0, "open": 0.0, "high": 0.0, "low": 0.0, "close": 0.0, "volume": 0.0}]
        report = check_data_quality(bars)
        assert report.null_ohlcv_count > 0

    def test_timestamp_range(self):
        bars = _make_good_bars(50)
        report = check_data_quality(bars)
        assert report.min_timestamp == 1700000000.0
        assert report.max_timestamp == 1700000000.0 + 49 * 300

    def test_non_monotonic(self):
        bars = _make_good_bars(10)
        bars[5] = {"timestamp": 1700000000.0, "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.5, "volume": 1000.0}
        report = check_data_quality(bars)
        assert report.non_monotonic_timestamps > 0


class TestDataQualitySerialization:
    def test_to_dict(self):
        report = check_data_quality(_make_good_bars(20))
        d = data_quality_to_dict(report)
        assert d["row_count"] == 20
        assert d["coverage_status"] == "OK"
        assert isinstance(d["warnings"], list)
