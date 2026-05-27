"""Tests for core/offline_backtest_metrics_engine.py — 25+ tests."""
from __future__ import annotations

import math

import pytest

from core.offline_backtest_metrics_engine import (
    compute_aggregate_metrics,
    compute_max_drawdown_r,
    compute_profit_factor,
    compute_run_metrics,
)


def _make_trade(
    trade_id: str = "T1",
    realized_r: float = 1.0,
    mfe_r: float = 1.5,
    mae_r: float = -0.3,
    hold_bars: int = 10,
    gross_pnl: float = 100.0,
    fees: float = 1.0,
    slippage_cost: float = 0.5,
    net_pnl: float = 98.5,
    entry_price: float = 100.0,
    exit_price: float = 101.0,
    exit_reason: str = "TP",
    entry_bar_index: int = 0,
    exit_bar_index: int = 10,
    signal_id: str = "S1",
) -> dict:
    return {
        "trade_id": trade_id,
        "signal_id": signal_id,
        "entry_bar_index": entry_bar_index,
        "exit_bar_index": exit_bar_index,
        "entry_price": entry_price,
        "exit_price": exit_price,
        "exit_reason": exit_reason,
        "realized_r": realized_r,
        "gross_pnl": gross_pnl,
        "fees": fees,
        "slippage_cost": slippage_cost,
        "net_pnl": net_pnl,
        "mfe_r": mfe_r,
        "mae_r": mae_r,
        "hold_bars": hold_bars,
    }


class TestMaxDrawdownR:
    def test_empty_curve(self):
        assert compute_max_drawdown_r([]) == 0.0

    def test_single_point(self):
        assert compute_max_drawdown_r([1.0]) == 0.0

    def test_no_drawdown(self):
        assert compute_max_drawdown_r([1.0, 2.0, 3.0]) == 0.0

    def test_simple_drawdown(self):
        result = compute_max_drawdown_r([10.0, 5.0])
        assert result == pytest.approx(-5.0)

    def test_drawdown_with_recovery(self):
        # peak=10, trough=5 => dd=-5; peak=12, trough=8 => dd=-4; worst = -5
        result = compute_max_drawdown_r([10.0, 5.0, 12.0, 8.0])
        assert result == pytest.approx(-5.0)

    def test_monotonic_decline(self):
        result = compute_max_drawdown_r([10.0, 8.0, 5.0, 1.0])
        assert result == pytest.approx(-9.0)


class TestProfitFactor:
    def test_no_trades(self):
        assert compute_profit_factor(0.0, 0.0) == 0.0

    def test_only_wins(self):
        result = compute_profit_factor(100.0, 0.0)
        assert result == float("inf")

    def test_only_losses(self):
        assert compute_profit_factor(0.0, -50.0) == 0.0

    def test_equal_wins_losses(self):
        assert compute_profit_factor(50.0, -50.0) == pytest.approx(1.0)

    def test_two_to_one(self):
        assert compute_profit_factor(200.0, -100.0) == pytest.approx(2.0)


class TestComputeRunMetrics:
    def test_empty_trades(self):
        m = compute_run_metrics([])
        assert m["trade_count"] == 0
        assert m["win_rate"] == 0.0
        assert m["expectancy_r"] == 0.0
        assert m["quality_adjusted_score"] == 0.0

    def test_single_winning_trade(self):
        t = _make_trade(realized_r=2.0)
        m = compute_run_metrics([t])
        assert m["trade_count"] == 1
        assert m["win_rate"] == 1.0
        assert m["expectancy_r"] == pytest.approx(2.0)
        assert m["median_r"] == pytest.approx(2.0)

    def test_single_losing_trade(self):
        t = _make_trade(realized_r=-1.0)
        m = compute_run_metrics([t])
        assert m["trade_count"] == 1
        assert m["win_rate"] == 0.0
        assert m["expectancy_r"] == pytest.approx(-1.0)

    def test_mixed_trades(self):
        trades = [
            _make_trade(f"T{i}", realized_r=r)
            for i, r in enumerate([1.0, -0.5, 2.0, -1.0, 1.5])
        ]
        m = compute_run_metrics(trades)
        assert m["trade_count"] == 5
        assert m["win_rate"] == pytest.approx(3 / 5)
        assert m["expectancy_r"] == pytest.approx(0.6)
        assert m["median_r"] == pytest.approx(1.0)

    def test_all_wins(self):
        trades = [_make_trade(f"T{i}", realized_r=float(i + 1)) for i in range(5)]
        m = compute_run_metrics(trades)
        assert m["win_rate"] == 1.0
        assert m["profit_factor"] == float("inf")

    def test_all_losses(self):
        trades = [_make_trade(f"T{i}", realized_r=-(i + 1) * 0.5) for i in range(4)]
        m = compute_run_metrics(trades)
        assert m["win_rate"] == 0.0
        assert m["profit_factor"] == 0.0

    def test_exposure_bars(self):
        trades = [
            _make_trade("T1", hold_bars=5),
            _make_trade("T2", hold_bars=10),
        ]
        m = compute_run_metrics(trades)
        assert m["exposure_bars"] == 15
        assert m["avg_hold_bars"] == pytest.approx(7.5)

    def test_avg_mfe_mae(self):
        trades = [
            _make_trade("T1", mfe_r=2.0, mae_r=-0.5),
            _make_trade("T2", mfe_r=1.0, mae_r=-1.0),
        ]
        m = compute_run_metrics(trades)
        assert m["avg_mfe_r"] == pytest.approx(1.5)
        assert m["avg_mae_r"] == pytest.approx(-0.75)

    def test_sample_adequacy_scaling(self):
        # 15 trades -> 0.5
        trades = [_make_trade(f"T{i}") for i in range(15)]
        m = compute_run_metrics(trades)
        assert m["sample_adequacy_score"] == pytest.approx(0.5)

    def test_sample_adequacy_full(self):
        trades = [_make_trade(f"T{i}") for i in range(30)]
        m = compute_run_metrics(trades)
        assert m["sample_adequacy_score"] == pytest.approx(1.0)

    def test_sample_adequacy_capped(self):
        trades = [_make_trade(f"T{i}") for i in range(50)]
        m = compute_run_metrics(trades)
        assert m["sample_adequacy_score"] == pytest.approx(1.0)

    def test_quality_adjusted_score_formula(self):
        # 4 trades, all win with r=1.0 => win_rate=1.0, expectancy=1.0, sqrt(4)=2
        trades = [_make_trade(f"T{i}", realized_r=1.0) for i in range(4)]
        m = compute_run_metrics(trades)
        assert m["quality_adjusted_score"] == pytest.approx(2.0)

    def test_max_drawdown_computed(self):
        trades = [
            _make_trade("T1", realized_r=3.0),
            _make_trade("T2", realized_r=-2.0),
            _make_trade("T3", realized_r=-2.0),
        ]
        m = compute_run_metrics(trades)
        # equity: 3, 1, -1 => peak=3, dd from peak = max(0, -2, -4) = -4
        assert m["max_drawdown_r"] == pytest.approx(-4.0)

    def test_profit_factor_mixed(self):
        trades = [
            _make_trade("T1", realized_r=2.0),
            _make_trade("T2", realized_r=3.0),
            _make_trade("T3", realized_r=-1.0),
            _make_trade("T4", realized_r=-1.0),
        ]
        m = compute_run_metrics(trades)
        assert m["profit_factor"] == pytest.approx(2.5)


class TestComputeAggregateMetrics:
    def test_empty(self):
        agg = compute_aggregate_metrics([])
        assert agg["run_count"] == 0
        assert agg["total_trades"] == 0

    def test_single_run(self):
        run = compute_run_metrics([_make_trade("T1", realized_r=1.0)])
        agg = compute_aggregate_metrics([run])
        assert agg["run_count"] == 1
        assert agg["total_trades"] == 1
        assert agg["expectancy_r"] == pytest.approx(1.0)

    def test_multiple_runs(self):
        r1 = compute_run_metrics([_make_trade("T1", realized_r=1.0)])
        r2 = compute_run_metrics([_make_trade("T2", realized_r=-0.5)])
        agg = compute_aggregate_metrics([r1, r2])
        assert agg["run_count"] == 2
        assert agg["total_trades"] == 2
        assert agg["median_expectancy_r"] == pytest.approx(0.25)

    def test_worst_drawdown_propagated(self):
        r1 = compute_run_metrics([
            _make_trade("T1", realized_r=5.0),
            _make_trade("T2", realized_r=-3.0),
        ])
        r2 = compute_run_metrics([
            _make_trade("T3", realized_r=1.0),
            _make_trade("T4", realized_r=-1.0),
        ])
        agg = compute_aggregate_metrics([r1, r2])
        assert agg["worst_drawdown_r"] <= r1["max_drawdown_r"]
        assert agg["worst_drawdown_r"] <= r2["max_drawdown_r"]

    def test_aggregate_has_expected_keys(self):
        r = compute_run_metrics([_make_trade("T1")])
        agg = compute_aggregate_metrics([r])
        expected = {
            "run_count", "total_trades", "trade_count", "win_rate",
            "expectancy_r", "avg_r", "median_r", "max_drawdown_r",
            "profit_factor", "avg_mfe_r", "avg_mae_r", "exposure_bars",
            "avg_hold_bars", "quality_adjusted_score", "sample_adequacy_score",
            "median_expectancy_r", "worst_drawdown_r",
        }
        assert expected.issubset(set(agg.keys()))
