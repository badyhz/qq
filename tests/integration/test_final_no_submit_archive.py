"""Integration test: final no-submit archive."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_mock_closeout.final_no_submit_archive import (
    create_archive, search_entries
)


def test_create_archive():
    archive = create_archive()
    assert len(archive.entries) >= 10
    assert archive.archive_id.startswith("ARC_")


def test_has_required_categories():
    archive = create_archive()
    cats = {e.category for e in archive.entries}
    assert "timeline" in cats
    assert "safety_markers" in cats
    assert "prohibited_actions" in cats
    assert "final_declaration" in cats


def test_search_entries():
    archive = create_archive()
    results = search_entries(archive, "submit")
    assert len(results) >= 1


def test_search_safety():
    archive = create_archive()
    results = search_entries(archive, "safety")
    assert len(results) >= 1


def test_render_report():
    from src.runtime_integrations.testnet_mock_closeout.final_no_submit_archive import render_report
    archive = create_archive()
    report = render_report(archive)
    assert "FINAL_NO_SUBMIT_ARCHIVE_READY" in report
    assert "REAL_TESTNET_SUBMIT_NOT_ALLOWED" in report
    assert "REAL_TRADING_NOT_ALLOWED" in report
