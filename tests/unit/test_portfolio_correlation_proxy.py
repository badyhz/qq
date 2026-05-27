"""Tests for portfolio correlation proxy — T6681-T6720.

Uncorrelated, correlated, sparse fixtures.
"""
from __future__ import annotations

import pytest
from core.portfolio_correlation_proxy import (
    compute_correlation_proxy, compute_correlation_matrix, build_correlation_report,
)


class TestCorrelationProxyNormal:
    def test_perfect_correlation(self):
        c = compute_correlation_proxy([1, 2, 3, 4, 5], [1, 2, 3, 4, 5])
        assert c > 0.99

    def test_negative_correlation(self):
        c = compute_correlation_proxy([1, 2, 3, 4, 5], [5, 4, 3, 2, 1])
        assert c < -0.99

    def test_build_report(self):
        report = build_correlation_report({"a": [1, 2, 3], "b": [3, 2, 1]}, seed=42)
        assert report["verdict"] == "PASS"


class TestCorrelationProxyEdge:
    def test_empty_returns(self):
        c = compute_correlation_proxy([], [])
        assert c == 0.0

    def test_single_value(self):
        c = compute_correlation_proxy([1], [2])
        assert c == 0.0
