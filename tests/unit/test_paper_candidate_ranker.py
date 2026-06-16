"""Tests for candidate ranker module."""
from __future__ import annotations

import pytest

from core.paper_trading.candidate_ranker import (
    Priority, RankedCandidate, rank_candidate, rank_candidates,
)


def _candidate(**kwargs):
    defaults = dict(
        review_id="test_001", symbol="BTCUSDT",
        strategy_name="macd_rebound", side="BUY",
        entry_price=50000.0, stop_loss=49000.0, take_profit=52000.0,
        score=62.0, rating="B", risk_summary="normal",
    )
    defaults.update(kwargs)
    return rank_candidate(**defaults)


class TestRankCandidate:
    def test_high_quality(self):
        r = _candidate(score=80, rating="A", trade_count=20, max_drawdown=3, profit_factor=2.5)
        assert r.priority == Priority.HIGH
        assert r.rank_score >= 60
        assert "rating_a" in r.reason_codes

    def test_medium_quality(self):
        r = _candidate(score=60, rating="B", trade_count=10, max_drawdown=4)
        assert r.priority in (Priority.HIGH, Priority.MEDIUM)
        assert "rating_b" in r.reason_codes

    def test_low_quality(self):
        r = _candidate(score=40, rating="C", trade_count=3, max_drawdown=6)
        assert r.priority == Priority.LOW
        assert "rating_c_marginal" in r.reason_codes

    def test_reject_rating(self):
        r = _candidate(score=20, rating="REJECT")
        assert r.priority == Priority.REJECT
        assert "rating_reject_weak" in r.reason_codes

    def test_d_rating_reject(self):
        r = _candidate(score=30, rating="D")
        assert r.priority == Priority.REJECT

    def test_small_sample_penalty(self):
        r1 = _candidate(score=70, rating="A", trade_count=20)
        r2 = _candidate(score=70, rating="A", trade_count=3)
        assert r1.rank_score > r2.rank_score
        assert "small_sample" in r2.reason_codes

    def test_high_drawdown_penalty(self):
        r1 = _candidate(score=70, rating="A", max_drawdown=2)
        r2 = _candidate(score=70, rating="A", max_drawdown=12)
        assert r1.rank_score > r2.rank_score
        assert "high_drawdown" in r2.reason_codes

    def test_duplicate_symbol_penalty(self):
        r1 = _candidate(score=70, rating="A", duplicate_symbol_count=0)
        r2 = _candidate(score=70, rating="A", duplicate_symbol_count=2)
        assert r1.rank_score > r2.rank_score
        assert "duplicate_symbol" in r2.reason_codes

    def test_human_summary_exists(self):
        r = _candidate()
        assert r.human_summary
        assert "BTCUSDT" in r.human_summary
        assert "BUY" in r.human_summary

    def test_good_rr_bonus(self):
        r = _candidate(entry_price=50000, stop_loss=49000, take_profit=53000)
        assert "good_rr" in r.reason_codes

    def test_weak_profit_factor_penalty(self):
        r = _candidate(profit_factor=0.5)
        assert "weak_profit_factor" in r.reason_codes


class TestRankCandidates:
    def test_stable_sorting(self):
        """Candidates with same score should maintain relative order."""
        cands = [
            _candidate(review_id="a", score=60, rating="B"),
            _candidate(review_id="b", score=60, rating="B"),
            _candidate(review_id="c", score=60, rating="B"),
        ]
        ranked = rank_candidates(cands)
        assert len(ranked) == 3
        assert ranked[0].rank == 1
        assert ranked[1].rank == 2
        assert ranked[2].rank == 3

    def test_higher_score_first(self):
        cands = [
            _candidate(review_id="low", score=40, rating="C"),
            _candidate(review_id="high", score=80, rating="A"),
        ]
        ranked = rank_candidates(cands)
        assert ranked[0].review_id == "high"
        assert ranked[0].rank == 1

    def test_empty_list(self):
        assert rank_candidates([]) == []
