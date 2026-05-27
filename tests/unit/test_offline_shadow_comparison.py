"""Tests for core/offline_shadow_comparison.py -- 10+ tests."""
from __future__ import annotations

import pytest

from core.offline_shadow_comparison import ComparisonResult, compare_experiments


def _result(experiment_id: str, **metrics: float) -> dict:
    """Build a minimal experiment result dict with flat metrics."""
    d: dict = {"experiment_id": experiment_id}
    d.update(metrics)
    return d


# ---------------------------------------------------------------------------
# empty / basic
# ---------------------------------------------------------------------------


def test_empty_list() -> None:
    c = compare_experiments([])
    assert c.experiment_ids == ()
    assert c.rows == ()
    assert c.best_by_metric == {}


def test_single_experiment() -> None:
    r = _result("exp_001", expectancy_r=0.5, win_rate=0.6)
    c = compare_experiments([r])
    assert c.experiment_ids == ("exp_001",)
    assert c.best_by_metric["expectancy_r"] == "exp_001"


def test_two_experiments_best_selected() -> None:
    a = _result("a", expectancy_r=0.2, win_rate=0.5)
    b = _result("b", expectancy_r=0.8, win_rate=0.4)
    c = compare_experiments([a, b])
    assert c.best_by_metric["expectancy_r"] == "b"
    assert c.best_by_metric["win_rate"] == "a"


# ---------------------------------------------------------------------------
# metric keys present
# ---------------------------------------------------------------------------


def test_metric_keys_covered() -> None:
    a = _result("a", expectancy_r=0.1, win_rate=0.5, avg_return_r=0.1,
                max_drawdown_r=-2.0, sample_quality_score=0.7, profit_factor=1.5)
    c = compare_experiments([a])
    expected_keys = {
        "expectancy_r", "win_rate", "avg_return_r",
        "max_drawdown_r", "sample_quality_score", "profit_factor",
    }
    assert set(c.metrics_compared) == expected_keys


# ---------------------------------------------------------------------------
# rows generated correctly
# ---------------------------------------------------------------------------


def test_rows_count_matches() -> None:
    a = _result("a", expectancy_r=0.2)
    b = _result("b", expectancy_r=0.5)
    c = compare_experiments([a, b])
    # 2 experiments x 6 metric keys = 12 rows
    assert len(c.rows) == 12


def test_row_values_correct() -> None:
    a = _result("a", expectancy_r=0.25)
    c = compare_experiments([a])
    expectancy_rows = [r for r in c.rows if r.metric_name == "expectancy_r"]
    assert len(expectancy_rows) == 1
    assert expectancy_rows[0].value == 0.25
    assert expectancy_rows[0].experiment_id == "a"


# ---------------------------------------------------------------------------
# best_by_metric with multiple experiments
# ---------------------------------------------------------------------------


def test_best_by_metric_three_experiments() -> None:
    a = _result("a", expectancy_r=0.1, max_drawdown_r=-5.0)
    b = _result("b", expectancy_r=0.5, max_drawdown_r=-2.0)
    c_result = _result("c", expectancy_r=0.3, max_drawdown_r=-1.0)
    c = compare_experiments([a, b, c_result])
    assert c.best_by_metric["expectancy_r"] == "b"
    assert c.best_by_metric["max_drawdown_r"] == "c"  # -1.0 > -2.0 > -5.0


# ---------------------------------------------------------------------------
# missing metrics default to 0
# ---------------------------------------------------------------------------


def test_missing_metric_defaults_to_zero() -> None:
    a = _result("a")  # no metrics
    b = _result("b", expectancy_r=0.5)
    c = compare_experiments([a, b])
    assert c.best_by_metric["expectancy_r"] == "b"


# ---------------------------------------------------------------------------
# immutability
# ---------------------------------------------------------------------------


def test_comparison_result_frozen() -> None:
    a = _result("a", expectancy_r=0.2)
    c = compare_experiments([a])
    with pytest.raises(AttributeError):
        c.experiment_ids = ("x",)  # type: ignore[misc]


# ---------------------------------------------------------------------------
# experiment ids preserved
# ---------------------------------------------------------------------------


def test_experiment_ids_preserved_in_order() -> None:
    a = _result("baseline-v1", expectancy_r=0.2)
    b = _result("candidate-v2", expectancy_r=0.5)
    c = compare_experiments([a, b])
    assert c.experiment_ids == ("baseline-v1", "candidate-v2")
