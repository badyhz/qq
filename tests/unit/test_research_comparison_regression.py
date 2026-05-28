"""Tests for research comparison regression detector.

Program E tests. Offline only. No network.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from core.research_bundle_series import load_bundle_series
from core.research_comparison_metrics import extract_metrics_from_records
from core.research_comparison_regression import (
    detect_regressions,
    regression_report_to_dict,
)

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "research_comparison_analytics"


class TestRegressionDetector:
    """Test regression detection."""

    def test_identical_no_regression(self):
        """Test identical bundles have no regressions."""
        bundles = [
            ("a", FIXTURES / "artifact_browser_baseline"),
            ("b", FIXTURES / "artifact_browser_baseline"),
        ]
        records = load_bundle_series(bundles)
        metrics = extract_metrics_from_records(records)
        report = detect_regressions(metrics[0], metrics[1])
        assert not report.has_regressions
        assert report.regression_count == 0
        assert report.status == "PASS"

    def test_score_drop_detected(self):
        """Test score drop above threshold is detected."""
        bundles = [
            ("baseline", FIXTURES / "artifact_browser_baseline"),
            ("regressed", FIXTURES / "artifact_browser_candidate_regressed"),
        ]
        records = load_bundle_series(bundles)
        metrics = extract_metrics_from_records(records)
        report = detect_regressions(metrics[0], metrics[1])
        assert report.has_regressions
        score_regs = [r for r in report.regressions if r.metric == "composite_score"]
        assert len(score_regs) > 0

    def test_blocker_increase_detected(self):
        """Test blocker count increase is detected."""
        bundles = [
            ("baseline", FIXTURES / "artifact_browser_baseline"),
            ("regressed", FIXTURES / "artifact_browser_candidate_regressed"),
        ]
        records = load_bundle_series(bundles)
        metrics = extract_metrics_from_records(records)
        report = detect_regressions(metrics[0], metrics[1])
        blocker_regs = [r for r in report.regressions if r.metric == "blocker_count"]
        # Regressed bundle has blockers, baseline has 0
        assert len(blocker_regs) > 0

    def test_safety_flag_mismatch_high_severity(self):
        """Test safety flag mismatch is HIGH severity."""
        bundles = [
            ("baseline", FIXTURES / "artifact_browser_baseline"),
            ("invalid", FIXTURES / "artifact_browser_invalid_safety"),
        ]
        records = load_bundle_series(bundles, strict=False)
        metrics = extract_metrics_from_records(records)
        report = detect_regressions(metrics[0], metrics[1])
        safety_regs = [r for r in report.regressions if r.category == "safety"]
        assert len(safety_regs) > 0
        assert all(r.severity == "HIGH" for r in safety_regs)

    def test_regression_report_to_dict(self):
        """Test regression report serialization."""
        bundles = [
            ("a", FIXTURES / "artifact_browser_baseline"),
            ("b", FIXTURES / "artifact_browser_baseline"),
        ]
        records = load_bundle_series(bundles)
        metrics = extract_metrics_from_records(records)
        report = detect_regressions(metrics[0], metrics[1])
        d = regression_report_to_dict(report)
        assert "has_regressions" in d
        assert "regressions" in d
        assert "status" in d

    def test_safety_regression_makes_fail(self):
        """Test safety regression makes overall status FAIL."""
        bundles = [
            ("baseline", FIXTURES / "artifact_browser_baseline"),
            ("invalid", FIXTURES / "artifact_browser_invalid_safety"),
        ]
        records = load_bundle_series(bundles, strict=False)
        metrics = extract_metrics_from_records(records)
        report = detect_regressions(metrics[0], metrics[1])
        assert report.status == "FAIL"

    def test_improved_bundle_no_regression(self):
        """Test improved bundle has no regressions."""
        bundles = [
            ("baseline", FIXTURES / "artifact_browser_baseline"),
            ("improved", FIXTURES / "artifact_browser_candidate_improved"),
        ]
        records = load_bundle_series(bundles)
        metrics = extract_metrics_from_records(records)
        report = detect_regressions(metrics[0], metrics[1])
        # Improved bundle shouldn't have regressions
        safety_regs = [r for r in report.regressions if r.category == "safety"]
        assert len(safety_regs) == 0

    def test_regression_deterministic(self):
        """Test regression detection is deterministic."""
        bundles = [
            ("baseline", FIXTURES / "artifact_browser_baseline"),
            ("regressed", FIXTURES / "artifact_browser_candidate_regressed"),
        ]
        records = load_bundle_series(bundles)
        metrics = extract_metrics_from_records(records)
        r1 = detect_regressions(metrics[0], metrics[1])
        r2 = detect_regressions(metrics[0], metrics[1])
        assert regression_report_to_dict(r1) == regression_report_to_dict(r2)
