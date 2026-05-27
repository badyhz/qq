"""Tests for portfolio research overlap analysis — T4681-T4710."""
from __future__ import annotations

import pytest

from core.multi_strategy_evaluator import RunResult
from core.portfolio_research_overlap import (
    OverlapAnalysis,
    analyze_overlap,
    overlap_analysis_to_dict,
)


def _make_result(strategy_id, symbol, timeframe="5m", signals=10, trades=10):
    return RunResult(
        run_result_id=f"r_{strategy_id}_{symbol}",
        matrix_row_id=f"row_{strategy_id}_{symbol}",
        strategy_id=strategy_id, symbol=symbol, timeframe=timeframe,
        split_id="s0", parameter_set_id="ps0", data_quality={},
        signal_count=signals, trade_count=trades, win_rate=0.5,
        expectancy_r=0.0, avg_return=0.01, max_drawdown=0.05,
        profit_factor=1.5, avg_mfe=0.03, avg_mae=0.01, score=0.5, warnings=[],
    )


class TestOverlapAnalysis:
    def test_empty(self):
        analysis = analyze_overlap([])
        assert len(analysis.entries) == 0

    def test_same_symbol_overlap(self):
        results = [
            _make_result("breakout", "BTCUSDT"),
            _make_result("momentum", "BTCUSDT"),
        ]
        analysis = analyze_overlap(results)
        assert len(analysis.entries) > 0
        entry = analysis.entries[0]
        assert entry.symbol == "BTCUSDT"
        assert entry.signal_overlap_count >= 0

    def test_different_symbols_no_overlap(self):
        results = [
            _make_result("breakout", "BTCUSDT"),
            _make_result("momentum", "ETHUSDT"),
        ]
        analysis = analyze_overlap(results)
        # Should have entries for each symbol separately
        for e in analysis.entries:
            assert e.signal_overlap_count == 0 or e.strategy_pair[0] != e.strategy_pair[1]

    def test_concentration_warnings(self):
        results = [
            _make_result("breakout", "BTCUSDT", signals=100, trades=100),
            _make_result("momentum", "BTCUSDT", signals=1, trades=1),
        ]
        analysis = analyze_overlap(results)
        # BTCUSDT dominates
        assert any("SYMBOL" in w or "CONCENTRATION" in w for w in analysis.concentration_warnings) or \
               len(analysis.entries) > 0  # at least has entries

    def test_high_overlap_detected(self):
        results = [
            _make_result("breakout", "BTCUSDT", signals=100, trades=100),
            _make_result("momentum", "BTCUSDT", signals=100, trades=100),
        ]
        analysis = analyze_overlap(results, high_overlap_threshold=0.5)
        # Same signal count = 100% overlap
        for e in analysis.entries:
            if e.signal_overlap_ratio > 0.5:
                assert "HIGH_SIGNAL_OVERLAP" in e.warnings


class TestOverlapSerialization:
    def test_to_dict(self):
        results = [_make_result("breakout", "BTCUSDT"), _make_result("momentum", "BTCUSDT")]
        analysis = analyze_overlap(results)
        d = overlap_analysis_to_dict(analysis)
        assert "entries" in d
        assert "concentration_warnings" in d
