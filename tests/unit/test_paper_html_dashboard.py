"""Tests for HTML dashboard generator."""
from __future__ import annotations

import os
import tempfile

import pytest

from core.paper_trading.runtime_orchestrator import RuntimeResult
from core.paper_trading.html_dashboard import generate_dashboard_html, write_dashboard


def _result(**kwargs):
    defaults = dict(
        status="OK", strategy_name="macd_rebound",
        fixtures_run=4, fixtures_failed=0,
        total_signals=10, total_plans=8, total_rejected=2,
        total_trades=6, total_pnl=500.0, win_rate=0.7,
        score=62.0, rating="B", alerts_written=1,
        safety_flags=["NO_REAL_ORDER", "PAPER_ONLY"],
    )
    defaults.update(kwargs)
    return RuntimeResult(**defaults)


class TestHtmlDashboard:
    def test_html_generates(self):
        html = generate_dashboard_html(_result())
        assert "<html" in html
        assert "Paper Trading Dashboard" in html

    def test_contains_key_fields(self):
        html = generate_dashboard_html(_result())
        assert "macd_rebound" in html
        assert "500.00" in html or "+500" in html
        assert "70.0%" in html
        assert "B" in html

    def test_no_external_http(self):
        html = generate_dashboard_html(_result())
        assert "http://" not in html
        assert "https://" not in html
        assert "cdn" not in html.lower()

    def test_no_script_src(self):
        html = generate_dashboard_html(_result())
        assert "<script" not in html.lower()

    def test_css_inline(self):
        html = generate_dashboard_html(_result())
        assert "<style>" in html

    def test_safety_footer(self):
        html = generate_dashboard_html(_result())
        assert "NO_REAL_ORDER" in html
        assert "PAPER_ONLY" in html

    def test_empty_result(self):
        html = generate_dashboard_html(_result(
            total_trades=0, total_pnl=0, win_rate=0,
            total_signals=0, total_plans=0, total_rejected=0,
            fixtures_run=0, score=0, rating="REJECT",
        ))
        assert "REJECT" in html
        assert "<html" in html

    def test_write_to_file(self):
        r = _result()
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
            path = f.name
        try:
            write_dashboard(r, path)
            with open(path) as f:
                content = f.read()
            assert "<html" in content
            assert "Paper Trading" in content
        finally:
            os.unlink(path)

    def test_no_external_links(self):
        html = generate_dashboard_html(_result())
        # No external stylesheet or script links
        assert 'rel="stylesheet"' not in html
        assert "src=" not in html or "data:" in html
