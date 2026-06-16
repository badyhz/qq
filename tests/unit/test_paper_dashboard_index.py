"""Tests for dashboard index module."""
from __future__ import annotations

import os
import tempfile

import pytest

from core.paper_trading.dashboard_index import (
    ReportEntry, scan_reports, generate_index_html, write_index,
)


class TestScanReports:
    def test_scan_empty_dir(self):
        with tempfile.TemporaryDirectory() as d:
            entries = scan_reports(d)
            assert entries == []

    def test_scan_nonexistent(self):
        entries = scan_reports("/tmp/nonexistent_paper_reports_dir")
        assert entries == []

    def test_scan_finds_reports(self):
        with tempfile.TemporaryDirectory() as d:
            for name in ["paper_trading_report.md", "paper_trading_dashboard.html", "other.txt"]:
                with open(os.path.join(d, name), "w") as f:
                    f.write("test")
            entries = scan_reports(d)
            assert len(entries) == 2
            names = [e.name for e in entries]
            assert "paper_trading_dashboard.html" in names
            assert "paper_trading_report.md" in names

    def test_scan_ignores_non_paper(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "other_report.md"), "w") as f:
                f.write("test")
            entries = scan_reports(d)
            assert len(entries) == 0

    def test_entry_has_size_and_modified(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "paper_trading_test.md")
            with open(path, "w") as f:
                f.write("hello world")
            entries = scan_reports(d)
            assert len(entries) == 1
            assert entries[0].size_bytes == 11
            assert entries[0].modified  # non-empty


class TestGenerateIndexHtml:
    def test_generates_html(self):
        entries = [
            ReportEntry("paper_trading_report.md", "/tmp/x", 1024, "2026-06-16 12:00"),
            ReportEntry("paper_trading_dashboard.html", "/tmp/y", 2048, "2026-06-16 13:00"),
        ]
        html = generate_index_html(entries)
        assert "<html" in html
        assert ">2<" in html
        assert "reports found" in html
        assert "paper_trading_report.md" in html
        assert "paper_trading_dashboard.html" in html

    def test_empty_entries(self):
        html = generate_index_html([])
        assert ">0<" in html
        assert "reports found" in html
        assert "<html" in html

    def test_no_external_resources(self):
        html = generate_index_html([])
        assert "http://" not in html
        assert "https://" not in html
        assert "<script" not in html.lower()

    def test_css_inline(self):
        html = generate_index_html([])
        assert "<style>" in html


class TestWriteIndex:
    def test_writes_file(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "paper_trading_test.md"), "w") as f:
                f.write("test")
            out = write_index(d)
            assert os.path.isfile(out)
            with open(out) as f:
                content = f.read()
            assert "<html" in content
            assert "paper_trading_test.md" in content

    def test_custom_output_path(self):
        with tempfile.TemporaryDirectory() as d:
            custom = os.path.join(d, "custom_index.html")
            write_index(d, custom)
            assert os.path.isfile(custom)
