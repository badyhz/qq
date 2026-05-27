"""T1848 - Frozen Backlog Dashboard Renderer Tests.

At least 10 tests. Pure functions only. No I/O except tmp_path file write.
"""
from __future__ import annotations

import pathlib

import pytest

from core.frozen_backlog_inventory import FROZEN_BACKLOG_INVENTORY
from core.frozen_backlog_report_materializer import materialize_full_report
from core.frozen_backlog_dashboard_renderer import (
    render_dashboard_html,
    render_file_table_html,
    render_hold_banner_html,
    render_risk_distribution_html,
    render_summary_cards_html,
)

_summary, _records = materialize_full_report(FROZEN_BACKLOG_INVENTORY)


# --- render_hold_banner_html ---


class TestHoldBanner:
    def test_contains_hold_text(self) -> None:
        html = render_hold_banner_html()
        assert "HOLD" in html

    def test_contains_hold_banner_class(self) -> None:
        html = render_hold_banner_html()
        assert 'class="hold-banner"' in html

    def test_contains_warning_icon(self) -> None:
        html = render_hold_banner_html()
        assert "hold-icon" in html


# --- render_summary_cards_html ---


class TestSummaryCards:
    def test_contains_total_files(self) -> None:
        html = render_summary_cards_html(_summary)
        assert "22" in html

    def test_contains_high_risk_count(self) -> None:
        html = render_summary_cards_html(_summary)
        assert "9" in html

    def test_contains_medium_risk_count(self) -> None:
        html = render_summary_cards_html(_summary)
        assert "13" in html

    def test_contains_hold(self) -> None:
        html = render_summary_cards_html(_summary)
        assert "HOLD" in html

    def test_has_card_class(self) -> None:
        html = render_summary_cards_html(_summary)
        assert 'class="card' in html

    def test_has_summary_cards_class(self) -> None:
        html = render_summary_cards_html(_summary)
        assert 'class="summary-cards"' in html


# --- render_risk_distribution_html ---


class TestRiskDistribution:
    def test_contains_bar_high(self) -> None:
        html = render_risk_distribution_html(_summary)
        assert "bar-high" in html

    def test_contains_bar_medium(self) -> None:
        html = render_risk_distribution_html(_summary)
        assert "bar-medium" in html

    def test_contains_risk_distribution_class(self) -> None:
        html = render_risk_distribution_html(_summary)
        assert 'class="risk-distribution"' in html

    def test_contains_counts(self) -> None:
        html = render_risk_distribution_html(_summary)
        assert "(9)" in html
        assert "(13)" in html


# --- render_file_table_html ---


class TestFileTable:
    def test_contains_table_tag(self) -> None:
        html = render_file_table_html(_records)
        assert "<table>" in html

    def test_contains_all_22_rows(self) -> None:
        html = render_file_table_html(_records)
        # Count <tr> in tbody (excluding header)
        assert html.count("<tr>") == 23  # 1 header + 22 data rows

    def test_contains_file_paths(self) -> None:
        html = render_file_table_html(_records)
        assert "core/live_runner.py" in html
        assert "scripts/live_playbook.py" in html

    def test_contains_risk_classes(self) -> None:
        html = render_file_table_html(_records)
        assert "HIGH" in html
        assert "MEDIUM" in html

    def test_contains_categories(self) -> None:
        html = render_file_table_html(_records)
        assert "LIVE_RUNNER" in html
        assert "OPERATIONAL_SHADOW" in html

    def test_contains_allowed_actions(self) -> None:
        html = render_file_table_html(_records)
        assert "review" in html
        assert "read" in html

    def test_contains_forbidden_actions(self) -> None:
        html = render_file_table_html(_records)
        assert "execute" in html
        assert "submit" in html

    def test_contains_table_header(self) -> None:
        html = render_file_table_html(_records)
        assert "<thead>" in html
        assert "File Path" in html
        assert "Risk Class" in html


# --- render_dashboard_html ---


class TestDashboardHtml:
    def test_is_html_document(self) -> None:
        html = render_dashboard_html(_summary, _records)
        assert html.startswith("<!DOCTYPE html>")
        assert "</html>" in html

    def test_contains_title(self) -> None:
        html = render_dashboard_html(_summary, _records)
        assert "Frozen Backlog Review Dashboard" in html

    def test_contains_hold_banner(self) -> None:
        html = render_dashboard_html(_summary, _records)
        assert "hold-banner" in html

    def test_contains_summary_cards(self) -> None:
        html = render_dashboard_html(_summary, _records)
        assert "summary-cards" in html

    def test_contains_file_table(self) -> None:
        html = render_dashboard_html(_summary, _records)
        assert "<table>" in html

    def test_contains_risk_distribution(self) -> None:
        html = render_dashboard_html(_summary, _records)
        assert "risk-distribution" in html

    def test_contains_safety_flags(self) -> None:
        html = render_dashboard_html(_summary, _records)
        assert "No Live" in html
        assert "No Submit" in html
        assert "No Exchange" in html

    def test_contains_css(self) -> None:
        html = render_dashboard_html(_summary, _records)
        assert "<style>" in html

    def test_contains_footer(self) -> None:
        html = render_dashboard_html(_summary, _records)
        assert "dashboard-footer" in html

    def test_no_external_resources(self) -> None:
        html = render_dashboard_html(_summary, _records)
        assert "https://" not in html
        assert "http://" not in html
        assert "cdn." not in html

    def test_deterministic(self) -> None:
        a = render_dashboard_html(_summary, _records)
        b = render_dashboard_html(_summary, _records)
        assert a == b

    def test_write_to_file(self, tmp_path: object) -> None:
        html = render_dashboard_html(_summary, _records)
        out = pathlib.Path(str(tmp_path)) / "dashboard.html"
        out.write_text(html, encoding="utf-8")
        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in content
