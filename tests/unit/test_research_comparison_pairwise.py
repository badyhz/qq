"""Tests for research comparison pairwise engine.

Program C tests. Offline only. No network.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from core.research_bundle_series import load_bundle_series
from core.research_comparison_metrics import extract_metrics_from_records
from core.research_comparison_pairwise import (
    build_pairwise_comparison_json,
    compare_all_pairs,
    compare_pairwise,
    pairwise_to_dict,
)

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "research_comparison_analytics"


class TestPairwiseComparison:
    """Test pairwise comparison."""

    def test_identical_bundles_stable(self):
        """Test identical bundles compare as STABLE."""
        bundles = [
            ("a", FIXTURES / "artifact_browser_baseline"),
            ("b", FIXTURES / "artifact_browser_baseline"),
        ]
        records = load_bundle_series(bundles)
        metrics = extract_metrics_from_records(records)
        comp = compare_pairwise(metrics[0], metrics[1], records[0], records[1])
        assert comp.overall_classification == "STABLE"
        assert comp.composite_score_delta == 0.0
        assert comp.blocker_change == 0
        assert comp.warning_change == 0
        assert not comp.safety_fail

    def test_changed_score_regression(self):
        """Test changed score classifies as REGRESSED or IMPROVED."""
        bundles = [
            ("baseline", FIXTURES / "artifact_browser_baseline"),
            ("regressed", FIXTURES / "artifact_browser_candidate_regressed"),
        ]
        records = load_bundle_series(bundles)
        metrics = extract_metrics_from_records(records)
        comp = compare_pairwise(metrics[0], metrics[1], records[0], records[1])
        assert comp.overall_classification in ("REGRESSED", "MIXED")
        assert comp.composite_score_delta < 0

    def test_improved_score(self):
        """Test improved score classifies as IMPROVED."""
        bundles = [
            ("baseline", FIXTURES / "artifact_browser_baseline"),
            ("improved", FIXTURES / "artifact_browser_candidate_improved"),
        ]
        records = load_bundle_series(bundles)
        metrics = extract_metrics_from_records(records)
        comp = compare_pairwise(metrics[0], metrics[1], records[0], records[1])
        assert comp.composite_score_delta > 0

    def test_safety_flag_mismatch_safety_fail(self):
        """Test safety flag mismatch creates SAFETY_FAIL."""
        bundles = [
            ("baseline", FIXTURES / "artifact_browser_baseline"),
            ("invalid", FIXTURES / "artifact_browser_invalid_safety"),
        ]
        records = load_bundle_series(bundles, strict=False)
        metrics = extract_metrics_from_records(records)
        comp = compare_pairwise(metrics[0], metrics[1], records[0], records[1])
        assert comp.safety_fail is True
        assert comp.overall_classification == "SAFETY_FAIL"

    def test_pairwise_to_dict(self):
        """Test pairwise serialization."""
        bundles = [
            ("a", FIXTURES / "artifact_browser_baseline"),
            ("b", FIXTURES / "artifact_browser_baseline"),
        ]
        records = load_bundle_series(bundles)
        metrics = extract_metrics_from_records(records)
        comp = compare_pairwise(metrics[0], metrics[1], records[0], records[1])
        d = pairwise_to_dict(comp)
        assert "overall_classification" in d
        assert "metric_deltas" in d
        assert "artifact_changes" in d

    def test_compare_all_pairs(self):
        """Test all-pairs comparison with 2 bundles."""
        bundles = [
            ("baseline", FIXTURES / "artifact_browser_baseline"),
            ("improved", FIXTURES / "artifact_browser_candidate_improved"),
        ]
        records = load_bundle_series(bundles)
        metrics = extract_metrics_from_records(records)
        comparisons = compare_all_pairs(metrics, records)
        assert len(comparisons) == 1

    def test_build_pairwise_json(self):
        """Test pairwise comparison JSON shape."""
        bundles = [
            ("baseline", FIXTURES / "artifact_browser_baseline"),
            ("improved", FIXTURES / "artifact_browser_candidate_improved"),
        ]
        records = load_bundle_series(bundles)
        metrics = extract_metrics_from_records(records)
        comparisons = compare_all_pairs(metrics, records)
        data = build_pairwise_comparison_json(comparisons)
        assert data["comparison_count"] == 1
        assert data["schema_version"] == "1.0.0"

    def test_metric_deltas_present(self):
        """Test metric deltas are present in comparison."""
        bundles = [
            ("baseline", FIXTURES / "artifact_browser_baseline"),
            ("improved", FIXTURES / "artifact_browser_candidate_improved"),
        ]
        records = load_bundle_series(bundles)
        metrics = extract_metrics_from_records(records)
        comp = compare_pairwise(metrics[0], metrics[1], records[0], records[1])
        assert len(comp.metric_deltas) > 0
        for d in comp.metric_deltas:
            assert d.classification in ("IMPROVED", "REGRESSED", "STABLE", "MIXED")

    def test_artifact_changes_tracked(self):
        """Test artifact changes are tracked."""
        bundles = [
            ("baseline", FIXTURES / "artifact_browser_baseline"),
            ("improved", FIXTURES / "artifact_browser_candidate_improved"),
        ]
        records = load_bundle_series(bundles)
        metrics = extract_metrics_from_records(records)
        comp = compare_pairwise(metrics[0], metrics[1], records[0], records[1])
        assert "unchanged" in comp.artifact_changes
