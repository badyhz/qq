"""Tests for bootstrap research report — T7441-T7480.

Worst percentile and stability tests.
"""
from __future__ import annotations

import pytest
from core.bootstrap_research_report import (
    compute_worst_case_percentile, compute_resampling_stability,
    build_bootstrap_report,
)


class TestBootstrapReportNormal:
    def test_worst_case_percentile(self):
        values = list(range(100))
        wc = compute_worst_case_percentile(values, 5.0)
        assert wc < 50

    def test_stability(self):
        values = [0.5] * 100
        result = compute_resampling_stability(values)
        assert result["stable"]

    def test_build_report(self):
        returns = [0.1, -0.05, 0.2, -0.1, 0.15]
        report = build_bootstrap_report(returns, n_iterations=50, seed=42)
        assert report["verdict"] in ("PASS", "FAIL")


class TestBootstrapReportEdge:
    def test_empty_returns(self):
        report = build_bootstrap_report([], seed=42)
        assert report["verdict"] == "FAIL"


class TestBootstrapReportAdversarial:
    def test_unstable(self):
        values = [0.0, 1.0, 0.0, 1.0, 0.0, 1.0]
        result = compute_resampling_stability(values)
        assert not result["stable"]


class TestBootstrapReportSafetyBoundary:
    def test_report_safety(self):
        report = build_bootstrap_report([0.1], seed=42)
        assert report["release_hold"] == "HOLD"
        assert report["advisory_only"] is True
