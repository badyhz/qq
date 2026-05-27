"""Tests for portfolio research aggregation — T4651-T4680."""
from __future__ import annotations

import json

import pytest

from core.multi_strategy_evaluator import RunResult
from core.portfolio_research_aggregation import (
    PortfolioAggregateResult,
    aggregate_portfolio,
    portfolio_to_dict,
    portfolio_to_json,
)


def _make_result(strategy_id="breakout", symbol="BTCUSDT", score=0.5, trades=10):
    return RunResult(
        run_result_id=f"r_{strategy_id}_{symbol}",
        matrix_row_id=f"row_{strategy_id}_{symbol}",
        strategy_id=strategy_id,
        symbol=symbol,
        timeframe="5m",
        split_id="s0",
        parameter_set_id="ps0",
        data_quality={},
        signal_count=trades,
        trade_count=trades,
        win_rate=score,
        expectancy_r=score * 2 - 1,
        avg_return=score * 0.02,
        max_drawdown=0.05,
        profit_factor=1.0 + score,
        avg_mfe=0.03,
        avg_mae=0.01,
        score=score,
        warnings=[],
    )


class TestPortfolioAggregation:
    def test_empty_results(self):
        result = aggregate_portfolio([])
        assert result.total_trades == 0
        assert len(result.included_strategy_ids) == 0

    def test_single_result(self):
        r = _make_result()
        result = aggregate_portfolio([r])
        assert result.total_trades == 10
        assert "breakout" in result.included_strategy_ids
        assert "BTCUSDT" in result.included_symbols

    def test_multi_strategy_aggregation(self):
        results = [_make_result("breakout"), _make_result("momentum")]
        result = aggregate_portfolio(results)
        assert len(result.included_strategy_ids) == 2
        assert result.total_trades == 20

    def test_equity_curve(self):
        results = [_make_result()]
        result = aggregate_portfolio(results)
        assert len(result.equity_curve_approx) > 0
        assert result.equity_curve_approx[0] == 1.0

    def test_exposure_summary(self):
        results = [_make_result("breakout", "BTCUSDT"), _make_result("momentum", "ETHUSDT")]
        result = aggregate_portfolio(results)
        assert "by_symbol" in result.exposure_summary

    def test_drawdown_summary(self):
        results = [_make_result("breakout"), _make_result("momentum")]
        result = aggregate_portfolio(results)
        assert "by_strategy" in result.drawdown_summary

    def test_low_trades_warning(self):
        r = _make_result(trades=1)
        result = aggregate_portfolio([r])
        assert any("LOW" in w for w in result.warnings)


class TestPortfolioSerialization:
    def test_to_dict(self):
        r = _make_result()
        result = aggregate_portfolio([r])
        d = portfolio_to_dict(result)
        assert d["portfolio_id"] == "portfolio_research_001"
        assert isinstance(d["included_strategy_ids"], list)

    def test_deterministic_json(self):
        r = _make_result()
        result = aggregate_portfolio([r])
        j1 = portfolio_to_json(result)
        j2 = portfolio_to_json(result)
        assert j1 == j2
