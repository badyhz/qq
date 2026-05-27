"""Negative tests for historical OHLCV backtest lab (Phase 20).

Covers error paths: missing files, malformed CSV, invalid data,
path traversal, frozen file protection, edge cases.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from core.historical_ohlcv_chunked_reader import (
    OHLCVColumnMapping,
    detect_gaps,
    read_ohlcv_chunks,
    summarize_dataset,
)
from core.historical_ohlcv_schema import HistoricalBar, HistoricalDataQualityReport
from core.offline_backtest_bundle_builder import build_backtest_bundle, compute_sha256
from scripts.run_historical_ohlcv_backtest_lab import (
    _step_data_quality,
    _step_matrix_evaluation,
    main,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

_COL_MAP = OHLCVColumnMapping(
    timestamp_col="timestamp",
    open_col="open",
    high_col="high",
    low_col="low",
    close_col="close",
    volume_col="volume",
)


def _write_csv(path: Path, rows: list[list[str]]) -> None:
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        for row in rows:
            writer.writerow(row)


def _good_rows(n: int = 20) -> list[list[str]]:
    header = ["timestamp", "open", "high", "low", "close", "volume"]
    rows = [header]
    base_ts = 1000000
    for i in range(n):
        ts = base_ts + i * 300
        o = 100.0 + i * 0.1
        h = o + 0.5
        l = o - 0.3
        c = o + 0.2
        v = 1000.0 + i
        rows.append([str(ts), f"{o:.2f}", f"{h:.2f}", f"{l:.2f}", f"{c:.2f}", f"{v:.2f}"])
    return rows


# ---------------------------------------------------------------------------
# Missing CSV file
# ---------------------------------------------------------------------------

class TestMissingCSV:
    def test_read_ohlcv_chunks_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            list(read_ohlcv_chunks(tmp_path / "no_such.csv", _COL_MAP, 100))

    def test_summarize_missing_csv_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            summarize_dataset(tmp_path / "no_such.csv", _COL_MAP, 100, "X", "5m")

    def test_pipeline_missing_csv_status(self, tmp_path):
        fixture_dir = tmp_path / "fix"
        fixture_dir.mkdir()
        report, clean = _step_data_quality(fixture_dir, ["MISSING"], ["5m"], 100)
        assert clean is False
        assert report["quality_reports"][0]["status"] == "missing"


# ---------------------------------------------------------------------------
# Malformed CSV (wrong columns)
# ---------------------------------------------------------------------------

class TestMalformedCSV:
    def test_wrong_column_names_raises(self, tmp_path):
        csv_path = tmp_path / "bad.csv"
        _write_csv(csv_path, [["ts", "o", "h", "l", "c", "vol"],
                               ["1000", "100", "101", "99", "100.5", "1000"]])
        with pytest.raises(ValueError, match="Missing columns"):
            list(read_ohlcv_chunks(csv_path, _COL_MAP, 100, "X", "5m"))

    def test_header_only_csv(self, tmp_path):
        csv_path = tmp_path / "header_only.csv"
        _write_csv(csv_path, [["timestamp", "open", "high", "low", "close", "volume"]])
        chunks = list(read_ohlcv_chunks(csv_path, _COL_MAP, 100, "X", "5m"))
        assert chunks == []

    def test_empty_csv_file(self, tmp_path):
        csv_path = tmp_path / "empty.csv"
        csv_path.write_text("")
        chunks = list(read_ohlcv_chunks(csv_path, _COL_MAP, 100, "X", "5m"))
        assert chunks == []

    def test_non_numeric_values_skipped(self, tmp_path):
        csv_path = tmp_path / "bad_vals.csv"
        _write_csv(csv_path, [
            ["timestamp", "open", "high", "low", "close", "volume"],
            ["1000", "not_a_number", "101", "99", "100.5", "1000"],
            ["1300", "100", "101", "99", "100.5", "1000"],
        ])
        chunks = list(read_ohlcv_chunks(csv_path, _COL_MAP, 100, "X", "5m"))
        all_bars = [b for chunk in chunks for b in chunk]
        assert len(all_bars) == 1  # only valid row kept


# ---------------------------------------------------------------------------
# Duplicate timestamps
# ---------------------------------------------------------------------------

class TestDuplicateTimestamps:
    def test_duplicate_detected_in_quality_report(self, tmp_path):
        csv_path = tmp_path / "dup.csv"
        rows = [["timestamp", "open", "high", "low", "close", "volume"]]
        for _ in range(5):
            rows.append(["1000000", "100", "101", "99", "100.5", "1000"])
        _write_csv(csv_path, rows)
        report = summarize_dataset(csv_path, _COL_MAP, 500, "X", "5m", 300)
        assert report.duplicate_count == 4
        assert report.is_clean is False

    def test_deduplication_in_reader(self, tmp_path):
        from core.historical_ohlcv_chunked_reader import deduplicate_bars
        bars = [
            HistoricalBar(timestamp=1000, open=1, high=2, low=0, close=1.5, volume=10, symbol="X", timeframe="5m"),
            HistoricalBar(timestamp=1000, open=1, high=2, low=0, close=1.5, volume=10, symbol="X", timeframe="5m"),
            HistoricalBar(timestamp=1300, open=1, high=2, low=0, close=1.5, volume=10, symbol="X", timeframe="5m"),
        ]
        deduped = deduplicate_bars(bars)
        assert len(deduped) == 2


# ---------------------------------------------------------------------------
# Gap detection
# ---------------------------------------------------------------------------

class TestGapDetection:
    def test_large_gap_detected(self):
        bars = [
            HistoricalBar(timestamp=1000, open=1, high=2, low=0, close=1.5, volume=10, symbol="X", timeframe="5m"),
            HistoricalBar(timestamp=5000, open=1, high=2, low=0, close=1.5, volume=10, symbol="X", timeframe="5m"),
        ]
        issues = detect_gaps(bars, expected_interval_seconds=300)
        assert len(issues) == 1

    def test_no_gap_within_threshold(self):
        bars = [
            HistoricalBar(timestamp=1000, open=1, high=2, low=0, close=1.5, volume=10, symbol="X", timeframe="5m"),
            HistoricalBar(timestamp=1200, open=1, high=2, low=0, close=1.5, volume=10, symbol="X", timeframe="5m"),
        ]
        issues = detect_gaps(bars, expected_interval_seconds=300)
        assert len(issues) == 0

    def test_single_bar_no_gap(self):
        bars = [
            HistoricalBar(timestamp=1000, open=1, high=2, low=0, close=1.5, volume=10, symbol="X", timeframe="5m"),
        ]
        issues = detect_gaps(bars, expected_interval_seconds=300)
        assert issues == []


# ---------------------------------------------------------------------------
# Invalid OHLCV values
# ---------------------------------------------------------------------------

class TestInvalidOHLCV:
    def test_high_less_than_low_raises(self):
        with pytest.raises(ValueError, match="high.*must be >= low"):
            HistoricalBar(timestamp=1000, open=100, high=90, low=100, close=95, volume=10, symbol="X", timeframe="5m")

    def test_negative_volume_raises(self):
        with pytest.raises(ValueError, match="non-negative"):
            HistoricalBar(timestamp=1000, open=100, high=101, low=99, close=100.5, volume=-5, symbol="X", timeframe="5m")

    def test_empty_symbol_raises(self):
        with pytest.raises(ValueError, match="symbol must be non-empty"):
            HistoricalBar(timestamp=1000, open=100, high=101, low=99, close=100.5, volume=10, symbol="", timeframe="5m")

    def test_empty_timeframe_raises(self):
        with pytest.raises(ValueError, match="timeframe must be non-empty"):
            HistoricalBar(timestamp=1000, open=100, high=101, low=99, close=100.5, volume=10, symbol="X", timeframe="")


# ---------------------------------------------------------------------------
# Insufficient data
# ---------------------------------------------------------------------------

class TestInsufficientData:
    def test_empty_fixture_dir(self, tmp_path):
        fixture_dir = tmp_path / "empty_fixtures"
        fixture_dir.mkdir()
        matrix = {"matrix_id": "m", "cells": [{"cell_id": "c0", "symbol": "X", "timeframe": "5m", "param_label": "conservative", "split_mode": "wf"}]}
        results = _step_matrix_evaluation(matrix, fixture_dir, 100)
        assert results[0]["status"] == "missing_data"

    def test_header_only_csv_no_bars(self, tmp_path):
        fixture_dir = tmp_path / "fix"
        fixture_dir.mkdir()
        csv_path = fixture_dir / "X_5m.csv"
        _write_csv(csv_path, [["timestamp", "open", "high", "low", "close", "volume"]])
        matrix = {"matrix_id": "m", "cells": [{"cell_id": "c0", "symbol": "X", "timeframe": "5m", "param_label": "conservative", "split_mode": "wf"}]}
        results = _step_matrix_evaluation(matrix, fixture_dir, 100)
        assert results[0]["status"] == "no_bars"


# ---------------------------------------------------------------------------
# Unsafe output path
# ---------------------------------------------------------------------------

class TestUnsafeOutputPath:
    def test_output_path_points_to_frozen_file(self, tmp_path):
        """Bundle builder should not write to frozen files."""
        f = tmp_path / "test.json"
        f.write_text("{}")
        result = build_backtest_bundle(tmp_path, {"test.json": str(f)})
        assert result["release_hold"] == "HOLD"

    def test_path_traversal_in_artifact_name(self, tmp_path):
        """Artifacts with traversal in name are just keys — no file write by builder."""
        f = tmp_path / "test.json"
        f.write_text("{}")
        result = build_backtest_bundle(tmp_path, {"../../../etc/passwd": str(f)})
        assert result["release_hold"] == "HOLD"


# ---------------------------------------------------------------------------
# Invalid param grid preset
# ---------------------------------------------------------------------------

class TestInvalidParamGrid:
    def test_invalid_preset_returns_1(self, tmp_path):
        fixture_dir = tmp_path / "fix"
        fixture_dir.mkdir()
        csv_path = fixture_dir / "BTCUSDT_5m.csv"
        _write_csv(csv_path, _good_rows(20))
        rc = main([
            "--fixture-dir", str(fixture_dir),
            "--output-dir", str(tmp_path / "out"),
            "--symbols", "BTCUSDT",
            "--timeframes", "5m",
            "--param-grid", "nonexistent_preset",
        ])
        assert rc == 1

    def test_empty_param_grid_returns_1(self, tmp_path):
        fixture_dir = tmp_path / "fix"
        fixture_dir.mkdir()
        csv_path = fixture_dir / "BTCUSDT_5m.csv"
        _write_csv(csv_path, _good_rows(20))
        rc = main([
            "--fixture-dir", str(fixture_dir),
            "--output-dir", str(tmp_path / "out"),
            "--symbols", "BTCUSDT",
            "--timeframes", "5m",
            "--param-grid", "",
        ])
        assert rc == 1


# ---------------------------------------------------------------------------
# Empty fixture directory
# ---------------------------------------------------------------------------

class TestEmptyFixtureDir:
    def test_pipeline_empty_dir(self, tmp_path):
        fixture_dir = tmp_path / "empty"
        fixture_dir.mkdir()
        rc = main([
            "--fixture-dir", str(fixture_dir),
            "--output-dir", str(tmp_path / "out"),
            "--symbols", "BTCUSDT",
            "--timeframes", "5m",
            "--param-grid", "conservative",
        ])
        # Should succeed (no CSVs -> missing_data status, but pipeline completes)
        assert rc == 0


# ---------------------------------------------------------------------------
# chunk_size edge cases
# ---------------------------------------------------------------------------

class TestChunkSizeEdgeCases:
    def test_chunk_size_one(self, tmp_path):
        csv_path = tmp_path / "small.csv"
        _write_csv(csv_path, _good_rows(5))
        chunks = list(read_ohlcv_chunks(csv_path, _COL_MAP, 1, "X", "5m"))
        assert len(chunks) == 5

    def test_chunk_size_zero_raises(self, tmp_path):
        csv_path = tmp_path / "small.csv"
        _write_csv(csv_path, _good_rows(5))
        with pytest.raises(ValueError, match="chunk_size must be positive"):
            list(read_ohlcv_chunks(csv_path, _COL_MAP, 0, "X", "5m"))

    def test_chunk_size_negative_raises(self, tmp_path):
        csv_path = tmp_path / "small.csv"
        _write_csv(csv_path, _good_rows(5))
        with pytest.raises(ValueError, match="chunk_size must be positive"):
            list(read_ohlcv_chunks(csv_path, _COL_MAP, -1, "X", "5m"))
