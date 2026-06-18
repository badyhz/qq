"""Tests for paper performance metrics — global, strategy, sample status."""
from __future__ import annotations

import os
import py_compile

import pytest

from core.paper_trading.paper_performance_metrics import (
    compute_performance, GlobalMetrics, StrategyScorecard, PerformanceScorecard,
    SAMPLE_STATUS_INSUFFICIENT, SAMPLE_STATUS_LOW, SAMPLE_STATUS_EVALUABLE,
    STRATEGY_STATUS_OBSERVE_ONLY, STRATEGY_STATUS_OBSERVE_MORE,
    STRATEGY_STATUS_CANDIDATE_KEEP, STRATEGY_STATUS_CANDIDATE_DISABLE,
)

MODULE_PATH = os.path.join(os.path.dirname(__file__), "..", "..",
                           "core", "paper_trading", "paper_performance_metrics.py")


def _clean_open(**overrides):
    pos = {
        "position_id": "PP_open",
        "intent_id": "TI_open",
        "strategy_id": "weak_short_watch",
        "strategy_type": "weak_short_watch",
        "symbol": "XRPUSDT",
        "side": "SHORT",
        "status": "OPEN",
        "entry_price": 1.15,
        "stop_loss": 1.18,
        "take_profit": 1.09,
        "realized_pnl": 0.0,
        "unrealized_pnl": 0.0,
        "r_multiple": 0.0,
        "lifecycle_mode": "future_only",
        "opened_bar_time": 5000,
        "quarantine_status": "CLEAN",
        "excluded_from_performance_stats": False,
        "quarantine_reasons": [],
    }
    pos.update(overrides)
    return pos


def _clean_tp(**overrides):
    pos = _clean_open(
        position_id="PP_tp",
        status="TAKE_PROFIT_HIT",
        realized_pnl=20.0,
        r_multiple=2.0,
    )
    pos.update(overrides)
    return pos


def _clean_sl(**overrides):
    pos = _clean_open(
        position_id="PP_sl",
        status="STOP_LOSS_HIT",
        realized_pnl=-10.0,
        r_multiple=-1.0,
    )
    pos.update(overrides)
    return pos


def _clean_timeout(**overrides):
    pos = _clean_open(
        position_id="PP_timeout",
        status="TIMEOUT_EXIT",
        realized_pnl=-5.0,
        r_multiple=-0.5,
    )
    pos.update(overrides)
    return pos


def _excluded_legacy(**overrides):
    pos = {
        "position_id": "PP_legacy",
        "strategy_id": "weak_short_watch",
        "strategy_type": "weak_short_watch",
        "symbol": "XRPUSDT",
        "status": "STOP_LOSS_HIT",
        "realized_pnl": -50.0,
        "r_multiple": -1.0,
        "quarantine_status": "LEGACY_PRE_FUTURE_ONLY_FIX",
        "excluded_from_performance_stats": True,
        "quarantine_reasons": ["missing_lifecycle_mode"],
    }
    pos.update(overrides)
    return pos


class TestModuleCompiles:
    def test_compiles(self):
        py_compile.compile(MODULE_PATH, doraise=True)


class TestEmptyInput:
    def test_empty_positions(self):
        sc = compute_performance([], "2026-06-18")
        gm = sc.global_metrics
        assert gm.total_positions == 0
        assert gm.clean_positions == 0
        assert gm.excluded_positions == 0
        assert gm.sample_status == SAMPLE_STATUS_INSUFFICIENT

    def test_empty_to_dict(self):
        sc = compute_performance([], "2026-06-18")
        d = sc.to_dict()
        assert "date" in d
        assert "global_metrics" in d
        assert "strategy_scorecards" in d


class TestExcludedPositions:
    def test_excluded_not_in_clean(self):
        positions = [_clean_open(), _excluded_legacy()]
        sc = compute_performance(positions, "2026-06-18")
        assert sc.global_metrics.clean_positions == 1
        assert sc.global_metrics.excluded_positions == 1

    def test_excluded_legacy_not_in_stats(self):
        positions = [_excluded_legacy()]
        sc = compute_performance(positions, "2026-06-18")
        assert sc.global_metrics.clean_positions == 0
        assert sc.global_metrics.excluded_positions == 1
        assert sc.global_metrics.realized_pnl == 0.0


class TestCleanOpenPositions:
    def test_open_in_open_count(self):
        sc = compute_performance([_clean_open()], "2026-06-18")
        assert sc.global_metrics.open_positions == 1
        assert sc.global_metrics.closed_positions == 0

    def test_open_not_in_closed_metrics(self):
        sc = compute_performance([_clean_open()], "2026-06-18")
        assert sc.global_metrics.win_rate == 0.0
        assert sc.global_metrics.sample_status == SAMPLE_STATUS_INSUFFICIENT


class TestCleanClosedPositions:
    def test_tp_is_win(self):
        sc = compute_performance([_clean_tp()], "2026-06-18")
        gm = sc.global_metrics
        assert gm.closed_positions == 1
        assert gm.take_profit_hit == 1
        assert gm.win_rate == 1.0
        assert gm.realized_pnl == 20.0

    def test_sl_is_loss(self):
        sc = compute_performance([_clean_sl()], "2026-06-18")
        gm = sc.global_metrics
        assert gm.stop_loss_hit == 1
        assert gm.loss_rate == 1.0
        assert gm.realized_pnl == -10.0

    def test_timeout_is_loss(self):
        sc = compute_performance([_clean_timeout()], "2026-06-18")
        gm = sc.global_metrics
        assert gm.timeout_exit == 1
        assert gm.loss_rate == 1.0


class TestWinRate:
    def test_2_of_3_wins(self):
        positions = [_clean_tp(), _clean_tp(position_id="PP_tp2"), _clean_sl()]
        sc = compute_performance(positions, "2026-06-18")
        assert sc.global_metrics.win_rate == pytest.approx(2 / 3, abs=0.001)

    def test_all_losses(self):
        sc = compute_performance([_clean_sl(), _clean_timeout()], "2026-06-18")
        assert sc.global_metrics.win_rate == 0.0
        assert sc.global_metrics.loss_rate == 1.0


class TestProfitFactor:
    def test_profit_factor_basic(self):
        positions = [_clean_tp(realized_pnl=20.0), _clean_sl(realized_pnl=-10.0)]
        sc = compute_performance(positions, "2026-06-18")
        assert sc.global_metrics.profit_factor == 2.0

    def test_profit_factor_no_loss(self):
        sc = compute_performance([_clean_tp()], "2026-06-18")
        assert sc.global_metrics.profit_factor == float("inf")

    def test_profit_factor_no_profit(self):
        sc = compute_performance([_clean_sl()], "2026-06-18")
        assert sc.global_metrics.profit_factor == 0.0


class TestExpectancyR:
    def test_avg_r_is_expectancy(self):
        positions = [_clean_tp(r_multiple=2.0), _clean_sl(r_multiple=-1.0)]
        sc = compute_performance(positions, "2026-06-18")
        assert sc.global_metrics.expectancy_r == 0.5


class TestMaxR:
    def test_max_win_loss_r(self):
        positions = [
            _clean_tp(r_multiple=3.0),
            _clean_sl(r_multiple=-2.0),
            _clean_tp(r_multiple=1.5),
        ]
        sc = compute_performance(positions, "2026-06-18")
        assert sc.global_metrics.max_single_win_r == 3.0
        assert sc.global_metrics.max_single_loss_r == -2.0


class TestSampleStatus:
    def test_zero_closed_insufficient(self):
        sc = compute_performance([_clean_open()], "2026-06-18")
        assert sc.global_metrics.sample_status == SAMPLE_STATUS_INSUFFICIENT

    def test_1_closed_low(self):
        sc = compute_performance([_clean_tp()], "2026-06-18")
        assert sc.global_metrics.sample_status == SAMPLE_STATUS_LOW

    def test_9_closed_low(self):
        positions = [_clean_tp(position_id=f"PP{i}") for i in range(9)]
        sc = compute_performance(positions, "2026-06-18")
        assert sc.global_metrics.sample_status == SAMPLE_STATUS_LOW

    def test_10_closed_evaluable(self):
        positions = [_clean_tp(position_id=f"PP{i}") for i in range(10)]
        sc = compute_performance(positions, "2026-06-18")
        assert sc.global_metrics.sample_status == SAMPLE_STATUS_EVALUABLE


class TestStrategyScorecard:
    def test_single_strategy(self):
        positions = [_clean_open(), _clean_tp()]
        sc = compute_performance(positions, "2026-06-18")
        assert len(sc.strategy_scorecards) == 1
        ss = sc.strategy_scorecards[0]
        assert ss.strategy_id == "weak_short_watch"
        assert ss.position_count == 2
        assert ss.open_count == 1
        assert ss.closed_count == 1

    def test_multiple_strategies(self):
        p1 = _clean_open(strategy_id="strat_a")
        p2 = _clean_open(strategy_id="strat_b", position_id="PP_b")
        sc = compute_performance([p1, p2], "2026-06-18")
        ids = {s.strategy_id for s in sc.strategy_scorecards}
        assert ids == {"strat_a", "strat_b"}

    def test_strategy_status_observe_only(self):
        sc = compute_performance([_clean_open()], "2026-06-18")
        ss = sc.strategy_scorecards[0]
        assert ss.sample_status == SAMPLE_STATUS_INSUFFICIENT
        assert ss.strategy_status == STRATEGY_STATUS_OBSERVE_ONLY

    def test_strategy_status_observe_more(self):
        sc = compute_performance([_clean_tp()], "2026-06-18")
        ss = sc.strategy_scorecards[0]
        assert ss.sample_status == SAMPLE_STATUS_LOW
        assert ss.strategy_status == STRATEGY_STATUS_OBSERVE_MORE

    def test_strategy_status_candidate_keep(self):
        positions = [_clean_tp(position_id=f"PP{i}", r_multiple=2.0, realized_pnl=20.0) for i in range(10)]
        sc = compute_performance(positions, "2026-06-18")
        ss = sc.strategy_scorecards[0]
        assert ss.sample_status == SAMPLE_STATUS_EVALUABLE
        assert ss.strategy_status == STRATEGY_STATUS_CANDIDATE_KEEP

    def test_strategy_status_candidate_disable(self):
        positions = [_clean_sl(position_id=f"PP{i}", r_multiple=-1.0, realized_pnl=-10.0) for i in range(10)]
        sc = compute_performance(positions, "2026-06-18")
        ss = sc.strategy_scorecards[0]
        assert ss.sample_status == SAMPLE_STATUS_EVALUABLE
        assert ss.strategy_status == STRATEGY_STATUS_CANDIDATE_DISABLE


class TestStrategyScore:
    def test_zero_score_when_no_closed(self):
        sc = compute_performance([_clean_open()], "2026-06-18")
        assert sc.strategy_scorecards[0].strategy_score == 0.0

    def test_positive_score_with_wins(self):
        positions = [_clean_tp(position_id=f"PP{i}", r_multiple=2.0, realized_pnl=20.0) for i in range(5)]
        sc = compute_performance(positions, "2026-06-18")
        assert sc.strategy_scorecards[0].strategy_score > 0.0


class TestSafetyFlags:
    def test_safety_flags_present(self):
        sc = compute_performance([], "2026-06-18")
        for flag in ["PAPER_ONLY", "NO_ORDER", "STATS_FROM_CLEAN_POSITIONS_ONLY"]:
            assert flag in sc.safety_flags


class TestNoForbiddenPatterns:
    def test_no_order_words(self):
        with open(MODULE_PATH) as f:
            content = f.read()
        for word in ["submit_order", "place_order", "cancel_order", "execute_trade"]:
            assert word not in content

    def test_no_env_reads(self):
        with open(MODULE_PATH) as f:
            content = f.read()
        assert "os.environ" not in content
        assert "os.getenv" not in content
