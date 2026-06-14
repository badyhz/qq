"""Integration test: review navigation report."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_mock_review.review_navigation_report import (
    create_report, search_entries
)


def test_create_report():
    report = create_report()
    assert len(report.entries) >= 8
    assert report.report_id.startswith("NAV_")


def test_search_entries():
    report = create_report()
    results = search_entries(report, "evidence")
    assert len(results) >= 1


def test_search_safety():
    report = create_report()
    results = search_entries(report, "safety")
    assert len(results) >= 1


def test_search_approval():
    report = create_report()
    results = search_entries(report, "approval")
    assert len(results) >= 1
