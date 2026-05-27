"""Tests for offline shadow report renderers (Phase 9)."""
import json

import pytest

from core.offline_shadow_report_renderer import (
    render_report_html,
    render_report_json,
    render_report_markdown,
)


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

def _make_result(**overrides):
    base = {
        "experiment_id": "exp_001",
        "symbol": "BTCUSDT",
        "timeframe": "5m",
        "param_label": "conservative",
        "window_id": "w_train",
        "metrics": {
            "candidate_count": 10,
            "win_count": 6,
            "loss_count": 4,
            "neutral_count": 0,
            "win_rate": 0.6,
            "avg_return_r": 0.5,
            "expectancy_r": 0.3,
            "max_drawdown_r": -1.2,
            "avg_mfe_r": 1.5,
            "avg_mae_r": -0.8,
            "profit_factor": 1.5,
            "sample_quality_score": 0.75,
            "coverage_status": "full",
        },
        "scorecard": {
            "grade": "PASS",
            "reason_codes": ["expectancy_ok"],
            "blockers": [],
        },
    }
    base.update(overrides)
    return base


def _make_two_results():
    return [
        _make_result(),
        _make_result(
            experiment_id="exp_002",
            symbol="ETHUSDT",
            timeframe="15m",
            param_label="aggressive",
            metrics={
                "candidate_count": 8,
                "win_count": 3,
                "loss_count": 5,
                "neutral_count": 0,
                "win_rate": 0.375,
                "avg_return_r": -0.1,
                "expectancy_r": -0.05,
                "max_drawdown_r": -2.0,
                "avg_mfe_r": 1.0,
                "avg_mae_r": -1.2,
                "profit_factor": 0.8,
                "sample_quality_score": 0.55,
                "coverage_status": "partial",
            },
            scorecard={
                "grade": "WATCH",
                "reason_codes": ["non_positive_expectancy=-0.0500"],
                "blockers": [],
            },
        ),
    ]


# ---------------------------------------------------------------------------
# Markdown tests
# ---------------------------------------------------------------------------

class TestRenderMarkdown:
    def test_empty_results(self):
        md = render_report_markdown([])
        assert "No experiments" in md

    def test_contains_title(self):
        md = render_report_markdown([_make_result()])
        assert "# Offline Shadow Research Report" in md

    def test_contains_hold_banner(self):
        md = render_report_markdown([_make_result()])
        assert "HOLD" in md

    def test_contains_summary_table(self):
        md = render_report_markdown([_make_result()])
        assert "| ID | Symbol |" in md

    def test_contains_experiment_id(self):
        md = render_report_markdown([_make_result()])
        assert "exp_001" in md

    def test_contains_metrics(self):
        md = render_report_markdown([_make_result()])
        assert "Win Rate" in md
        assert "Expectancy" in md
        assert "Profit Factor" in md

    def test_contains_scorecard(self):
        md = render_report_markdown([_make_result()])
        assert "PASS" in md
        assert "Scorecard" in md

    def test_multiple_experiments(self):
        results = _make_two_results()
        md = render_report_markdown(results)
        assert "exp_001" in md
        assert "exp_002" in md

    def test_scorecard_criteria(self):
        md = render_report_markdown([_make_result()])
        assert "reason_codes" in md or "expectancy_ok" in md

    def test_no_scorecard(self):
        result = _make_result()
        del result["scorecard"]
        md = render_report_markdown([result])
        assert "exp_001" in md  # still renders


# ---------------------------------------------------------------------------
# JSON tests
# ---------------------------------------------------------------------------

class TestRenderJson:
    def test_empty_results(self):
        report = render_report_json([])
        assert report["release_hold"] == "HOLD"
        assert report["experiment_count"] == 0
        assert report["experiments"] == []

    def test_hold_field(self):
        report = render_report_json([_make_result()])
        assert report["release_hold"] == "HOLD"

    def test_experiment_count(self):
        report = render_report_json(_make_two_results())
        assert report["experiment_count"] == 2

    def test_summary_fields(self):
        report = render_report_json([_make_result()])
        summary = report["summary"]
        assert "experiment_count" in summary
        assert "total_candidates" in summary
        assert "avg_win_rate" in summary
        assert "avg_expectancy_r" in summary
        assert "best_experiment_id" in summary

    def test_experiments_array(self):
        report = render_report_json(_make_two_results())
        assert len(report["experiments"]) == 2
        assert report["experiments"][0]["experiment_id"] == "exp_001"

    def test_best_worst(self):
        report = render_report_json(_make_two_results())
        assert report["summary"]["best_experiment_id"] == "exp_001"
        assert report["summary"]["worst_experiment_id"] == "exp_002"

    def test_metrics_preserved(self):
        report = render_report_json([_make_result()])
        m = report["experiments"][0]["metrics"]
        assert m["win_rate"] == 0.6
        assert m["candidate_count"] == 10

    def test_scorecard_preserved(self):
        report = render_report_json([_make_result()])
        sc = report["experiments"][0]["scorecard"]
        assert sc["grade"] == "PASS"

    def test_json_serializable(self):
        report = render_report_json(_make_two_results())
        # should not raise
        json.dumps(report)


# ---------------------------------------------------------------------------
# HTML tests
# ---------------------------------------------------------------------------

class TestRenderHtml:
    def test_empty_results(self):
        html = render_report_html([])
        assert "<!DOCTYPE html>" in html

    def test_hold_banner(self):
        html = render_report_html([_make_result()])
        assert "HOLD" in html
        assert "No Live Trading" in html

    def test_contains_experiment_id(self):
        html = render_report_html([_make_result()])
        assert "exp_001" in html

    def test_contains_summary_cards(self):
        html = render_report_html([_make_result()])
        assert "Experiments" in html
        assert "Avg Win Rate" in html

    def test_contains_table(self):
        html = render_report_html([_make_result()])
        assert "<table>" in html
        assert "<th>" in html

    def test_grade_color(self):
        html = render_report_html([_make_result()])
        # B+ should have a green-ish color
        assert "color:" in html

    def test_multiple_experiments_in_table(self):
        html = render_report_html(_make_two_results())
        assert "exp_001" in html
        assert "exp_002" in html

    def test_html_escaped(self):
        result = _make_result(experiment_id="<script>alert(1)</script>")
        html = render_report_html([result])
        assert "<script>" not in html
        assert "&lt;script&gt;" in html
