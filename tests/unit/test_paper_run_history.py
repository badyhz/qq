"""Tests for run history module."""
from __future__ import annotations

import json
import os
import tempfile

import pytest

from core.paper_trading.run_history import (
    RunRecord, TrendDelta,
    record_from_result, append_record, read_history,
    filter_by_date, compare_last_two, compute_trend,
)


def _record(**kwargs):
    defaults = dict(
        timestamp="2026-06-16T12:00:00Z",
        strategy_name="macd_rebound", status="OK",
        fixtures_run=4, fixtures_failed=0,
        total_signals=10, total_plans=8, total_rejected=2,
        total_trades=6, total_pnl=500.0, win_rate=0.7,
        score=62.0, rating="B", alerts_written=1,
    )
    defaults.update(kwargs)
    return RunRecord(**defaults)


class TestRecordFromResult:
    def test_conversion(self):
        class FakeResult:
            strategy_name = "macd_rebound"
            status = "OK"
            fixtures_run = 3
            fixtures_failed = 0
            total_signals = 8
            total_plans = 6
            total_rejected = 2
            total_trades = 5
            total_pnl = 350.5
            win_rate = 0.6
            score = 58.0
            rating = "B"
            alerts_written = 0

        rec = record_from_result(FakeResult())
        assert rec.strategy_name == "macd_rebound"
        assert rec.total_pnl == 350.5
        assert rec.timestamp.endswith("Z")


class TestAppendAndRead:
    def test_append_and_read(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            path = f.name
        try:
            r1 = _record(total_pnl=100)
            r2 = _record(total_pnl=200, timestamp="2026-06-16T13:00:00Z")
            append_record(r1, path)
            append_record(r2, path)
            records = read_history(path)
            assert len(records) == 2
            assert records[0].total_pnl == 100
            assert records[1].total_pnl == 200
        finally:
            os.unlink(path)

    def test_read_empty(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            path = f.name
        try:
            records = read_history(path)
            assert records == []
        finally:
            os.unlink(path)

    def test_read_nonexistent(self):
        records = read_history("/tmp/nonexistent_paper_history.jsonl")
        assert records == []

    def test_read_with_limit(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            path = f.name
        try:
            for i in range(5):
                append_record(_record(total_pnl=float(i * 100)), path)
            records = read_history(path, limit=3)
            assert len(records) == 3
            assert records[0].total_pnl == 200.0
        finally:
            os.unlink(path)

    def test_skips_blank_lines(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False, mode="w") as f:
            f.write(json.dumps({"timestamp": "2026-06-16T12:00:00Z", "strategy_name": "macd_rebound", "status": "OK", "fixtures_run": 1, "fixtures_failed": 0, "total_signals": 1, "total_plans": 1, "total_rejected": 0, "total_trades": 1, "total_pnl": 100, "win_rate": 1.0, "score": 80, "rating": "A", "alerts_written": 0}) + "\n")
            f.write("\n")
            f.write("not json\n")
            path = f.name
        try:
            records = read_history(path)
            assert len(records) == 1
        finally:
            os.unlink(path)


class TestFilterByDate:
    def test_filter(self):
        records = [
            _record(timestamp="2026-06-15T10:00:00Z"),
            _record(timestamp="2026-06-16T10:00:00Z"),
            _record(timestamp="2026-06-16T14:00:00Z"),
        ]
        filtered = filter_by_date(records, "2026-06-16")
        assert len(filtered) == 2

    def test_filter_none(self):
        records = [_record(timestamp="2026-06-15T10:00:00Z")]
        filtered = filter_by_date(records, "2026-06-20")
        assert len(filtered) == 0


class TestCompareLastTwo:
    def test_improving(self):
        records = [
            _record(score=50, total_pnl=100, win_rate=0.5, total_trades=4),
            _record(score=60, total_pnl=200, win_rate=0.6, total_trades=5),
        ]
        delta = compare_last_two(records)
        assert delta is not None
        assert delta.score == 10
        assert delta.pnl == 100
        assert delta.improved is True

    def test_declining(self):
        records = [
            _record(score=60, total_pnl=200, win_rate=0.6, total_trades=5),
            _record(score=50, total_pnl=100, win_rate=0.5, total_trades=4),
        ]
        delta = compare_last_two(records)
        assert delta is not None
        assert delta.score == -10
        assert delta.improved is False

    def test_too_few(self):
        records = [_record()]
        assert compare_last_two(records) is None


class TestComputeTrend:
    def test_empty(self):
        t = compute_trend([])
        assert t["count"] == 0

    def test_rising(self):
        records = [_record(score=40 + i * 5, total_pnl=i * 100) for i in range(5)]
        t = compute_trend(records, window=5)
        assert t["count"] == 5
        assert t["score_trend"] == "rising"

    def test_falling(self):
        records = [_record(score=80 - i * 10, total_pnl=1000 - i * 200) for i in range(5)]
        t = compute_trend(records, window=5)
        assert t["score_trend"] == "falling"

    def test_flat(self):
        records = [_record(score=60, total_pnl=500) for _ in range(5)]
        t = compute_trend(records, window=5)
        assert t["score_trend"] == "flat"
        assert t["pnl_trend"] == "flat"

    def test_window_larger_than_data(self):
        records = [_record(score=60)]
        t = compute_trend(records, window=10)
        assert t["count"] == 1
        assert t["score_trend"] == "flat"
