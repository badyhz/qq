"""Tests for core/offline_shadow_scorecard.py -- 12+ tests."""
from __future__ import annotations

import pytest

from core.offline_shadow_scorecard import grade_experiment, grade_run


def _metrics(**overrides) -> dict:
    """Build a metrics dict with sensible defaults, overriding given keys."""
    base = {
        "candidate_count": 10,
        "win_count": 6,
        "loss_count": 4,
        "neutral_count": 0,
        "win_rate": 0.6,
        "avg_return_r": 0.5,
        "expectancy_r": 0.3,
        "max_drawdown_r": -2.0,
        "avg_mfe_r": 1.5,
        "avg_mae_r": -0.8,
        "profit_factor": 2.0,
        "sample_quality_score": 0.6,
        "coverage_status": "full",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# grade_run -- PASS
# ---------------------------------------------------------------------------

def test_pass_all_gates_met() -> None:
    m = _metrics()
    g = grade_run(m)
    assert g["grade"] == "PASS"
    assert g["blockers"] == []


def test_pass_boundary_candidate_count() -> None:
    m = _metrics(candidate_count=5, sample_quality_score=0.3, expectancy_r=0.01)
    g = grade_run(m)
    # candidate_count meets gate, quality meets gate, expectancy>0 -> PASS
    assert g["grade"] == "PASS"


# ---------------------------------------------------------------------------
# grade_run -- REJECT (hard gates)
# ---------------------------------------------------------------------------

def test_reject_insufficient_candidates() -> None:
    m = _metrics(candidate_count=3)
    g = grade_run(m)
    assert g["grade"] == "REJECT"
    assert "insufficient_candidates" in g["blockers"]


def test_reject_drawdown_exceeded() -> None:
    m = _metrics(max_drawdown_r=-10.0)
    g = grade_run(m)
    assert g["grade"] == "REJECT"
    assert "drawdown_exceeded" in g["blockers"]


def test_reject_multiple_blockers() -> None:
    m = _metrics(candidate_count=1, max_drawdown_r=-20.0)
    g = grade_run(m)
    assert g["grade"] == "REJECT"
    assert "insufficient_candidates" in g["blockers"]
    assert "drawdown_exceeded" in g["blockers"]
    assert len(g["blockers"]) == 2


# ---------------------------------------------------------------------------
# grade_run -- WATCH (soft gates)
# ---------------------------------------------------------------------------

def test_watch_low_sample_quality() -> None:
    m = _metrics(sample_quality_score=0.1, expectancy_r=0.5)
    g = grade_run(m)
    assert g["grade"] == "WATCH"
    assert any("low_sample_quality" in r for r in g["reason_codes"])


def test_watch_non_positive_expectancy() -> None:
    m = _metrics(expectancy_r=-0.1, sample_quality_score=0.5)
    g = grade_run(m)
    assert g["grade"] == "WATCH"
    assert any("non_positive_expectancy" in r for r in g["reason_codes"])


def test_watch_zero_expectancy() -> None:
    m = _metrics(expectancy_r=0.0, sample_quality_score=0.5)
    g = grade_run(m)
    assert g["grade"] == "WATCH"


# ---------------------------------------------------------------------------
# grade_run -- reason_codes content
# ---------------------------------------------------------------------------

def test_reason_codes_include_candidate_count() -> None:
    m = _metrics(candidate_count=2)
    g = grade_run(m)
    assert any("candidate_count=2" in r for r in g["reason_codes"])


def test_reason_codes_include_drawdown_value() -> None:
    m = _metrics(max_drawdown_r=-8.0)
    g = grade_run(m)
    assert any("-8.0" in r or "max_drawdown_r" in r for r in g["reason_codes"])


# ---------------------------------------------------------------------------
# grade_run -- custom gates
# ---------------------------------------------------------------------------

def test_custom_gate_strict_candidate_count() -> None:
    m = _metrics(candidate_count=8)
    g = grade_run(m, gates={"min_candidate_count": 10})
    assert g["grade"] == "REJECT"
    assert "insufficient_candidates" in g["blockers"]


# ---------------------------------------------------------------------------
# grade_experiment
# ---------------------------------------------------------------------------

def test_grade_experiment_all_pass() -> None:
    results = {
        "experiment_id": "e1",
        "runs": [
            {"run_id": "r1", "metrics": _metrics()},
            {"run_id": "r2", "metrics": _metrics()},
        ],
    }
    scorecard = grade_experiment(results)
    assert scorecard["verdict"] == "PASS"
    assert scorecard["pass_count"] == 2
    assert scorecard["reject_count"] == 0


def test_grade_experiment_one_reject_taints() -> None:
    results = {
        "experiment_id": "e2",
        "runs": [
            {"run_id": "good", "metrics": _metrics()},
            {"run_id": "bad", "metrics": _metrics(candidate_count=1)},
        ],
    }
    scorecard = grade_experiment(results)
    assert scorecard["verdict"] == "REJECT"
    assert scorecard["reject_count"] == 1
    assert scorecard["pass_count"] == 1


def test_grade_experiment_watch_only() -> None:
    results = {
        "experiment_id": "e3",
        "runs": [
            {"run_id": "w1", "metrics": _metrics(expectancy_r=-0.01, sample_quality_score=0.5)},
        ],
    }
    scorecard = grade_experiment(results)
    assert scorecard["verdict"] == "WATCH"


def test_grade_experiment_empty_runs() -> None:
    results = {"experiment_id": "e4", "runs": []}
    scorecard = grade_experiment(results)
    assert scorecard["verdict"] == "WATCH"
    assert scorecard["pass_count"] == 0


def test_grade_experiment_preserves_run_ids() -> None:
    results = {
        "experiment_id": "e5",
        "runs": [
            {"run_id": "alpha", "metrics": _metrics()},
        ],
    }
    scorecard = grade_experiment(results)
    assert scorecard["run_grades"][0]["run_id"] == "alpha"
