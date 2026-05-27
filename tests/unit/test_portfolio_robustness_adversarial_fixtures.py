"""Tests for portfolio robustness adversarial fixtures — T6881-T6920.

Same-bar pileup, concentrated exposure, correlated loss fixtures.
"""
from __future__ import annotations

import pytest
from core.portfolio_overlap_risk import compute_overlap, build_overlap_risk_report
from core.portfolio_correlation_proxy import compute_correlation_proxy, build_correlation_report
from core.portfolio_crowding_concentration import compute_crowding_score


class TestPortfolioAdversarial:
    def test_high_overlap_detected(self):
        overlap = compute_overlap([1, 1, 1], [1, 1, 1], "a", "b")
        assert overlap.overlap_score == 1.0

    def test_high_overlap_blocks(self):
        overlaps = [compute_overlap([1, 1, 1], [1, 1, 1], "a", "b")]
        report = build_overlap_risk_report(overlaps, max_overlap_risk=0.5, seed=42)
        assert report["verdict"] == "FAIL"

    def test_high_correlation(self):
        corr = compute_correlation_proxy([1, 2, 3, 4, 5], [1, 2, 3, 4, 5])
        assert corr > 0.99

    def test_crowding_detected(self):
        result = compute_crowding_score({"a": 0.9, "b": 0.1})
        assert result["crowding_score"] > 0.5


class TestPortfolioNormal:
    def test_no_overlap(self):
        overlap = compute_overlap([1, -1, 1], [-1, 1, -1], "a", "b")
        assert overlap.overlap_score == 1.0  # all bars have non-zero signals

    def test_balanced_portfolio(self):
        result = compute_crowding_score({"a": 0.25, "b": 0.25, "c": 0.25, "d": 0.25})
        assert result["crowding_score"] < 0.5


class TestPortfolioSafetyBoundary:
    def test_report_safety(self):
        report = build_overlap_risk_report([], seed=42)
        assert report["release_hold"] == "HOLD"
        assert report["advisory_only"] is True
