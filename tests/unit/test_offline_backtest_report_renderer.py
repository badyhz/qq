"""Tests for core/offline_backtest_report_renderer.py — 20+ tests."""
from __future__ import annotations

import json

import pytest

from core.offline_backtest_report_renderer import (
    render_backtest_report_html,
    render_backtest_report_json,
    render_backtest_report_markdown,
)


def _minimal_data() -> dict:
    return {"title": "Test Report", "release_hold": "HOLD"}


def _full_data() -> dict:
    return {
        "title": "Full Backtest Report",
        "release_hold": "HOLD",
        "executive_summary": "Strategy shows positive edge.",
        "data_quality": {
            "items": [
                {"symbol": "BTCUSDT", "timeframe": "1h", "total_rows": 1000,
                 "is_clean": True, "issue_count": 0},
                {"symbol": "ETHUSDT", "timeframe": "4h", "total_rows": 500,
                 "is_clean": False, "issue_count": 3},
            ]
        },
        "walk_forward_matrix": [
            {"split_id": "S1", "symbol": "BTCUSDT", "trade_count": 20,
             "expectancy_r": 0.5, "win_rate": 0.6, "max_drawdown_r": -2.0, "grade": "PASS"},
            {"split_id": "S2", "symbol": "ETHUSDT", "trade_count": 15,
             "expectancy_r": -0.1, "win_rate": 0.4, "max_drawdown_r": -4.0, "grade": "REJECT"},
        ],
        "top_params": [
            {"param_id": "P1", "quality_adjusted_score": 2.5, "expectancy_r": 0.5,
             "profit_factor": 1.8, "trade_count": 25, "grade": "PASS"},
        ],
        "rejected_params": [
            {"param_id": "P2", "reasons": ["negative expectancy", "high drawdown"]},
        ],
        "robustness_table": [
            {"check_name": "fee_sensitivity", "is_robust": True,
             "passes": ("1bps", "5bps"), "fails": (), "detail": "2/2 pass"},
            {"check_name": "slippage_sensitivity", "is_robust": False,
             "passes": ("1bps",), "fails": ("10bps",), "detail": "1/2 pass"},
        ],
        "symbol_breakdown": [
            {"symbol": "BTCUSDT", "timeframe": "1h", "run_count": 5,
             "avg_expectancy": 0.4, "best_grade": "PASS"},
        ],
        "next_recommendation": "Increase sample size for ETHUSDT.",
    }


class TestMarkdownRenderer:
    def test_minimal(self):
        md = render_backtest_report_markdown(_minimal_data())
        assert "# Test Report" in md
        assert "HOLD" in md

    def test_title(self):
        md = render_backtest_report_markdown({"title": "My Report"})
        assert "# My Report" in md

    def test_default_title(self):
        md = render_backtest_report_markdown({})
        assert "Offline Backtest Report" in md

    def test_executive_summary(self):
        md = render_backtest_report_markdown({
            "executive_summary": "Good results.",
        })
        assert "Good results." in md
        assert "Executive Summary" in md

    def test_data_quality_table(self):
        data = _full_data()
        md = render_backtest_report_markdown(data)
        assert "BTCUSDT" in md
        assert "ETHUSDT" in md
        assert "1000" in md

    def test_walk_forward_matrix(self):
        md = render_backtest_report_markdown(_full_data())
        assert "Walk-Forward Matrix" in md
        assert "S1" in md
        assert "S2" in md

    def test_top_params(self):
        md = render_backtest_report_markdown(_full_data())
        assert "Top Parameter Sets" in md
        assert "P1" in md

    def test_rejected_params(self):
        md = render_backtest_report_markdown(_full_data())
        assert "Rejected" in md
        assert "P2" in md
        assert "negative expectancy" in md

    def test_robustness_table(self):
        md = render_backtest_report_markdown(_full_data())
        assert "Robustness" in md
        assert "fee_sensitivity" in md

    def test_symbol_breakdown(self):
        md = render_backtest_report_markdown(_full_data())
        assert "Symbol" in md
        assert "BTCUSDT" in md

    def test_next_recommendation(self):
        md = render_backtest_report_markdown(_full_data())
        assert "Next Research" in md
        assert "Increase sample" in md

    def test_empty_sections_omitted(self):
        md = render_backtest_report_markdown(_minimal_data())
        assert "Walk-Forward" not in md
        assert "Top Parameter" not in md

    def test_release_hold_always_present(self):
        md = render_backtest_report_markdown({"release_hold": "HOLD"})
        assert "HOLD" in md


class TestJSONRenderer:
    def test_minimal(self):
        j = render_backtest_report_json(_minimal_data())
        parsed = json.loads(j)
        assert parsed["title"] == "Test Report"

    def test_full_data_roundtrip(self):
        data = _full_data()
        j = render_backtest_report_json(data)
        parsed = json.loads(j)
        assert parsed["title"] == data["title"]
        assert len(parsed["walk_forward_matrix"]) == 2

    def test_empty_data(self):
        j = render_backtest_report_json({})
        assert json.loads(j) == {}

    def test_json_valid(self):
        j = render_backtest_report_json(_full_data())
        parsed = json.loads(j)
        assert isinstance(parsed, dict)


class TestHTMLRenderer:
    def test_minimal(self):
        html = render_backtest_report_html(_minimal_data())
        assert "<!DOCTYPE html>" in html
        assert "Test Report" in html
        assert "HOLD" in html

    def test_title_tag(self):
        html = render_backtest_report_html({"title": "My Report"})
        assert "<title>My Report</title>" in html

    def test_default_title(self):
        html = render_backtest_report_html({})
        assert "Offline Backtest Report" in html

    def test_executive_summary(self):
        html = render_backtest_report_html({"executive_summary": "Edge found."})
        assert "Edge found." in html

    def test_data_quality_table(self):
        html = render_backtest_report_html(_full_data())
        assert "BTCUSDT" in html
        assert "<table>" in html

    def test_walk_forward_matrix(self):
        html = render_backtest_report_html(_full_data())
        assert "Walk-Forward" in html
        assert "S1" in html

    def test_top_params(self):
        html = render_backtest_report_html(_full_data())
        assert "P1" in html

    def test_rejected_params(self):
        html = render_backtest_report_html(_full_data())
        assert "P2" in html

    def test_robustness_table(self):
        html = render_backtest_report_html(_full_data())
        assert "fee_sensitivity" in html

    def test_symbol_breakdown(self):
        html = render_backtest_report_html(_full_data())
        assert "BTCUSDT" in html

    def test_next_recommendation(self):
        html = render_backtest_report_html(_full_data())
        assert "Increase sample" in html

    def test_html_closes(self):
        html = render_backtest_report_html(_minimal_data())
        assert "</html>" in html

    def test_grade_css_classes(self):
        html = render_backtest_report_html(_full_data())
        assert 'class="pass"' in html
        assert 'class="reject"' in html
