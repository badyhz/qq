"""Tests for bootstrap confidence intervals — T7401-T7440.

Normal, skewed, sparse tests.
"""
from __future__ import annotations

import pytest
from core.bootstrap_confidence_intervals import (
    compute_confidence_intervals, compute_win_rate_ci,
    compute_expectancy_ci, build_bootstrap_confidence_report,
)


class TestConfidenceIntervalsNormal:
    def test_ci_basic(self):
        values = list(range(100))
        ci = compute_confidence_intervals(values)
        assert ci["lower"] < ci["upper"]
        assert ci["confidence_level"] == 0.95

    def test_win_rate_ci(self):
        returns = [0.1, -0.05, 0.2, -0.1, 0.15]
        ci = compute_win_rate_ci(returns, n_iterations=50, seed=42)
        assert "win_rate" in ci
        assert ci["ci_lower"] <= ci["win_rate"] <= ci["ci_upper"]


class TestConfidenceIntervalsEdge:
    def test_empty_values(self):
        ci = compute_confidence_intervals([])
        assert ci["lower"] == 0.0
        assert ci["upper"] == 0.0


class TestConfidenceIntervalsDeterministic:
    def test_deterministic(self):
        ci1 = compute_win_rate_ci([0.1, -0.05, 0.2], n_iterations=50, seed=42)
        ci2 = compute_win_rate_ci([0.1, -0.05, 0.2], n_iterations=50, seed=42)
        assert ci1["ci_lower"] == ci2["ci_lower"]

    def test_build_report_safety(self):
        report = build_bootstrap_confidence_report([0.1, -0.05], n_iterations=50, seed=42)
        assert report["release_hold"] == "HOLD"
        assert report["advisory_only"] is True
