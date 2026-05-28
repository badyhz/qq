"""Tests for research trend engine.

Program D tests. Offline only. No network.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from core.research_bundle_series import load_bundle_series
from core.research_comparison_metrics import extract_metrics_from_records
from core.research_trend_engine import (
    compute_trend_report,
    trend_report_to_dict,
)

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "research_comparison_analytics"


class TestTrendEngine:
    """Test multi-run trend engine."""

    def test_trend_with_three_bundles(self):
        """Test trend computation with 3 bundles."""
        bundles = [
            ("run1", FIXTURES / "quality_gate_series_three_runs" / "run1"),
            ("run2", FIXTURES / "quality_gate_series_three_runs" / "run2"),
            ("run3", FIXTURES / "quality_gate_series_three_runs" / "run3"),
        ]
        records = load_bundle_series(bundles)
        metrics = extract_metrics_from_records(records)
        report = compute_trend_report(metrics)
        assert report.bundle_count == 3
        assert len(report.labels) == 3
        assert len(report.metric_trends) > 0

    def test_monotonic_improvement_detected(self):
        """Test monotonic improvement detection."""
        bundles = [
            ("run1", FIXTURES / "quality_gate_series_three_runs" / "run1"),
            ("run2", FIXTURES / "quality_gate_series_three_runs" / "run2"),
            ("run3", FIXTURES / "quality_gate_series_three_runs" / "run3"),
        ]
        records = load_bundle_series(bundles)
        metrics = extract_metrics_from_records(records)
        report = compute_trend_report(metrics)
        # composite_score should show improvement trend
        score_trend = [t for t in report.metric_trends if t.metric == "composite_score"]
        if score_trend:
            assert score_trend[0].trend_type == "monotonic_improvement"

    def test_trend_rejects_two_bundles(self):
        """Test trend engine rejects < 3 bundles."""
        bundles = [
            ("a", FIXTURES / "artifact_browser_baseline"),
            ("b", FIXTURES / "artifact_browser_candidate_improved"),
        ]
        records = load_bundle_series(bundles)
        metrics = extract_metrics_from_records(records)
        with pytest.raises(ValueError, match="at least 3"):
            compute_trend_report(metrics)

    def test_trend_report_to_dict(self):
        """Test trend report serialization."""
        bundles = [
            ("run1", FIXTURES / "quality_gate_series_three_runs" / "run1"),
            ("run2", FIXTURES / "quality_gate_series_three_runs" / "run2"),
            ("run3", FIXTURES / "quality_gate_series_three_runs" / "run3"),
        ]
        records = load_bundle_series(bundles)
        metrics = extract_metrics_from_records(records)
        report = compute_trend_report(metrics)
        d = trend_report_to_dict(report)
        assert "metric_trends" in d
        assert "detections" in d
        assert "overall_trend" in d

    def test_trend_deterministic(self):
        """Test trend report is deterministic across reruns."""
        bundles = [
            ("run1", FIXTURES / "quality_gate_series_three_runs" / "run1"),
            ("run2", FIXTURES / "quality_gate_series_three_runs" / "run2"),
            ("run3", FIXTURES / "quality_gate_series_three_runs" / "run3"),
        ]
        records = load_bundle_series(bundles)
        metrics = extract_metrics_from_records(records)
        report1 = compute_trend_report(metrics)
        report2 = compute_trend_report(metrics)
        assert trend_report_to_dict(report1) == trend_report_to_dict(report2)

    def test_trend_detects_fragment_regression(self):
        """Test trend detects parameter fragility improvement (lower is better)."""
        bundles = [
            ("run1", FIXTURES / "quality_gate_series_three_runs" / "run1"),
            ("run2", FIXTURES / "quality_gate_series_three_runs" / "run2"),
            ("run3", FIXTURES / "quality_gate_series_three_runs" / "run3"),
        ]
        records = load_bundle_series(bundles)
        metrics = extract_metrics_from_records(records)
        report = compute_trend_report(metrics)
        frag_trend = [t for t in report.metric_trends if t.metric == "parameter_fragility"]
        if frag_trend:
            # Fragility decreases across runs, should be improvement
            assert frag_trend[0].trend_type == "monotonic_improvement"

    def test_overall_trend(self):
        """Test overall trend classification."""
        bundles = [
            ("run1", FIXTURES / "quality_gate_series_three_runs" / "run1"),
            ("run2", FIXTURES / "quality_gate_series_three_runs" / "run2"),
            ("run3", FIXTURES / "quality_gate_series_three_runs" / "run3"),
        ]
        records = load_bundle_series(bundles)
        metrics = extract_metrics_from_records(records)
        report = compute_trend_report(metrics)
        assert report.overall_trend in ("improving", "regressing", "stable", "mixed")
