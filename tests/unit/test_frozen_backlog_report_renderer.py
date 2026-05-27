"""T1530 - Frozen Backlog Report Markdown Renderer Tests.

At least 10 tests. Pure functions only. No I/O except tmp_path file write.
"""
from __future__ import annotations

import os
import subprocess
import sys

import pytest

from core.frozen_backlog_inventory import FROZEN_BACKLOG_INVENTORY
from core.frozen_backlog_report_materializer import materialize_full_report
from core.frozen_backlog_report_renderer import (
    render_record_markdown,
    render_report_markdown,
    render_summary_markdown,
)

_summary, _records = materialize_full_report(FROZEN_BACKLOG_INVENTORY)
_ALL_FILE_PATHS = tuple(r.file_path for r in FROZEN_BACKLOG_INVENTORY.records)


# --- render_record_markdown ---


class TestRenderRecordMarkdown:
    def test_contains_file_path(self) -> None:
        record = _records[0]
        md = render_record_markdown(record)
        assert record.file_path in md

    def test_contains_risk_class(self) -> None:
        record = _records[0]
        md = render_record_markdown(record)
        assert record.risk_class in md

    def test_contains_release_hold(self) -> None:
        for record in _records:
            md = render_record_markdown(record)
            assert "HOLD" in md

    def test_contains_allowed_actions(self) -> None:
        record = _records[0]
        md = render_record_markdown(record)
        for action in record.allowed_actions:
            assert action in md

    def test_contains_forbidden_actions(self) -> None:
        record = _records[0]
        md = render_record_markdown(record)
        for action in record.forbidden_actions:
            assert action in md

    def test_contains_required_evidence(self) -> None:
        record = _records[0]
        md = render_record_markdown(record)
        for evidence in record.required_evidence:
            assert evidence in md

    def test_deterministic(self) -> None:
        record = _records[0]
        a = render_record_markdown(record)
        b = render_record_markdown(record)
        assert a == b

    def test_contains_section_header(self) -> None:
        record = _records[0]
        md = render_record_markdown(record)
        assert md.startswith("### ")


# --- render_summary_markdown ---


class TestRenderSummaryMarkdown:
    def test_contains_total_files(self) -> None:
        md = render_summary_markdown(_summary)
        assert str(_summary.total_files) in md

    def test_contains_high_risk_count(self) -> None:
        md = render_summary_markdown(_summary)
        assert str(_summary.high_risk_count) in md

    def test_contains_medium_risk_count(self) -> None:
        md = render_summary_markdown(_summary)
        assert str(_summary.medium_risk_count) in md

    def test_contains_hold(self) -> None:
        md = render_summary_markdown(_summary)
        assert "HOLD" in md

    def test_contains_safety_constraints(self) -> None:
        md = render_summary_markdown(_summary)
        assert "No Live" in md
        assert "No Submit" in md
        assert "No Exchange" in md

    def test_deterministic(self) -> None:
        a = render_summary_markdown(_summary)
        b = render_summary_markdown(_summary)
        assert a == b

    def test_contains_summary_header(self) -> None:
        md = render_summary_markdown(_summary)
        assert "## Summary" in md


# --- render_report_markdown ---


class TestRenderReportMarkdown:
    def test_contains_all_file_paths(self) -> None:
        md = render_report_markdown(_summary, _records)
        for path in _ALL_FILE_PATHS:
            assert path in md, f"Missing file path: {path}"

    def test_contains_22_records(self) -> None:
        assert len(_records) == 22

    def test_contains_report_header(self) -> None:
        md = render_report_markdown(_summary, _records)
        assert "# Frozen Backlog Review Report" in md

    def test_contains_summary_section(self) -> None:
        md = render_report_markdown(_summary, _records)
        assert "## Summary" in md

    def test_contains_frozen_files_section(self) -> None:
        md = render_report_markdown(_summary, _records)
        assert "## Frozen Files" in md

    def test_contains_hold(self) -> None:
        md = render_report_markdown(_summary, _records)
        assert "HOLD" in md

    def test_deterministic(self) -> None:
        a = render_report_markdown(_summary, _records)
        b = render_report_markdown(_summary, _records)
        assert a == b

    def test_contains_counts(self) -> None:
        md = render_report_markdown(_summary, _records)
        assert str(_summary.total_files) in md
        assert str(_summary.high_risk_count) in md
        assert str(_summary.medium_risk_count) in md

    def test_write_to_file(self, tmp_path: object) -> None:
        """Verify markdown can be written to file."""
        import pathlib

        md = render_report_markdown(_summary, _records)
        out = pathlib.Path(str(tmp_path)) / "report.md"
        out.write_text(md, encoding="utf-8")
        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert content == md

    def test_non_empty(self) -> None:
        md = render_report_markdown(_summary, _records)
        assert len(md) > 0
