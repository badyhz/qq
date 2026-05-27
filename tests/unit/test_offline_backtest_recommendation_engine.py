"""Tests for offline backtest recommendation engine (Phase 22)."""
from __future__ import annotations

import pytest

from core.offline_backtest_recommendation_engine import (
    BacktestRecommendation,
    generate_backtest_recommendations,
    rank_recommendations,
)


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

def _pass_scorecard(cell_id="cell_0000", param_label="conservative"):
    return {
        "cell_id": cell_id,
        "symbol": "BTCUSDT",
        "timeframe": "5m",
        "param_label": param_label,
        "grade": "PASS",
        "reason_codes": [],
        "blockers": [],
        "metrics": {
            "expectancy_r": 0.5,
            "win_rate": 0.65,
            "sample_quality_score": 0.8,
            "max_drawdown_r": -2.0,
            "profit_factor": 1.8,
            "candidate_count": 20,
        },
    }


def _watch_scorecard(cell_id="cell_0001", param_label="balanced"):
    return {
        "cell_id": cell_id,
        "symbol": "BTCUSDT",
        "timeframe": "5m",
        "param_label": param_label,
        "grade": "WATCH",
        "reason_codes": ["low_sample_quality"],
        "blockers": [],
        "metrics": {
            "expectancy_r": 0.1,
            "win_rate": 0.50,
            "sample_quality_score": 0.35,
            "max_drawdown_r": -3.0,
            "profit_factor": 1.1,
            "candidate_count": 5,
        },
    }


def _reject_scorecard(cell_id="cell_0002", param_label="aggressive"):
    return {
        "cell_id": cell_id,
        "symbol": "BTCUSDT",
        "timeframe": "5m",
        "param_label": param_label,
        "grade": "REJECT",
        "reason_codes": ["insufficient_candidates"],
        "blockers": ["insufficient_candidates"],
        "metrics": {
            "expectancy_r": -0.3,
            "win_rate": 0.30,
            "sample_quality_score": 0.1,
            "max_drawdown_r": -8.0,
            "profit_factor": 0.5,
            "candidate_count": 2,
        },
    }


def _empty_comparison():
    return {"best_by_metric": {}}


def _comparison_with_best(cell_id="cell_0000"):
    return {
        "best_by_metric": {
            "expectancy_r": cell_id,
            "win_rate": cell_id,
        }
    }


# ---------------------------------------------------------------------------
# generate_backtest_recommendations tests
# ---------------------------------------------------------------------------

class TestGenerateBacktestRecommendations:
    def test_empty_scorecards_returns_empty(self):
        recs = generate_backtest_recommendations([], _empty_comparison())
        assert recs == ()

    def test_pass_scorecard_promotes(self):
        recs = generate_backtest_recommendations(
            [_pass_scorecard()], _empty_comparison()
        )
        assert len(recs) == 1
        assert recs[0].action == "PROMOTE"

    def test_reject_scorecard_with_blockers(self):
        recs = generate_backtest_recommendations(
            [_reject_scorecard()], _empty_comparison()
        )
        assert len(recs) == 1
        assert recs[0].action == "REJECT_OVERFIT"

    def test_watch_scorecard_collect_more_data(self):
        recs = generate_backtest_recommendations(
            [_watch_scorecard()], _empty_comparison()
        )
        assert len(recs) == 1
        # Low sample quality -> COLLECT_MORE_DATA
        assert recs[0].action == "COLLECT_MORE_DATA"

    def test_multiple_scorecards(self):
        recs = generate_backtest_recommendations(
            [_pass_scorecard(), _watch_scorecard(), _reject_scorecard()],
            _empty_comparison(),
        )
        assert len(recs) == 3

    def test_recommendation_fields_present(self):
        recs = generate_backtest_recommendations(
            [_pass_scorecard()], _empty_comparison()
        )
        rec = recs[0]
        assert isinstance(rec, BacktestRecommendation)
        assert rec.recommendation_id
        assert rec.action
        assert 0.0 <= rec.confidence <= 1.0
        assert rec.rationale
        assert rec.param_id
        assert isinstance(rec.risk_factors, tuple)

    def test_frozen_dataclass(self):
        recs = generate_backtest_recommendations(
            [_pass_scorecard()], _empty_comparison()
        )
        with pytest.raises(AttributeError):
            recs[0].action = "CHANGED"

    def test_best_in_metric_boosts_rationale(self):
        recs = generate_backtest_recommendations(
            [_pass_scorecard()], _comparison_with_best("cell_0000")
        )
        assert "Best in at least one" in recs[0].rationale

    def test_risk_factors_populated(self):
        sc = _watch_scorecard()
        sc["metrics"]["max_drawdown_r"] = -6.0
        recs = generate_backtest_recommendations([sc], _empty_comparison())
        assert len(recs[0].risk_factors) > 0

    def test_no_edge_keeps_hold(self):
        sc = {
            "cell_id": "c0",
            "param_label": "p0",
            "grade": "WATCH",
            "reason_codes": [],
            "blockers": [],
            "metrics": {
                "expectancy_r": -0.01,
                "win_rate": 0.40,
                "sample_quality_score": 0.1,
                "max_drawdown_r": -1.0,
            },
        }
        recs = generate_backtest_recommendations([sc], _empty_comparison())
        assert recs[0].action == "KEEP_HOLD"

    def test_robustness_param_accepted(self):
        """robustness param is accepted without error."""
        recs = generate_backtest_recommendations(
            [_pass_scorecard()], _empty_comparison(), robustness={"ok": True}
        )
        assert len(recs) == 1


# ---------------------------------------------------------------------------
# rank_recommendations tests
# ---------------------------------------------------------------------------

class TestRankRecommendations:
    def test_promote_ranked_first(self):
        recs = generate_backtest_recommendations(
            [_reject_scorecard(), _pass_scorecard(), _watch_scorecard()],
            _empty_comparison(),
        )
        ranked = rank_recommendations(recs)
        assert ranked[0].action == "PROMOTE"

    def test_reject_ranked_last(self):
        recs = generate_backtest_recommendations(
            [_reject_scorecard(), _pass_scorecard(), _watch_scorecard()],
            _empty_comparison(),
        )
        ranked = rank_recommendations(recs)
        assert ranked[-1].action == "REJECT_OVERFIT"

    def test_empty_input(self):
        assert rank_recommendations(()) == ()

    def test_single_recommendation(self):
        recs = generate_backtest_recommendations(
            [_pass_scorecard()], _empty_comparison()
        )
        ranked = rank_recommendations(recs)
        assert len(ranked) == 1

    def test_confidence_tiebreaker(self):
        """Higher confidence ranked first within same action."""
        sc1 = _pass_scorecard("cell_0000", "conservative")
        sc1["metrics"]["expectancy_r"] = 0.3
        sc2 = _pass_scorecard("cell_0001", "balanced")
        sc2["metrics"]["expectancy_r"] = 0.8  # higher confidence
        recs = generate_backtest_recommendations([sc1, sc2], _empty_comparison())
        ranked = rank_recommendations(recs)
        # Both are PROMOTE, higher confidence first
        assert ranked[0].confidence >= ranked[1].confidence

    def test_returns_tuple(self):
        recs = generate_backtest_recommendations(
            [_pass_scorecard()], _empty_comparison()
        )
        ranked = rank_recommendations(recs)
        assert isinstance(ranked, tuple)
