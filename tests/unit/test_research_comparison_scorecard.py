"""Tests for research comparison scorecard.

Program F tests. Offline only. No network.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from core.research_bundle_series import load_bundle_series
from core.research_comparison_metrics import extract_metrics_from_records
from core.research_comparison_scorecard import (
    build_scorecard,
    scorecard_to_dict,
)

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "research_comparison_analytics"


class TestComparisonScorecard:
    """Test comparison scorecard."""

    def test_scorecard_recommends_best_score(self):
        """Test scorecard recommends bundle with best composite score."""
        bundles = [
            ("baseline", FIXTURES / "artifact_browser_baseline"),
            ("improved", FIXTURES / "artifact_browser_candidate_improved"),
        ]
        records = load_bundle_series(bundles)
        metrics = extract_metrics_from_records(records)
        sc = build_scorecard(metrics)
        assert sc.best_composite_score == "improved"
        assert sc.best_composite_score_value == 0.90

    def test_scorecard_safest_bundle(self):
        """Test scorecard identifies safest bundle."""
        bundles = [
            ("baseline", FIXTURES / "artifact_browser_baseline"),
            ("improved", FIXTURES / "artifact_browser_candidate_improved"),
        ]
        records = load_bundle_series(bundles)
        metrics = extract_metrics_from_records(records)
        sc = build_scorecard(metrics)
        assert sc.safest_bundle in ("baseline", "improved")
        assert sc.advisory_only is True

    def test_scorecard_promotion_blocked(self):
        """Test scorecard blocks promotion."""
        bundles = [
            ("baseline", FIXTURES / "artifact_browser_baseline"),
            ("improved", FIXTURES / "artifact_browser_candidate_improved"),
        ]
        records = load_bundle_series(bundles)
        metrics = extract_metrics_from_records(records)
        sc = build_scorecard(metrics)
        assert sc.promotion_blocked is True
        assert "Human review" in sc.promotion_block_reason

    def test_scorecard_to_dict(self):
        """Test scorecard serialization."""
        bundles = [
            ("baseline", FIXTURES / "artifact_browser_baseline"),
            ("improved", FIXTURES / "artifact_browser_candidate_improved"),
        ]
        records = load_bundle_series(bundles)
        metrics = extract_metrics_from_records(records)
        sc = build_scorecard(metrics)
        d = scorecard_to_dict(sc)
        assert "best_composite_score" in d
        assert "safest_bundle" in d
        assert "promotion_blocked" in d
        assert d["promotion_blocked"] is True

    def test_scorecard_review_priority(self):
        """Test scorecard review priority ordering."""
        bundles = [
            ("baseline", FIXTURES / "artifact_browser_baseline"),
            ("improved", FIXTURES / "artifact_browser_candidate_improved"),
        ]
        records = load_bundle_series(bundles)
        metrics = extract_metrics_from_records(records)
        sc = build_scorecard(metrics)
        assert len(sc.review_priority) == 2
        assert sc.review_priority[0] == "improved"  # Higher score first

    def test_scorecard_least_fragile(self):
        """Test scorecard identifies least fragile bundle."""
        bundles = [
            ("baseline", FIXTURES / "artifact_browser_baseline"),
            ("improved", FIXTURES / "artifact_browser_candidate_improved"),
        ]
        records = load_bundle_series(bundles)
        metrics = extract_metrics_from_records(records)
        sc = build_scorecard(metrics)
        assert sc.least_fragile == "improved"  # Lower fragility

    def test_scorecard_best_negative_control(self):
        """Test scorecard identifies best negative control margin."""
        bundles = [
            ("baseline", FIXTURES / "artifact_browser_baseline"),
            ("improved", FIXTURES / "artifact_browser_candidate_improved"),
        ]
        records = load_bundle_series(bundles)
        metrics = extract_metrics_from_records(records)
        sc = build_scorecard(metrics)
        assert sc.best_negative_control == "improved"

    def test_scorecard_deterministic(self):
        """Test scorecard is deterministic."""
        bundles = [
            ("baseline", FIXTURES / "artifact_browser_baseline"),
            ("improved", FIXTURES / "artifact_browser_candidate_improved"),
        ]
        records = load_bundle_series(bundles)
        metrics = extract_metrics_from_records(records)
        sc1 = build_scorecard(metrics)
        sc2 = build_scorecard(metrics)
        assert scorecard_to_dict(sc1) == scorecard_to_dict(sc2)

    def test_scorecard_empty_metrics_raises(self):
        """Test empty metrics raises ValueError."""
        with pytest.raises(ValueError):
            build_scorecard(())
