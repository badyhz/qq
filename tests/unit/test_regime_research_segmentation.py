"""Tests for regime research segmentation — T7521-T7560.

Trend, chop, volatile, ambiguous tests.
"""
from __future__ import annotations

import pytest
from core.regime_research_segmentation import classify_regime, segment_by_regime, build_regime_breakdown


class TestRegimeSegmentationNormal:
    def test_classify_trend(self):
        # Strong upward trend
        returns = [0.01] * 20
        regime = classify_regime(returns, lookback=10)
        assert regime == "TREND"

    def test_classify_chop(self):
        # Low volatility, no direction
        returns = [0.0001, -0.0001] * 20
        regime = classify_regime(returns, lookback=10)
        assert regime == "CHOP"

    def test_build_breakdown(self):
        returns = [0.01] * 30
        report = build_regime_breakdown("strat1", returns, seed=42)
        assert "regime_scores" in report


class TestRegimeSegmentationEdge:
    def test_short_returns(self):
        regime = classify_regime([0.01], lookback=20)
        assert regime == "AMBIGUOUS"


class TestRegimeSegmentationDeterministic:
    def test_deterministic(self):
        returns = [0.01, -0.01, 0.02, -0.02] * 10
        r1 = build_regime_breakdown("s", returns, seed=42)
        r2 = build_regime_breakdown("s", returns, seed=42)
        r1_copy = {k: v for k, v in r1.items() if k != "generated_at"}
        r2_copy = {k: v for k, v in r2.items() if k != "generated_at"}
        assert r1_copy == r2_copy


class TestRegimeSegmentationSafetyBoundary:
    def test_report_safety(self):
        report = build_regime_breakdown("s", [], seed=42)
        assert report["release_hold"] == "HOLD"
        assert report["advisory_only"] is True
