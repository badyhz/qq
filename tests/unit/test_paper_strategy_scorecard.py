"""Tests for strategy scorecard."""
from __future__ import annotations

import pytest

from core.paper_trading.performance_metrics import PerformanceMetrics
from core.paper_trading.strategy_scorecard import Rating, Scorecard, score_strategy


def _metrics(**kwargs):
    defaults = dict(
        total_trades=10, winners=6, losers=4, breakevens=0,
        win_rate=0.6, total_pnl=1000, avg_pnl_per_trade=100,
        avg_win=300, avg_loss=-100, profit_factor=1.8,
        max_drawdown=500, max_consecutive_losses=2,
        avg_rr_actual=1.2, expectancy=140,
    )
    defaults.update(kwargs)
    return PerformanceMetrics(**defaults)


class TestStrategyScorecard:
    def test_empty_reject(self):
        m = _metrics(total_trades=0, winners=0, losers=0, win_rate=0,
                     total_pnl=0, avg_pnl_per_trade=0, avg_win=0,
                     avg_loss=0, profit_factor=0, max_drawdown=0,
                     max_consecutive_losses=0, avg_rr_actual=0, expectancy=0)
        s = score_strategy(m)
        assert s.rating == Rating.REJECT
        assert s.final_score == 0

    def test_good_strategy_a_or_b(self):
        m = _metrics(
            total_trades=25, winners=17, losers=8, win_rate=0.68,
            total_pnl=5000, avg_pnl_per_trade=200,
            avg_win=500, avg_loss=-150, profit_factor=2.8,
            max_drawdown=300, max_consecutive_losses=2,
            avg_rr_actual=1.5, expectancy=295,
        )
        s = score_strategy(m)
        assert s.rating in (Rating.A, Rating.B)
        assert s.final_score >= 55

    def test_small_sample_downgrade(self):
        m = _metrics(
            total_trades=3, winners=3, losers=0, win_rate=1.0,
            total_pnl=300, avg_pnl_per_trade=100,
            avg_win=100, avg_loss=0, profit_factor=float("inf"),
            max_drawdown=0, max_consecutive_losses=0,
            avg_rr_actual=2.0, expectancy=100,
        )
        s = score_strategy(m)
        # All wins but small sample → max B
        assert s.rating in (Rating.B, Rating.C, Rating.D)

    def test_all_wins_small_sample_cap_b(self):
        m = _metrics(
            total_trades=4, winners=4, losers=0, win_rate=1.0,
            total_pnl=800, avg_pnl_per_trade=200,
            avg_win=200, avg_loss=0, profit_factor=float("inf"),
            max_drawdown=0, max_consecutive_losses=0,
            avg_rr_actual=2.0, expectancy=200,
        )
        s = score_strategy(m)
        assert s.rating != Rating.A  # can't be A with small sample

    def test_negative_expectancy_c_or_d(self):
        m = _metrics(
            total_trades=15, winners=4, losers=11, win_rate=0.27,
            total_pnl=-2000, avg_pnl_per_trade=-133,
            avg_win=200, avg_loss=-236, profit_factor=0.30,
            max_drawdown=3000, max_consecutive_losses=6,
            avg_rr_actual=-0.5, expectancy=-173,
        )
        s = score_strategy(m)
        assert s.rating in (Rating.C, Rating.D, Rating.REJECT)

    def test_high_drawdown_penalty(self):
        m = _metrics(
            total_trades=20, winners=10, losers=10, win_rate=0.5,
            total_pnl=100, avg_pnl_per_trade=5,
            avg_win=500, avg_loss=-490, profit_factor=1.02,
            max_drawdown=15000, max_consecutive_losses=5,
            avg_rr_actual=0.1, expectancy=5,
        )
        s = score_strategy(m)
        assert s.risk_penalty < 0

    def test_scorecard_frozen(self):
        m = _metrics()
        s = score_strategy(m)
        with pytest.raises(AttributeError):
            s.final_score = 999  # type: ignore

    def test_score_components_reasonable(self):
        m = _metrics()
        s = score_strategy(m)
        assert 0 <= s.win_rate_score <= 20
        assert 0 <= s.profit_factor_score <= 20
        assert 0 <= s.drawdown_score <= 20
        assert 0 <= s.expectancy_score <= 20
        assert 0 <= s.trade_count_score <= 20

    def test_stable_profit_higher_score(self):
        good = _metrics(total_trades=20, winners=14, losers=6, win_rate=0.7,
                        total_pnl=5000, avg_pnl_per_trade=250,
                        avg_win=500, avg_loss=-150, profit_factor=3.0,
                        max_drawdown=200, max_consecutive_losses=1,
                        avg_rr_actual=2.0, expectancy=295)
        bad = _metrics(total_trades=20, winners=8, losers=12, win_rate=0.4,
                       total_pnl=-500, avg_pnl_per_trade=-25,
                       avg_win=200, avg_loss=-250, profit_factor=0.53,
                       max_drawdown=5000, max_consecutive_losses=5,
                       avg_rr_actual=-0.3, expectancy=-130)
        s_good = score_strategy(good)
        s_bad = score_strategy(bad)
        assert s_good.final_score > s_bad.final_score
        assert s_good.rating.value < s_bad.rating.value  # A < B < C < D < REJECT
