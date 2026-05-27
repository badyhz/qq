"""Tests for multi-strategy evaluator — T4621-T4650."""
from __future__ import annotations

import json

import pytest

from core.multi_strategy_evaluator import (
    EvaluationResult,
    RunResult,
    _compute_simple_metrics,
    evaluate_matrix_row,
    evaluation_to_dict,
    run_result_to_dict,
)
from core.multi_strategy_matrix import MatrixRow
from core.strategy_research_interface import StrategySignal


def _make_row():
    return MatrixRow(
        matrix_row_id="row_test_001",
        strategy_id="breakout",
        strategy_family="breakout",
        symbol="BTCUSDT",
        timeframe="5m",
        split_id="split_0_TRAIN",
        parameter_set_id="ps_001",
        fixture_path="/tmp/test.csv",
        dataset_id="BTCUSDT_5m_fixture",
    )


def _make_bars(n=50):
    return [{"timestamp": 1700000000.0 + i * 300, "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.5, "volume": 1000.0} for i in range(n)]


class TestEvaluator:
    def test_evaluate_empty_bars(self):
        row = _make_row()
        result = evaluate_matrix_row(row, [])
        assert result.signal_count == 0
        assert result.release_hold == "HOLD"
        assert result.data_quality["coverage_status"] == "EMPTY"

    def test_evaluate_with_bars(self):
        row = _make_row()
        result = evaluate_matrix_row(row, _make_bars(50))
        assert result.signal_count == 0  # no generator
        assert result.data_quality["coverage_status"] == "OK"

    def test_run_result_fields(self):
        row = _make_row()
        result = evaluate_matrix_row(row, _make_bars(50))
        assert result.run_result_id == "result_row_test_001"
        assert result.strategy_id == "breakout"
        assert result.symbol == "BTCUSDT"
        assert result.release_hold == "HOLD"

    def test_run_result_to_dict(self):
        row = _make_row()
        result = evaluate_matrix_row(row, _make_bars(50))
        d = run_result_to_dict(result)
        assert d["run_result_id"] == "result_row_test_001"
        assert d["release_hold"] == "HOLD"


class TestSimpleMetrics:
    def test_empty_signals(self):
        m = _compute_simple_metrics([])
        assert m["signal_count"] == 0
        assert m["trade_count"] == 0

    def test_with_signals(self):
        signals = [
            StrategySignal(signal_id="s1", strategy_id="test", symbol="BTC", timeframe="5m",
                           timestamp=1.0, side="LONG", entry_reference_price=100.0, confidence=0.8),
            StrategySignal(signal_id="s2", strategy_id="test", symbol="BTC", timeframe="5m",
                           timestamp=2.0, side="LONG", entry_reference_price=101.0, confidence=0.6),
        ]
        m = _compute_simple_metrics(signals)
        assert m["signal_count"] == 2
        assert m["win_rate"] > 0
        assert m["score"] > 0


class TestEvaluationResult:
    def test_serialization(self):
        row = _make_row()
        result = evaluate_matrix_row(row, _make_bars(50))
        eval_result = EvaluationResult(
            results=(result,),
            total_rows=1,
            evaluated_rows=1,
            skipped_rows=0,
            warnings=[],
        )
        d = evaluation_to_dict(eval_result)
        assert d["total_rows"] == 1
        assert d["evaluated_rows"] == 1
        assert len(d["results"]) == 1
