"""Tests for offline backtest run evaluator. 15+ tests."""

import pytest

from core.offline_backtest_parameter_grid import BacktestParameterSet
from core.offline_backtest_run_evaluator import RunResult, _aggregate_metrics, evaluate_run
from core.walk_forward_split_engine import SplitType, WalkForwardSplit


def _bar(high=105.0, low=95.0, open_=100.0, close=104.0, ts=0):
    return {"timestamp": ts, "open": open_, "high": high, "low": low, "close": close, "volume": 1.0}


def _make_params(lookback=5, buffer=0.001, sl_r=0.75, tp_r=1.5, max_hold=20,
                 fee=10.0, slip=5.0, min_body=0.2, cooldown=3):
    return BacktestParameterSet(
        param_id="test_p1", label="test",
        lookback_bars=lookback, breakout_buffer_pct=buffer,
        stop_loss_r=sl_r, take_profit_r=tp_r, max_hold_bars=max_hold,
        fee_bps=fee, slippage_bps=slip, min_body_pct=min_body, cooldown_bars=cooldown,
    )


def _make_split(start=0, end=30, split_id=0, split_type=SplitType.TEST):
    return WalkForwardSplit(
        split_id=split_id, split_type=split_type,
        start_index=start, end_index=end, bar_count=end - start,
    )


def _make_breakout_bars(n=30):
    """Create bars with breakout pattern: range then breakout."""
    bars = []
    for i in range(n):
        if i < 15:
            bars.append(_bar(high=100.0, low=95.0, open_=97.0, close=98.0, ts=i))
        else:
            bars.append(_bar(high=108.0 + (i - 15) * 0.5, low=99.0, open_=100.0,
                             close=105.0 + (i - 15) * 0.3, ts=i))
    return bars


class TestRunResultDataclass:
    def test_frozen(self):
        r = RunResult(run_id="r1", symbol="BTC", timeframe="5m",
                      param_id="p1", split_id=0, trades=(), trade_count=0, metrics={})
        with pytest.raises(AttributeError):
            r.run_id = "r2"  # type: ignore

    def test_valid_construction(self):
        r = RunResult(run_id="r1", symbol="BTC", timeframe="5m",
                      param_id="p1", split_id=0, trades=(), trade_count=0, metrics={})
        assert r.run_id == "r1"
        assert r.trade_count == 0

    def test_mismatched_trade_count_raises(self):
        with pytest.raises(ValueError, match="trade_count"):
            RunResult(run_id="r1", symbol="BTC", timeframe="5m",
                      param_id="p1", split_id=0, trades=(), trade_count=5, metrics={})


class TestAggregateMetrics:
    def test_empty_trades(self):
        metrics = _aggregate_metrics([])
        assert metrics["total_trades"] == 0
        assert metrics["win_rate"] == 0.0
        assert metrics["total_net_pnl"] == 0.0

    def test_has_all_keys(self):
        metrics = _aggregate_metrics([])
        expected_keys = {"total_trades", "win_count", "loss_count", "win_rate",
                        "total_net_pnl", "total_gross_pnl", "total_fees",
                        "total_slippage_cost", "avg_r", "max_r", "min_r",
                        "avg_hold_bars", "max_mfe_r", "max_mae_r",
                        "profit_factor", "expectancy"}
        assert set(metrics.keys()) == expected_keys


class TestEvaluateRun:
    def test_empty_split_returns_zero_trades(self):
        bars = [_make_breakout_bars(30)]
        split = _make_split(start=0, end=0)
        params = _make_params()
        result = evaluate_run(bars[0], split, params, symbol="BTC", timeframe="5m")
        assert result.trade_count == 0

    def test_returns_run_result_type(self):
        bars = _make_breakout_bars(30)
        split = _make_split(start=0, end=30)
        params = _make_params()
        result = evaluate_run(bars, split, params)
        assert isinstance(result, RunResult)

    def test_symbol_and_timeframe_propagated(self):
        bars = _make_breakout_bars(30)
        split = _make_split(start=0, end=30)
        params = _make_params()
        result = evaluate_run(bars, split, params, symbol="ETHUSDT", timeframe="15m")
        assert result.symbol == "ETHUSDT"
        assert result.timeframe == "15m"

    def test_param_id_propagated(self):
        bars = _make_breakout_bars(30)
        split = _make_split(start=0, end=30)
        params = _make_params()
        result = evaluate_run(bars, split, params)
        assert result.param_id == params.param_id

    def test_split_id_propagated(self):
        bars = _make_breakout_bars(30)
        split = _make_split(start=0, end=30, split_id=7)
        params = _make_params()
        result = evaluate_run(bars, split, params)
        assert result.split_id == 7

    def test_metrics_dict_populated(self):
        bars = _make_breakout_bars(30)
        split = _make_split(start=0, end=30)
        params = _make_params()
        result = evaluate_run(bars, split, params)
        assert isinstance(result.metrics, dict)
        assert "total_trades" in result.metrics

    def test_run_id_is_unique(self):
        bars = _make_breakout_bars(30)
        split = _make_split(start=0, end=30)
        params = _make_params()
        r1 = evaluate_run(bars, split, params)
        r2 = evaluate_run(bars, split, params)
        assert r1.run_id != r2.run_id

    def test_trade_count_matches_trades_tuple(self):
        bars = _make_breakout_bars(30)
        split = _make_split(start=0, end=30)
        params = _make_params()
        result = evaluate_run(bars, split, params)
        assert result.trade_count == len(result.trades)

    def test_trades_are_tuple(self):
        bars = _make_breakout_bars(30)
        split = _make_split(start=0, end=30)
        params = _make_params()
        result = evaluate_run(bars, split, params)
        assert isinstance(result.trades, tuple)

    def test_range_bars_produce_no_signals(self):
        """Flat bars should produce no breakout signals."""
        bars = [_bar(high=100.0, low=95.0, open_=97.0, close=98.0, ts=i) for i in range(30)]
        split = _make_split(start=0, end=30)
        params = _make_params()
        result = evaluate_run(bars, split, params)
        assert result.trade_count == 0

    def test_breakout_bars_may_produce_signals(self):
        bars = _make_breakout_bars(50)
        split = _make_split(start=0, end=50)
        params = _make_params(lookback=5, buffer=0.001, min_body=0.1, cooldown=1)
        result = evaluate_run(bars, split, params)
        # At least check it doesn't crash and returns valid structure
        assert isinstance(result, RunResult)
        assert result.trade_count == len(result.trades)

    def test_partial_window(self):
        """Evaluate only part of the bars."""
        bars = _make_breakout_bars(50)
        split = _make_split(start=10, end=30)
        params = _make_params()
        result = evaluate_run(bars, split, params)
        assert isinstance(result, RunResult)

    def test_metrics_trade_count_consistency(self):
        bars = _make_breakout_bars(30)
        split = _make_split(start=0, end=30)
        params = _make_params()
        result = evaluate_run(bars, split, params)
        assert result.metrics["total_trades"] == result.trade_count
