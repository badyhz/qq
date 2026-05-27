"""Performance guard tests for chunked OHLCV reader (Phase 21).

Verifies chunked reader handles large files without loading all rows at once,
and that repeated reads don't accumulate memory.
"""
from __future__ import annotations

import csv
import gc
import sys
from pathlib import Path

import pytest

from core.historical_ohlcv_chunked_reader import (
    OHLCVColumnMapping,
    read_ohlcv_chunks,
    summarize_dataset,
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


def _generate_large_csv(path: Path, n_rows: int) -> None:
    """Write a CSV with n_rows data rows."""
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "open", "high", "low", "close", "volume"])
        base_ts = 1000000
        for i in range(n_rows):
            ts = base_ts + i * 300
            o = 100.0 + i * 0.01
            h = o + 0.5
            l = o - 0.3
            c = o + 0.2
            v = 1000.0 + i
            writer.writerow([str(ts), f"{o:.2f}", f"{h:.2f}", f"{l:.2f}", f"{c:.2f}", f"{v:.2f}"])


# ---------------------------------------------------------------------------
# tests
# ---------------------------------------------------------------------------

class TestChunkedReaderPerformance:
    def test_5000_rows_processed(self, tmp_path):
        """Chunked reader processes 5000-row CSV without error."""
        csv_path = tmp_path / "large.csv"
        _generate_large_csv(csv_path, 5000)
        total_bars = 0
        for chunk in read_ohlcv_chunks(csv_path, _COL_MAP, 500, "BTCUSDT", "5m"):
            total_bars += len(chunk)
        assert total_bars == 5000

    def test_chunk_size_10(self, tmp_path):
        """Chunk size 10 works correctly."""
        csv_path = tmp_path / "large.csv"
        _generate_large_csv(csv_path, 100)
        chunks = list(read_ohlcv_chunks(csv_path, _COL_MAP, 10, "BTCUSDT", "5m"))
        assert len(chunks) == 10
        total = sum(len(c) for c in chunks)
        assert total == 100

    def test_chunk_size_50(self, tmp_path):
        """Chunk size 50 works correctly."""
        csv_path = tmp_path / "large.csv"
        _generate_large_csv(csv_path, 200)
        chunks = list(read_ohlcv_chunks(csv_path, _COL_MAP, 50, "BTCUSDT", "5m"))
        assert len(chunks) == 4
        total = sum(len(c) for c in chunks)
        assert total == 200

    def test_chunk_size_100(self, tmp_path):
        """Chunk size 100 works correctly."""
        csv_path = tmp_path / "large.csv"
        _generate_large_csv(csv_path, 350)
        chunks = list(read_ohlcv_chunks(csv_path, _COL_MAP, 100, "BTCUSDT", "5m"))
        # 4 chunks: 100, 100, 100, 50
        assert len(chunks) == 4
        assert len(chunks[-1]) == 50

    def test_chunk_size_500(self, tmp_path):
        """Chunk size 500 works correctly."""
        csv_path = tmp_path / "large.csv"
        _generate_large_csv(csv_path, 1200)
        chunks = list(read_ohlcv_chunks(csv_path, _COL_MAP, 500, "BTCUSDT", "5m"))
        assert len(chunks) == 3
        assert len(chunks[0]) == 500
        assert len(chunks[1]) == 500
        assert len(chunks[2]) == 200

    def test_repeated_reads_no_accumulation(self, tmp_path):
        """Multiple reads of the same file don't accumulate memory."""
        csv_path = tmp_path / "repeat.csv"
        _generate_large_csv(csv_path, 500)

        gc.collect()
        baseline_objects = len(gc.get_objects())

        for _ in range(5):
            total = 0
            for chunk in read_ohlcv_chunks(csv_path, _COL_MAP, 100, "BTCUSDT", "5m"):
                total += len(chunk)
            assert total == 500

        gc.collect()
        final_objects = len(gc.get_objects())
        # Allow some growth but not unbounded (5x the baseline would be pathological)
        growth = final_objects - baseline_objects
        assert growth < baseline_objects * 0.5, f"Object growth too large: {growth}"

    def test_summarize_large_dataset(self, tmp_path):
        """summarize_dataset handles 5000 rows efficiently."""
        csv_path = tmp_path / "large.csv"
        _generate_large_csv(csv_path, 5000)
        report = summarize_dataset(csv_path, _COL_MAP, 500, "BTCUSDT", "5m", 300)
        assert report.total_rows == 5000
        assert report.valid_rows == 5000
        assert report.is_clean is True

    def test_chunk_boundary_correctness(self, tmp_path):
        """Data across chunk boundaries is complete and correct."""
        csv_path = tmp_path / "boundary.csv"
        n = 25
        _generate_large_csv(csv_path, n)

        all_bars = []
        for chunk in read_ohlcv_chunks(csv_path, _COL_MAP, 10, "BTCUSDT", "5m"):
            all_bars.extend(chunk)

        assert len(all_bars) == n
        # Check timestamps are sequential
        for i in range(1, len(all_bars)):
            assert all_bars[i].timestamp > all_bars[i - 1].timestamp
