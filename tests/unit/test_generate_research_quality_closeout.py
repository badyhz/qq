"""Tests for generate research quality closeout — T8841-T8880.

PASS/PARTIAL/FAIL closeout tests.
"""
from __future__ import annotations

import pytest
from core.research_quality_closeout import generate_closeout_report, build_closeout_data, ADVISORY_REMINDER


class TestCloseoutNormal:
    def test_generate_pass_report(self):
        report = generate_closeout_report(verdict="PASS", seed=42)
        assert "PASS" in report
        assert "advisory" in report.lower()

    def test_generate_fail_report(self):
        report = generate_closeout_report(verdict="FAIL", seed=42)
        assert "FAIL" in report

    def test_build_closeout_data(self):
        data = build_closeout_data("PASS", seed=42)
        assert data["verdict"] == "PASS"
        assert data["release_hold"] == "HOLD"


class TestCloseoutEdge:
    def test_with_artifacts(self):
        report = generate_closeout_report(verdict="PASS", artifacts=["a.json", "b.json"], seed=42)
        assert "a.json" in report


class TestCloseoutSafetyBoundary:
    def test_advisory_reminder_present(self):
        report = generate_closeout_report(verdict="PASS", seed=42)
        assert "advisory" in report.lower() or "ADVISORY" in report

    def test_closeout_data_safety(self):
        data = build_closeout_data("PASS", seed=42)
        assert data["release_hold"] == "HOLD"
        assert data["advisory_only"] is True
        assert data["human_review_required"] is True
