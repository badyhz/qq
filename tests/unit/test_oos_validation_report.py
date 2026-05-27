"""Tests for OOS validation report — T5721-T5750.

Stable, unstable, sparse OOS tests.
"""
from __future__ import annotations

import pytest
from core.oos_validation_report import compute_oos_split_metrics, build_oos_validation_report


class TestOOSValidationNormal:
    def test_stable_oos(self):
        data = [{"split_id": "s1", "strategy_id": "str", "symbol": "BTC", "timeframe": "5m",
                 "train_score": 0.5, "test_score": 0.48}]
        metrics = compute_oos_split_metrics(data, min_stability=0.5)
        assert metrics[0].stable

    def test_build_report(self):
        from core.oos_validation_report import OOSSplitMetric
        metrics = (OOSSplitMetric("s1", "str", "BTC", "5m", 0.5, 0.48, 0.04, True, ""),)
        report = build_oos_validation_report(metrics, seed=42)
        assert report["verdict"] == "PASS"


class TestOOSValidationEdge:
    def test_empty_results(self):
        metrics = compute_oos_split_metrics([])
        assert metrics == ()


class TestOOSValidationAdversarial:
    def test_unstable_oos(self):
        data = [{"split_id": "s1", "strategy_id": "str", "symbol": "BTC", "timeframe": "5m",
                 "train_score": 0.5, "test_score": 0.1}]
        metrics = compute_oos_split_metrics(data, min_stability=0.5)
        assert not metrics[0].stable


class TestOOSValidationSafetyBoundary:
    def test_report_safety(self):
        report = build_oos_validation_report((), seed=42)
        assert report["release_hold"] == "HOLD"
        assert report["advisory_only"] is True
        assert report["human_review_required"] is True
