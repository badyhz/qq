"""Tests for parameter sweep engine."""
from __future__ import annotations

import os
import pytest

from core.paper_trading.parameter_sweep import (
    ParameterSet, SweepConfig, SweepResult,
    default_score, generate_default_param_sets, run_sweep,
)
from core.paper_trading.performance_metrics import PerformanceMetrics

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "..", "fixtures", "paper_trading")


def _fixture(name: str) -> str:
    return os.path.join(FIXTURE_DIR, name)


def _noop_signal(bars, i):
    if i == 5:
        return {
            "symbol": "BTCUSDT", "side": "BUY",
            "entry_price": bars[i].close,
            "stop_loss": bars[i].close * 0.98,
            "take_profit": bars[i].close * 1.06,
            "invalidation_price": bars[i].close * 0.97,
            "signal_source": "sweep_test",
        }
    return None


class TestParameterSweep:
    def test_empty_param_sets_raises(self):
        config = SweepConfig(
            fixtures=[_fixture("macd_rebound_sample.json")],
            param_sets=[],
            signal_fn=_noop_signal,
        )
        with pytest.raises(ValueError, match="No parameter sets"):
            run_sweep(config)

    def test_empty_fixtures_raises(self):
        config = SweepConfig(
            fixtures=[],
            param_sets=[ParameterSet()],
            signal_fn=_noop_signal,
        )
        with pytest.raises(ValueError, match="No fixtures"):
            run_sweep(config)

    def test_single_param_set(self):
        config = SweepConfig(
            fixtures=[_fixture("macd_rebound_sample.json")],
            param_sets=[ParameterSet()],
            signal_fn=_noop_signal,
        )
        results = run_sweep(config)
        assert len(results) == 1
        assert isinstance(results[0].score, float)

    def test_multi_param_sorted(self):
        params = [
            ParameterSet(min_rr_ratio=1.0),
            ParameterSet(min_rr_ratio=2.0),
            ParameterSet(min_rr_ratio=1.5),
        ]
        config = SweepConfig(
            fixtures=[_fixture("macd_rebound_sample.json")],
            param_sets=params,
            signal_fn=_noop_signal,
        )
        results = run_sweep(config)
        assert len(results) == 3
        # Should be sorted by score descending
        for i in range(len(results) - 1):
            assert results[i].score >= results[i + 1].score

    def test_failed_fixture_no_crash(self):
        """Malformed fixture should not crash the sweep."""
        config = SweepConfig(
            fixtures=[
                _fixture("macd_rebound_sample.json"),
                _fixture("malformed_sample.json"),
            ],
            param_sets=[ParameterSet()],
            signal_fn=_noop_signal,
        )
        results = run_sweep(config)
        assert len(results) == 1
        assert results[0].fixtures_error >= 1

    def test_default_score_explainable(self):
        # Good metrics
        good = PerformanceMetrics(
            total_trades=20, winners=14, losers=6, breakevens=0,
            win_rate=0.7, total_pnl=5000, avg_pnl_per_trade=250,
            avg_win=500, avg_loss=-200, profit_factor=2.5,
            max_drawdown=500, max_consecutive_losses=2,
            avg_rr_actual=1.5, expectancy=290,
        )
        # Bad metrics
        bad = PerformanceMetrics(
            total_trades=5, winners=1, losers=4, breakevens=0,
            win_rate=0.2, total_pnl=-1000, avg_pnl_per_trade=-200,
            avg_win=100, avg_loss=-275, profit_factor=0.36,
            max_drawdown=1200, max_consecutive_losses=4,
            avg_rr_actual=-0.5, expectancy=-220,
        )
        good_score = default_score(good)
        bad_score = default_score(bad)
        assert good_score > bad_score

    def test_default_score_zero_trades(self):
        m = PerformanceMetrics(
            total_trades=0, winners=0, losers=0, breakevens=0,
            win_rate=0, total_pnl=0, avg_pnl_per_trade=0,
            avg_win=0, avg_loss=0, profit_factor=0,
            max_drawdown=0, max_consecutive_losses=0,
            avg_rr_actual=0, expectancy=0,
        )
        assert default_score(m) == -100.0

    def test_generate_default_param_sets(self):
        params = generate_default_param_sets()
        assert len(params) > 10
        # All should have tp > sl
        for p in params:
            assert p.take_profit_pct > p.stop_loss_pct

    def test_no_network_in_sweep(self):
        """Sweep should not import any network modules."""
        import core.paper_trading.parameter_sweep as mod
        source = open(mod.__file__).read()
        assert "requests" not in source
        assert "httpx" not in source
        assert "websocket" not in source

    def test_sweep_result_frozen(self):
        params = ParameterSet()
        m = PerformanceMetrics(
            total_trades=0, winners=0, losers=0, breakevens=0,
            win_rate=0, total_pnl=0, avg_pnl_per_trade=0,
            avg_win=0, avg_loss=0, profit_factor=0,
            max_drawdown=0, max_consecutive_losses=0,
            avg_rr_actual=0, expectancy=0,
        )
        r = SweepResult(params=params, metrics=m, score=0.0,
                        fixtures_run=1, fixtures_ok=1, fixtures_error=0)
        with pytest.raises(AttributeError):
            r.score = 999  # type: ignore
