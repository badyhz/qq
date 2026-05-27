"""Tests for strategy robustness lab — T6321-T6360.

Normal, sparse, adverse fixtures.
"""
from __future__ import annotations

import pytest
from core.strategy_robustness_lab import assess_strategy_robustness, build_strategy_robustness_report


class TestStrategyRobustnessNormal:
    def test_robust_strategy(self):
        results = [{"score": 0.5, "trade_count": 20}] * 5
        r = assess_strategy_robustness("strat1", results)
        assert r.is_robust

    def test_build_report(self):
        results = [{"score": 0.5, "trade_count": 20}] * 5
        r = assess_strategy_robustness("strat1", results)
        report = build_strategy_robustness_report([r], seed=42)
        assert report["verdict"] == "PASS"


class TestStrategyRobustnessEdge:
    def test_no_results(self):
        r = assess_strategy_robustness("strat1", [])
        assert not r.is_robust


class TestStrategyRobustnessAdversarial:
    def test_low_trades(self):
        results = [{"score": 0.5, "trade_count": 1}]
        r = assess_strategy_robustness("strat1", results, min_trades=10)
        assert not r.is_robust

    def test_low_score(self):
        results = [{"score": -0.1, "trade_count": 20}]
        r = assess_strategy_robustness("strat1", results, min_score=0.0)
        assert not r.is_robust


class TestStrategyRobustnessSafetyBoundary:
    def test_report_safety(self):
        report = build_strategy_robustness_report([], seed=42)
        assert report["release_hold"] == "HOLD"
        assert report["advisory_only"] is True
