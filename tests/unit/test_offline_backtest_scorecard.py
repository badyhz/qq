"""Tests for core/offline_backtest_scorecard.py — 20+ tests."""
from __future__ import annotations

import pytest

from core.offline_backtest_scorecard import BacktestScorecard, grade_run


def _good_run(**overrides) -> dict:
    """A run that passes all gates."""
    base = {
        "trade_count": 20,
        "expectancy_r": 0.5,
        "max_drawdown_r": -2.0,
        "profit_factor": 1.5,
        "data_quality_clean": True,
        "split_coverage_full": True,
    }
    base.update(overrides)
    return base


class TestBacktestScorecard:
    def test_frozen(self):
        sc = BacktestScorecard(
            scorecard_id="SC1", run_id="R1", grade="PASS",
            metrics={}, quality_gates={}, reasons=(),
        )
        with pytest.raises(AttributeError):
            sc.grade = "REJECT"

    def test_empty_scorecard_id_raises(self):
        with pytest.raises(ValueError, match="scorecard_id"):
            BacktestScorecard(
                scorecard_id="", run_id="R1", grade="PASS",
                metrics={}, quality_gates={}, reasons=(),
            )

    def test_empty_run_id_raises(self):
        with pytest.raises(ValueError, match="run_id"):
            BacktestScorecard(
                scorecard_id="SC1", run_id="", grade="PASS",
                metrics={}, quality_gates={}, reasons=(),
            )

    def test_invalid_grade_raises(self):
        with pytest.raises(ValueError, match="grade"):
            BacktestScorecard(
                scorecard_id="SC1", run_id="R1", grade="INVALID",
                metrics={}, quality_gates={}, reasons=(),
            )

    def test_reasons_must_be_tuple(self):
        with pytest.raises(ValueError, match="reasons"):
            BacktestScorecard(
                scorecard_id="SC1", run_id="R1", grade="PASS",
                metrics={}, quality_gates={}, reasons=["not", "tuple"],
            )

    def test_valid_grades_accepted(self):
        for g in ("PASS", "WATCH", "REJECT", "INSUFFICIENT_SAMPLE"):
            sc = BacktestScorecard(
                scorecard_id="SC1", run_id="R1", grade=g,
                metrics={}, quality_gates={}, reasons=(),
            )
            assert sc.grade == g


class TestGradeRun:
    def test_pass_all_gates(self):
        sc = grade_run(_good_run(), run_id="R1")
        assert sc.grade == "PASS"
        assert len(sc.reasons) == 0

    def test_insufficient_sample(self):
        sc = grade_run(_good_run(trade_count=5), run_id="R2")
        assert sc.grade == "INSUFFICIENT_SAMPLE"
        assert any("trade_count" in r for r in sc.reasons)

    def test_reject_negative_expectancy(self):
        sc = grade_run(_good_run(expectancy_r=-0.1), run_id="R3")
        assert sc.grade == "REJECT"
        assert any("expectancy" in r for r in sc.reasons)

    def test_reject_zero_expectancy(self):
        sc = grade_run(_good_run(expectancy_r=0.0), run_id="R3b")
        assert sc.grade == "REJECT"

    def test_reject_bad_drawdown(self):
        sc = grade_run(_good_run(max_drawdown_r=-10.0), run_id="R4")
        assert sc.grade == "REJECT"
        assert any("drawdown" in r for r in sc.reasons)

    def test_reject_low_profit_factor(self):
        sc = grade_run(_good_run(profit_factor=0.5), run_id="R5")
        assert sc.grade == "REJECT"
        assert any("profit_factor" in r for r in sc.reasons)

    def test_watch_data_quality(self):
        sc = grade_run(_good_run(data_quality_clean=False), run_id="R6")
        assert sc.grade == "WATCH"
        assert any("data_quality" in r for r in sc.reasons)

    def test_watch_split_coverage(self):
        sc = grade_run(_good_run(split_coverage_full=False), run_id="R7")
        assert sc.grade == "WATCH"
        assert any("split" in r for r in sc.reasons)

    def test_reject_takes_priority_over_watch(self):
        # Both reject-level and watch-level failures
        sc = grade_run(
            _good_run(expectancy_r=-0.1, data_quality_clean=False),
            run_id="R8",
        )
        assert sc.grade == "REJECT"

    def test_insufficient_sample_takes_priority(self):
        sc = grade_run(
            _good_run(trade_count=0, expectancy_r=-1.0, profit_factor=0.0),
            run_id="R9",
        )
        assert sc.grade == "INSUFFICIENT_SAMPLE"

    def test_quality_gates_populated(self):
        sc = grade_run(_good_run(), run_id="R10")
        assert sc.quality_gates["min_trades"] is True
        assert sc.quality_gates["positive_expectancy"] is True
        assert sc.quality_gates["max_drawdown_r"] is True
        assert sc.quality_gates["profit_factor"] is True
        assert sc.quality_gates["data_quality_clean"] is True
        assert sc.quality_gates["split_coverage_full"] is True

    def test_metrics_preserved(self):
        run = _good_run()
        sc = grade_run(run, run_id="R11")
        assert sc.metrics is run

    def test_custom_thresholds(self):
        # Pass with custom lower thresholds
        sc = grade_run(
            _good_run(trade_count=3, expectancy_r=0.01, profit_factor=0.5),
            run_id="R12",
            min_trades=2,
            min_profit_factor=0.3,
        )
        assert sc.grade == "PASS"

    def test_default_run_id(self):
        sc = grade_run(_good_run())
        assert sc.run_id == "unknown"

    def test_default_scorecard_id(self):
        sc = grade_run(_good_run(), run_id="R13")
        assert "R13" in sc.scorecard_id

    def test_boundary_trade_count(self):
        sc = grade_run(_good_run(trade_count=10), run_id="R14")
        assert sc.grade == "PASS"

    def test_boundary_drawdown_exact(self):
        # drawdown exactly at threshold => REJECT (not > threshold)
        sc = grade_run(_good_run(max_drawdown_r=-5.0), run_id="R15")
        assert sc.grade == "REJECT"

    def test_boundary_profit_factor_exact(self):
        # pf exactly 1.0 => REJECT (not > 1.0)
        sc = grade_run(_good_run(profit_factor=1.0), run_id="R16")
        assert sc.grade == "REJECT"

    def test_multiple_reject_reasons(self):
        sc = grade_run(
            _good_run(expectancy_r=-1.0, max_drawdown_r=-10.0, profit_factor=0.5),
            run_id="R17",
        )
        assert sc.grade == "REJECT"
        assert len(sc.reasons) >= 3

    def test_watch_both_soft_failures(self):
        sc = grade_run(
            _good_run(data_quality_clean=False, split_coverage_full=False),
            run_id="R18",
        )
        assert sc.grade == "WATCH"
        assert len(sc.reasons) == 2
