"""Tests for portfolio degradation and drawdown — T6841-T6880.

Degradation, drawdown, missing data tests.
"""
from __future__ import annotations

import pytest
from core.portfolio_degradation_drawdown import (
    compute_drawdown_proxy, compute_portfolio_degradation,
    build_portfolio_robustness_report,
)


class TestDrawdownNormal:
    def test_no_drawdown(self):
        r = compute_drawdown_proxy([100, 101, 102, 103])
        assert r["max_drawdown"] == 0.0

    def test_drawdown(self):
        r = compute_drawdown_proxy([100, 110, 90, 95])
        assert r["max_drawdown"] == 20.0


class TestDrawdownEdge:
    def test_empty_equity(self):
        r = compute_drawdown_proxy([])
        assert r["max_drawdown"] == 0.0


class TestDegradationNormal:
    def test_no_degradation(self):
        r = compute_portfolio_degradation(0.5, 0.5)
        assert not r["degradation_detected"]

    def test_degradation_detected(self):
        r = compute_portfolio_degradation(0.5, 0.1)
        assert r["degradation_detected"]


class TestDrawdownSafetyBoundary:
    def test_report_safety(self):
        report = build_portfolio_robustness_report({}, {}, seed=42)
        assert report["release_hold"] == "HOLD"
        assert report["advisory_only"] is True
