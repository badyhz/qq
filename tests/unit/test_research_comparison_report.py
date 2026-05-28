"""Tests for research comparison report rendering.

Program G+H tests. Offline only. No network.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from core.research_bundle_series import load_bundle_series
from core.research_comparison_metrics import (
    build_extracted_metrics_json,
    extract_metrics_from_records,
)
from core.research_comparison_pairwise import (
    build_pairwise_comparison_json,
    compare_all_pairs,
)
from core.research_comparison_regression import (
    detect_regressions,
    regression_report_to_dict,
)
from core.research_comparison_report import (
    render_comparison_html,
    render_comparison_markdown,
)
from core.research_comparison_scorecard import (
    build_scorecard,
    scorecard_to_dict,
)
from core.research_trend_engine import (
    compute_trend_report,
    trend_report_to_dict,
)

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "research_comparison_analytics"


def _build_report_data():
    """Helper to build report data from fixtures."""
    bundles = [
        ("baseline", FIXTURES / "artifact_browser_baseline"),
        ("improved", FIXTURES / "artifact_browser_candidate_improved"),
    ]
    records = load_bundle_series(bundles)
    metrics = extract_metrics_from_records(records)
    metrics_json = build_extracted_metrics_json(metrics)
    comparisons = compare_all_pairs(metrics, records)
    pairwise_json = build_pairwise_comparison_json(comparisons)
    scorecard = build_scorecard(metrics)
    scorecard_json = scorecard_to_dict(scorecard)

    rr = detect_regressions(metrics[0], metrics[1])
    regression_json = {
        "has_regressions": rr.has_regressions,
        "regression_count": rr.regression_count,
        "regressions": [
            {"severity": r.severity, "description": r.description}
            for r in rr.regressions
        ],
    }

    trend_json = {
        "bundle_count": 0,
        "labels": [],
        "metric_trends": [],
        "detections": [],
        "overall_trend": "insufficient_data",
    }

    return scorecard_json, metrics_json, pairwise_json, trend_json, regression_json, {}


class TestMarkdownReport:
    """Test markdown report rendering."""

    def test_markdown_contains_required_sections(self):
        """Test markdown report contains required sections."""
        scorecard, metrics, pairwise, trend, regression, manifest = _build_report_data()
        md = render_comparison_markdown(scorecard, metrics, pairwise, trend, regression, manifest)
        assert "# Research Comparison Report" in md
        assert "## 1. Executive Comparison Verdict" in md
        assert "## 2. Bundle List" in md
        assert "## 3. Safety Boundary" in md
        assert "## 4. Metric Table" in md
        assert "## 5. Pairwise Differences" in md
        assert "## 6. Trend Analysis" in md
        assert "## 7. Regression Detector" in md
        assert "## 8. Artifact Drift" in md
        assert "## 9. Negative Control Margin Comparison" in md
        assert "## 10. Bootstrap Uncertainty Comparison" in md
        assert "## 11. Regime Risk Comparison" in md
        assert "## 12. Portfolio Overlap Comparison" in md
        assert "## 13. Human Review Recommendations" in md
        assert "## 14. Advisory-Only" in md

    def test_markdown_contains_advisory_statement(self):
        """Test advisory-only statement present."""
        scorecard, metrics, pairwise, trend, regression, manifest = _build_report_data()
        md = render_comparison_markdown(scorecard, metrics, pairwise, trend, regression, manifest)
        assert "advisory only" in md.lower()
        assert "HOLD" in md

    def test_markdown_deterministic(self):
        """Test markdown report is deterministic."""
        scorecard, metrics, pairwise, trend, regression, manifest = _build_report_data()
        md1 = render_comparison_markdown(scorecard, metrics, pairwise, trend, regression, manifest)
        md2 = render_comparison_markdown(scorecard, metrics, pairwise, trend, regression, manifest)
        assert md1 == md2


class TestHTMLReport:
    """Test HTML report rendering."""

    def test_html_contains_required_sections(self):
        """Test HTML report contains required sections."""
        scorecard, metrics, pairwise, trend, regression, manifest = _build_report_data()
        html = render_comparison_html(scorecard, metrics, pairwise, trend, regression, manifest)
        assert "<!DOCTYPE html>" in html
        assert "Research Comparison Report" in html
        assert "<table" in html

    def test_html_standalone(self):
        """Test HTML has no external dependencies."""
        scorecard, metrics, pairwise, trend, regression, manifest = _build_report_data()
        html = render_comparison_html(scorecard, metrics, pairwise, trend, regression, manifest)
        assert "cdn" not in html.lower()
        assert "https://" not in html
        assert "http://" not in html
        assert "<script src=" not in html

    def test_html_has_css(self):
        """Test HTML has inline CSS."""
        scorecard, metrics, pairwise, trend, regression, manifest = _build_report_data()
        html = render_comparison_html(scorecard, metrics, pairwise, trend, regression, manifest)
        assert "<style>" in html

    def test_html_advisory_footer(self):
        """Test HTML has advisory footer."""
        scorecard, metrics, pairwise, trend, regression, manifest = _build_report_data()
        html = render_comparison_html(scorecard, metrics, pairwise, trend, regression, manifest)
        assert "Advisory only" in html
        assert "HOLD" in html

    def test_html_deterministic(self):
        """Test HTML report is deterministic."""
        scorecard, metrics, pairwise, trend, regression, manifest = _build_report_data()
        html1 = render_comparison_html(scorecard, metrics, pairwise, trend, regression, manifest)
        html2 = render_comparison_html(scorecard, metrics, pairwise, trend, regression, manifest)
        assert html1 == html2
