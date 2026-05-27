"""Tests for core/offline_shadow_metric_engine.py -- 15+ tests with known fixtures."""
from __future__ import annotations

import math

import pytest

from core.offline_shadow_metric_engine import (
    compute_aggregate_metrics,
    compute_run_metrics,
)


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

def _outcomes(*returns: float) -> list[dict]:
    """Build outcome list from plain return_r values (no mfe/mae)."""
    return [{"return_r": r} for r in returns]


def _outcomes_full(records: list[tuple]) -> list[dict]:
    """Build outcome list from (return_r, mfe_r, mae_r) tuples."""
    return [{"return_r": r, "mfe_r": mfe, "mae_r": mae} for r, mfe, mae in records]


# ---------------------------------------------------------------------------
# compute_run_metrics -- basic counts
# ---------------------------------------------------------------------------

def test_empty_outcomes() -> None:
    m = compute_run_metrics([])
    assert m["candidate_count"] == 0
    assert m["win_count"] == 0
    assert m["loss_count"] == 0
    assert m["neutral_count"] == 0
    assert m["coverage_status"] == "empty"
    assert m["sample_quality_score"] == 0.0


def test_single_win() -> None:
    m = compute_run_metrics(_outcomes(2.0))
    assert m["candidate_count"] == 1
    assert m["win_count"] == 1
    assert m["loss_count"] == 0
    assert m["neutral_count"] == 0
    assert m["win_rate"] == 1.0


def test_single_loss() -> None:
    m = compute_run_metrics(_outcomes(-1.5))
    assert m["candidate_count"] == 1
    assert m["win_count"] == 0
    assert m["loss_count"] == 1
    assert m["win_rate"] == 0.0


def test_mixed_counts() -> None:
    outcomes = _outcomes(1.0, 2.0, -0.5, 0.0, 3.0)
    m = compute_run_metrics(outcomes)
    assert m["candidate_count"] == 5
    assert m["win_count"] == 3
    assert m["loss_count"] == 1
    assert m["neutral_count"] == 1


# ---------------------------------------------------------------------------
# compute_run_metrics -- win_rate and avg_return_r
# ---------------------------------------------------------------------------

def test_win_rate_known() -> None:
    outcomes = _outcomes(1.0, 1.0, -1.0, -1.0)
    m = compute_run_metrics(outcomes)
    assert m["win_rate"] == 0.5


def test_avg_return_r_known() -> None:
    outcomes = _outcomes(2.0, 4.0, -1.0)
    m = compute_run_metrics(outcomes)
    # (2 + 4 - 1) / 3 = 1.666...
    assert abs(m["avg_return_r"] - 5.0 / 3.0) < 1e-6


# ---------------------------------------------------------------------------
# compute_run_metrics -- expectancy_r
# ---------------------------------------------------------------------------

def test_expectancy_r_known() -> None:
    # 2 wins at 2.0, 2 losses at -1.0
    # win_rate=0.5, avg_win=2.0, loss_rate=0.5, avg_loss=1.0
    # expectancy = 0.5*2.0 - 0.5*1.0 = 0.5
    outcomes = _outcomes(2.0, 2.0, -1.0, -1.0)
    m = compute_run_metrics(outcomes)
    assert abs(m["expectancy_r"] - 0.5) < 1e-6


def test_expectancy_r_all_wins() -> None:
    outcomes = _outcomes(1.0, 3.0)
    m = compute_run_metrics(outcomes)
    # win_rate=1.0, avg_win=2.0, loss_rate=0.0
    assert abs(m["expectancy_r"] - 2.0) < 1e-6


def test_expectancy_r_all_losses() -> None:
    outcomes = _outcomes(-2.0, -4.0)
    m = compute_run_metrics(outcomes)
    # loss_rate=1.0, avg_loss=3.0
    assert abs(m["expectancy_r"] - (-3.0)) < 1e-6


# ---------------------------------------------------------------------------
# compute_run_metrics -- max_drawdown_r
# ---------------------------------------------------------------------------

def test_max_drawdown_monotonic_up() -> None:
    outcomes = _outcomes(1.0, 2.0, 3.0)
    m = compute_run_metrics(outcomes)
    assert m["max_drawdown_r"] == 0.0


def test_max_drawdown_known() -> None:
    # cumulative: 0 -> +3 -> +1 -> +4 -> +2
    # peaks:      0    3    3    4    4
    # dd:         0    0   -2    0   -2
    outcomes = _outcomes(3.0, -2.0, 3.0, -2.0)
    m = compute_run_metrics(outcomes)
    assert m["max_drawdown_r"] == -2.0


def test_max_drawdown_worst_single() -> None:
    outcomes = _outcomes(1.0, -5.0, 3.0)
    # cum: 1, -4, -1; peaks: 1, 1, 1; dd: 0, -5, -2
    m = compute_run_metrics(outcomes)
    assert m["max_drawdown_r"] == -5.0


# ---------------------------------------------------------------------------
# compute_run_metrics -- profit_factor
# ---------------------------------------------------------------------------

def test_profit_factor_known() -> None:
    # gross_profit=3.0, gross_loss=1.0 -> pf=3.0
    outcomes = _outcomes(1.0, 2.0, -1.0)
    m = compute_run_metrics(outcomes)
    assert abs(m["profit_factor"] - 3.0) < 1e-6


def test_profit_factor_no_losses() -> None:
    outcomes = _outcomes(1.0, 2.0)
    m = compute_run_metrics(outcomes)
    assert m["profit_factor"] == float("inf")


def test_profit_factor_no_wins() -> None:
    outcomes = _outcomes(-1.0, -2.0)
    m = compute_run_metrics(outcomes)
    assert m["profit_factor"] == 0.0


# ---------------------------------------------------------------------------
# compute_run_metrics -- mfe/mae and coverage
# ---------------------------------------------------------------------------

def test_full_coverage_with_mfe_mae() -> None:
    outcomes = _outcomes_full([(1.0, 2.0, -0.5), (2.0, 3.0, -1.0)])
    m = compute_run_metrics(outcomes)
    assert m["coverage_status"] == "full"
    assert abs(m["avg_mfe_r"] - 2.5) < 1e-6
    assert abs(m["avg_mae_r"] - (-0.75)) < 1e-6


def test_partial_coverage_without_mfe_mae() -> None:
    outcomes = _outcomes(1.0, 2.0)
    m = compute_run_metrics(outcomes)
    assert m["coverage_status"] == "partial"
    assert m["avg_mfe_r"] == 0.0
    assert m["avg_mae_r"] == 0.0


# ---------------------------------------------------------------------------
# compute_run_metrics -- sample_quality_score
# ---------------------------------------------------------------------------

def test_sample_quality_score_empty() -> None:
    m = compute_run_metrics([])
    assert m["sample_quality_score"] == 0.0


def test_sample_quality_score_high() -> None:
    # 10+ outcomes, all with mfe/mae, win_rate near 0.5
    records = [(0.5, 1.0, -0.3), (-0.3, 0.8, -0.5)] * 5
    outcomes = _outcomes_full(records)
    m = compute_run_metrics(outcomes)
    # count_score=1.0, completeness=1.0, balance~1.0 -> ~1.0
    assert m["sample_quality_score"] > 0.9


def test_sample_quality_score_low_count() -> None:
    outcomes = _outcomes_full([(1.0, 2.0, -0.5)])
    m = compute_run_metrics(outcomes)
    # count_score=0.1, completeness=1.0, balance=0.0 (win_rate=1.0)
    # (0.1 + 1.0 + 0.0) / 3 = 0.3667
    assert m["sample_quality_score"] < 0.5


# ---------------------------------------------------------------------------
# compute_run_metrics -- neutral returns
# ---------------------------------------------------------------------------

def test_neutral_count() -> None:
    outcomes = _outcomes(0.0, 0.0, 1.0, -1.0)
    m = compute_run_metrics(outcomes)
    assert m["neutral_count"] == 2


# ---------------------------------------------------------------------------
# compute_aggregate_metrics
# ---------------------------------------------------------------------------

def test_aggregate_empty() -> None:
    m = compute_aggregate_metrics([])
    assert m["run_count"] == 0
    assert m["candidate_count"] == 0
    assert m["coverage_status"] == "empty"


def test_aggregate_single_run() -> None:
    run = compute_run_metrics(_outcomes(1.0, -0.5, 2.0))
    agg = compute_aggregate_metrics([run])
    assert agg["run_count"] == 1
    assert agg["candidate_count"] == 3
    assert agg["win_count"] == 2
    assert agg["loss_count"] == 1


def test_aggregate_multiple_runs() -> None:
    run_a = compute_run_metrics(_outcomes(1.0, 2.0))
    run_b = compute_run_metrics(_outcomes(-1.0, 0.5))
    agg = compute_aggregate_metrics([run_a, run_b])
    assert agg["run_count"] == 2
    assert agg["candidate_count"] == 4
    assert agg["win_count"] == 3
    assert agg["loss_count"] == 1


def test_aggregate_drawdown_is_worst() -> None:
    run_a = compute_run_metrics(_outcomes(3.0, -2.0))
    run_b = compute_run_metrics(_outcomes(1.0, -6.0))
    agg = compute_aggregate_metrics([run_a, run_b])
    assert agg["max_drawdown_r"] == min(
        run_a["max_drawdown_r"], run_b["max_drawdown_r"]
    )


def test_aggregate_coverage_mixed() -> None:
    run_full = compute_run_metrics(_outcomes_full([(1.0, 2.0, -0.5)]))
    run_partial = compute_run_metrics(_outcomes(1.0))
    agg = compute_aggregate_metrics([run_full, run_partial])
    # has both full and partial -> partial
    assert agg["coverage_status"] == "partial"
