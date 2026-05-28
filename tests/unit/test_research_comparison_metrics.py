"""Tests for research comparison metrics extraction.

Program B tests. Offline only. No network.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.research_bundle_series import load_bundle_series
from core.research_comparison_metrics import (
    build_extracted_metrics_json,
    extract_metrics,
    extract_metrics_from_records,
    metrics_to_dict,
)

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "research_comparison_analytics"


class TestMetricExtraction:
    """Test metric extraction from bundles."""

    def test_extract_from_quality_bundle(self):
        """Test metric extraction from quality gate bundle."""
        bundles = [
            ("baseline", FIXTURES / "quality_gate_baseline"),
            ("candidate", FIXTURES / "quality_gate_candidate_changed"),
        ]
        records = load_bundle_series(bundles)
        metrics = extract_metrics_from_records(records)
        assert len(metrics) == 2

    def test_extract_from_artifact_browser(self):
        """Test metric extraction from artifact browser bundle."""
        bundles = [
            ("baseline", FIXTURES / "artifact_browser_baseline"),
            ("candidate", FIXTURES / "artifact_browser_candidate_improved"),
        ]
        records = load_bundle_series(bundles)
        metrics = extract_metrics_from_records(records)
        assert len(metrics) == 2

    def test_metric_shape(self):
        """Test extracted metrics have expected fields."""
        bundles = [
            ("baseline", FIXTURES / "artifact_browser_baseline"),
            ("candidate", FIXTURES / "artifact_browser_candidate_improved"),
        ]
        records = load_bundle_series(bundles)
        m = extract_metrics(records[0])
        assert hasattr(m, "verdict")
        assert hasattr(m, "composite_score")
        assert hasattr(m, "evidence_completeness")
        assert hasattr(m, "stability_score")
        assert hasattr(m, "parameter_fragility")
        assert hasattr(m, "overlap_risk")
        assert hasattr(m, "negative_control_margin")
        assert hasattr(m, "bootstrap_ci_width")
        assert hasattr(m, "bootstrap_worst_case")
        assert hasattr(m, "regime_concentration_warning_count")
        assert hasattr(m, "portfolio_crowding_score")
        assert hasattr(m, "blocker_count")
        assert hasattr(m, "warning_count")
        assert hasattr(m, "release_hold")
        assert hasattr(m, "advisory_only")
        assert hasattr(m, "human_review_required")
        assert hasattr(m, "no_network")
        assert hasattr(m, "quality_gate_version")
        assert hasattr(m, "deterministic_seed")

    def test_safety_flags_correct(self):
        """Test safety flags are correctly extracted."""
        bundles = [
            ("baseline", FIXTURES / "artifact_browser_baseline"),
            ("candidate", FIXTURES / "artifact_browser_candidate_improved"),
        ]
        records = load_bundle_series(bundles)
        for m in extract_metrics_from_records(records):
            assert m.release_hold == "HOLD"
            assert m.advisory_only is True
            assert m.human_review_required is True
            assert m.no_network is True

    def test_metrics_to_dict(self):
        """Test metrics serialization."""
        bundles = [
            ("baseline", FIXTURES / "artifact_browser_baseline"),
            ("candidate", FIXTURES / "artifact_browser_candidate_improved"),
        ]
        records = load_bundle_series(bundles)
        m = extract_metrics(records[0])
        d = metrics_to_dict(m)
        assert isinstance(d, dict)
        assert "composite_score" in d
        assert "release_hold" in d

    def test_build_extracted_metrics_json(self):
        """Test extracted_metrics.json shape."""
        bundles = [
            ("baseline", FIXTURES / "artifact_browser_baseline"),
            ("candidate", FIXTURES / "artifact_browser_candidate_improved"),
        ]
        records = load_bundle_series(bundles)
        metrics = extract_metrics_from_records(records)
        data = build_extracted_metrics_json(metrics)
        assert data["bundle_count"] == 2
        assert len(data["metrics"]) == 2
        assert data["schema_version"] == "1.0.0"

    def test_improved_bundle_higher_score(self):
        """Test improved bundle has higher composite score."""
        bundles = [
            ("baseline", FIXTURES / "artifact_browser_baseline"),
            ("improved", FIXTURES / "artifact_browser_candidate_improved"),
        ]
        records = load_bundle_series(bundles)
        metrics = extract_metrics_from_records(records)
        baseline = [m for m in metrics if m.label == "baseline"][0]
        improved = [m for m in metrics if m.label == "improved"][0]
        assert improved.composite_score > baseline.composite_score

    def test_regressed_bundle_lower_score(self):
        """Test regressed bundle has lower composite score."""
        bundles = [
            ("baseline", FIXTURES / "artifact_browser_baseline"),
            ("regressed", FIXTURES / "artifact_browser_candidate_regressed"),
        ]
        records = load_bundle_series(bundles)
        metrics = extract_metrics_from_records(records)
        baseline = [m for m in metrics if m.label == "baseline"][0]
        regressed = [m for m in metrics if m.label == "regressed"][0]
        assert regressed.composite_score < baseline.composite_score
