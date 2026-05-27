"""Tests for core/offline_backtest_comparison.py — 15+ tests."""
from __future__ import annotations

import pytest

from core.offline_backtest_comparison import ComparisonResult, compare_parameter_sets


def _sc(
    param_id: str = "P1",
    grade: str = "PASS",
    quality_adjusted_score: float = 1.0,
    trade_count: int = 20,
    max_drawdown_r: float = -2.0,
    profit_factor: float = 1.5,
    expectancy_r: float = 0.5,
    sample_adequacy_score: float = 1.0,
) -> dict:
    return {
        "param_id": param_id,
        "run_id": param_id,
        "scorecard_id": f"SC-{param_id}",
        "grade": grade,
        "metrics": {
            "quality_adjusted_score": quality_adjusted_score,
            "trade_count": trade_count,
            "max_drawdown_r": max_drawdown_r,
            "profit_factor": profit_factor,
            "expectancy_r": expectancy_r,
            "sample_adequacy_score": sample_adequacy_score,
        },
    }


class TestComparisonResult:
    def test_frozen(self):
        cr = ComparisonResult(
            comparison_id="C1", best_param_id="P1", worst_param_id="P2",
            stable_winner=False, overfit_candidate=False,
            drawdown_regression=False, sample_weakness=False,
            symbol_inconsistency=False, recommendations=(),
        )
        with pytest.raises(AttributeError):
            cr.stable_winner = True

    def test_empty_comparison_id_raises(self):
        with pytest.raises(ValueError, match="comparison_id"):
            ComparisonResult(
                comparison_id="", best_param_id="P1", worst_param_id="P2",
                stable_winner=False, overfit_candidate=False,
                drawdown_regression=False, sample_weakness=False,
                symbol_inconsistency=False, recommendations=(),
            )

    def test_recommendations_must_be_tuple(self):
        with pytest.raises(ValueError, match="recommendations"):
            ComparisonResult(
                comparison_id="C1", best_param_id="P1", worst_param_id="P2",
                stable_winner=False, overfit_candidate=False,
                drawdown_regression=False, sample_weakness=False,
                symbol_inconsistency=False, recommendations=["bad"],
            )


class TestCompareParameterSets:
    def test_empty_scorecards(self):
        cr = compare_parameter_sets([])
        assert cr.best_param_id == "none"
        assert cr.sample_weakness is True
        assert "no_scorecards" in cr.recommendations[0]

    def test_single_pass(self):
        cr = compare_parameter_sets([_sc()])
        assert cr.best_param_id == "P1"
        assert cr.stable_winner is True

    def test_stable_winner_detected(self):
        scs = [
            _sc("P1", quality_adjusted_score=2.0, max_drawdown_r=-1.0),
            _sc("P2", quality_adjusted_score=0.5),
        ]
        cr = compare_parameter_sets(scs)
        assert cr.stable_winner is True
        assert "P1" in cr.best_param_id or "stable winner" in cr.recommendations[0]

    def test_no_stable_winner_all_reject(self):
        scs = [
            _sc("P1", grade="REJECT", expectancy_r=-1.0),
            _sc("P2", grade="REJECT", expectancy_r=-0.5),
        ]
        cr = compare_parameter_sets(scs)
        assert cr.stable_winner is False

    def test_overfit_candidate(self):
        # Best has 10x score of median, few trades
        scs = [
            _sc("P1", quality_adjusted_score=10.0, trade_count=5),
            _sc("P2", quality_adjusted_score=1.0, trade_count=20),
            _sc("P3", quality_adjusted_score=1.0, trade_count=20),
            _sc("P4", quality_adjusted_score=1.0, trade_count=20),
        ]
        cr = compare_parameter_sets(scs)
        assert cr.overfit_candidate is True

    def test_no_overfit_many_trades(self):
        scs = [
            _sc("P1", quality_adjusted_score=10.0, trade_count=50),
            _sc("P2", quality_adjusted_score=1.0, trade_count=20),
            _sc("P3", quality_adjusted_score=1.0, trade_count=20),
        ]
        cr = compare_parameter_sets(scs)
        assert cr.overfit_candidate is False

    def test_drawdown_regression(self):
        scs = [_sc("P1", max_drawdown_r=-4.0)]
        cr = compare_parameter_sets(scs)
        assert cr.drawdown_regression is True

    def test_no_drawdown_regression(self):
        scs = [_sc("P1", max_drawdown_r=-1.0)]
        cr = compare_parameter_sets(scs)
        assert cr.drawdown_regression is False

    def test_sample_weakness(self):
        scs = [
            _sc("P1", sample_adequacy_score=0.3),
            _sc("P2", sample_adequacy_score=0.2),
            _sc("P3", sample_adequacy_score=0.4),
        ]
        cr = compare_parameter_sets(scs)
        assert cr.sample_weakness is True

    def test_no_sample_weakness(self):
        scs = [
            _sc("P1", sample_adequacy_score=1.0),
            _sc("P2", sample_adequacy_score=0.8),
        ]
        cr = compare_parameter_sets(scs)
        assert cr.sample_weakness is False

    def test_symbol_inconsistency(self):
        # High variance in expectancy
        scs = [
            _sc("P1", expectancy_r=5.0),
            _sc("P2", expectancy_r=-5.0),
            _sc("P3", expectancy_r=0.1),
        ]
        cr = compare_parameter_sets(scs)
        assert cr.symbol_inconsistency is True

    def test_no_symbol_inconsistency(self):
        scs = [
            _sc("P1", expectancy_r=0.5),
            _sc("P2", expectancy_r=0.6),
            _sc("P3", expectancy_r=0.55),
        ]
        cr = compare_parameter_sets(scs)
        assert cr.symbol_inconsistency is False

    def test_best_worst_ranking(self):
        scs = [
            _sc("LOW", quality_adjusted_score=0.1),
            _sc("HIGH", quality_adjusted_score=5.0),
            _sc("MID", quality_adjusted_score=1.0),
        ]
        cr = compare_parameter_sets(scs)
        assert cr.best_param_id == "HIGH"
        assert cr.worst_param_id == "LOW"

    def test_custom_comparison_id(self):
        cr = compare_parameter_sets([_sc()], comparison_id="MY-CMP")
        assert cr.comparison_id == "MY-CMP"

    def test_recommendations_populated(self):
        scs = [_sc("P1")]
        cr = compare_parameter_sets(scs)
        assert len(cr.recommendations) > 0
