"""Tests for core/offline_shadow_comparison.py -- 15+ tests."""
from __future__ import annotations

import pytest

from core.offline_shadow_comparison import compare_experiments


def _result(
    experiment_id: str = "exp",
    runs: list[dict] | None = None,
    verdict: str | None = None,
) -> dict:
    """Build a minimal experiment result dict."""
    d: dict = {
        "experiment_id": experiment_id,
        "run_count": len(runs) if runs else 0,
        "runs": runs or [],
    }
    if verdict is not None:
        d["verdict"] = verdict
    return d


def _run(run_id: str, expectancy: float, drawdown: float = -1.0,
         candidates: int = 10, quality: float = 0.5,
         win_count: int = 6, loss_count: int = 4) -> dict:
    return {
        "run_id": run_id,
        "outcome_count": candidates,
        "metrics": {
            "candidate_count": candidates,
            "win_count": win_count,
            "loss_count": loss_count,
            "neutral_count": 0,
            "win_rate": win_count / candidates if candidates else 0,
            "avg_return_r": expectancy,
            "expectancy_r": expectancy,
            "max_drawdown_r": drawdown,
            "avg_mfe_r": 1.0,
            "avg_mae_r": -0.5,
            "profit_factor": 2.0,
            "sample_quality_score": quality,
            "coverage_status": "full",
        },
    }


# ---------------------------------------------------------------------------
# basic delta computation
# ---------------------------------------------------------------------------

def test_expectancy_improvement() -> None:
    a = _result("a", [_run("r1", expectancy=0.2)])
    b = _result("b", [_run("r1", expectancy=0.5)])
    c = compare_experiments(a, b)
    assert c["deltas"]["expectancy_r"] > 0
    assert c["directions"]["expectancy_improved"] is True
    assert c["directions"]["expectancy_deteriorated"] is False


def test_expectancy_deterioration() -> None:
    a = _result("a", [_run("r1", expectancy=0.5)])
    b = _result("b", [_run("r1", expectancy=0.1)])
    c = compare_experiments(a, b)
    assert c["deltas"]["expectancy_r"] < 0
    assert c["directions"]["expectancy_deteriorated"] is True


def test_drawdown_improvement() -> None:
    """Less negative drawdown = improvement."""
    a = _result("a", [_run("r1", expectancy=0.3, drawdown=-5.0)])
    b = _result("b", [_run("r1", expectancy=0.3, drawdown=-2.0)])
    c = compare_experiments(a, b)
    assert c["deltas"]["max_drawdown_r"] > 0  # -2 - (-5) = +3
    assert c["directions"]["drawdown_improved"] is True


def test_drawdown_deterioration() -> None:
    a = _result("a", [_run("r1", expectancy=0.3, drawdown=-2.0)])
    b = _result("b", [_run("r1", expectancy=0.3, drawdown=-8.0)])
    c = compare_experiments(a, b)
    assert c["deltas"]["max_drawdown_r"] < 0
    assert c["directions"]["drawdown_deteriorated"] is True


# ---------------------------------------------------------------------------
# sample count and quality
# ---------------------------------------------------------------------------

def test_sample_count_delta() -> None:
    a = _result("a", [_run("r1", expectancy=0.2, candidates=10)])
    b = _result("b", [_run("r1", expectancy=0.2, candidates=25)])
    c = compare_experiments(a, b)
    assert c["deltas"]["sample_count"] == 15


def test_quality_score_delta() -> None:
    a = _result("a", [_run("r1", expectancy=0.2, quality=0.3)])
    b = _result("b", [_run("r1", expectancy=0.2, quality=0.8)])
    c = compare_experiments(a, b)
    assert c["deltas"]["sample_quality_score"] > 0


# ---------------------------------------------------------------------------
# gate status changes
# ---------------------------------------------------------------------------

def test_gate_status_change_detected() -> None:
    a = _result("a", [_run("r1", expectancy=0.2)], verdict="PASS")
    b = _result("b", [_run("r1", expectancy=-0.1)], verdict="REJECT")
    c = compare_experiments(a, b)
    assert c["gate_changed"] is True
    assert c["gate_status_a"] == "PASS"
    assert c["gate_status_b"] == "REJECT"


def test_gate_status_unchanged() -> None:
    a = _result("a", [_run("r1", expectancy=0.2)], verdict="PASS")
    b = _result("b", [_run("r1", expectancy=0.3)], verdict="PASS")
    c = compare_experiments(a, b)
    assert c["gate_changed"] is False


# ---------------------------------------------------------------------------
# rank changes
# ---------------------------------------------------------------------------

def test_rank_change_detected() -> None:
    a = _result("a", [
        _run("x", expectancy=0.5),
        _run("y", expectancy=0.1),
    ])
    b = _result("b", [
        _run("x", expectancy=0.1),
        _run("y", expectancy=0.5),
    ])
    c = compare_experiments(a, b)
    assert len(c["rank_changes"]) > 0
    change = c["rank_changes"][0]
    assert change["direction"] in ("improved", "deteriorated")


def test_no_rank_change_when_same() -> None:
    a = _result("a", [_run("x", expectancy=0.5), _run("y", expectancy=0.1)])
    b = _result("b", [_run("x", expectancy=0.6), _run("y", expectancy=0.2)])
    c = compare_experiments(a, b)
    assert len(c["rank_changes"]) == 0


# ---------------------------------------------------------------------------
# overall improved flag
# ---------------------------------------------------------------------------

def test_improved_true_when_expectancy_up_no_regression() -> None:
    a = _result("a", [_run("r1", expectancy=0.2, drawdown=-2.0)], verdict="WATCH")
    b = _result("b", [_run("r1", expectancy=0.5, drawdown=-1.0)], verdict="PASS")
    c = compare_experiments(a, b)
    assert c["improved"] is True


def test_improved_false_when_pass_to_reject() -> None:
    """Even if expectancy goes up, PASS->REJECT gate flip = not improved."""
    a = _result("a", [_run("r1", expectancy=0.2)], verdict="PASS")
    b = _result("b", [_run("r1", expectancy=0.3)], verdict="REJECT")
    c = compare_experiments(a, b)
    assert c["improved"] is False


def test_improved_false_when_drawdown_deteriorates() -> None:
    a = _result("a", [_run("r1", expectancy=0.2, drawdown=-1.0)])
    b = _result("b", [_run("r1", expectancy=0.3, drawdown=-8.0)])
    c = compare_experiments(a, b)
    assert c["improved"] is False


# ---------------------------------------------------------------------------
# empty / edge cases
# ---------------------------------------------------------------------------

def test_both_empty() -> None:
    a = _result("a")
    b = _result("b")
    c = compare_experiments(a, b)
    assert c["improved"] is False
    assert c["deltas"]["expectancy_r"] == 0.0


def test_experiment_ids_preserved() -> None:
    a = _result("baseline-v1", [_run("r1", expectancy=0.2)])
    b = _result("candidate-v2", [_run("r1", expectancy=0.5)])
    c = compare_experiments(a, b)
    assert c["baseline_experiment_id"] == "baseline-v1"
    assert c["candidate_experiment_id"] == "candidate-v2"
