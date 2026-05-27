"""Tests for research workbench report renderers — T4801-T4830."""
from __future__ import annotations

import pytest

from core.research_workbench_report import render_html_report, render_markdown_report


SAMPLE_DATA = {
    "strategy_count": 4,
    "total_rows": 100,
    "strategy_registry": {"strategy_count": 4, "validation_status": "PASS"},
    "parameter_search": {"search_budget": 120, "expanded_combinations": 80, "evaluated_combinations": 80, "budget_truncated": False},
    "results": {"total_rows": 100, "evaluated_rows": 95, "skipped_rows": 5},
    "portfolio_summary": {"total_trades": 500, "aggregate_expectancy_r": 0.3, "max_drawdown_approx": 0.08},
    "comparison": {"strategy_rankings": [{"strategy_id": "breakout", "avg_score": 0.6, "total_trades": 200}]},
    "promotion_recommendations": [{"strategy_id": "breakout", "symbol": "BTCUSDT", "status": "PROMOTE_TO_NEXT_RESEARCH_ROUND"}],
    "manifest": {"release_hold": "HOLD", "no_live": True, "no_submit": True, "no_exchange": True, "no_network": True},
}


class TestMarkdownRenderer:
    def test_renders_empty(self):
        md = render_markdown_report({})
        assert "Multi-Strategy Research Workbench" in md

    def test_renders_full(self):
        md = render_markdown_report(SAMPLE_DATA)
        assert "Executive Summary" in md
        assert "Strategy Registry" in md
        assert "Parameter Search" in md
        assert "Portfolio Aggregation" in md
        assert "HOLD" in md

    def test_deterministic(self):
        md1 = render_markdown_report(SAMPLE_DATA)
        md2 = render_markdown_report(SAMPLE_DATA)
        assert md1 == md2

    def test_no_external_assets(self):
        md = render_markdown_report(SAMPLE_DATA)
        assert "http://" not in md
        assert "https://" not in md


class TestHTMLRenderer:
    def test_renders_html(self):
        html = render_html_report(SAMPLE_DATA)
        assert "<!DOCTYPE html>" in html
        assert "</html>" in html

    def test_no_external_assets(self):
        html = render_html_report(SAMPLE_DATA)
        assert "cdn." not in html
        assert "googleapis" not in html
        assert "http://" not in html

    def test_inline_css(self):
        html = render_html_report(SAMPLE_DATA)
        assert "<style>" in html

    def test_deterministic(self):
        h1 = render_html_report(SAMPLE_DATA)
        h2 = render_html_report(SAMPLE_DATA)
        assert h1 == h2
