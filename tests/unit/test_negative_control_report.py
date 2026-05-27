"""Tests for negative control report — T7241-T7280.

Real-beats-control, real-fails-control, margin tests.
"""
from __future__ import annotations

import pytest
from core.negative_control_report import evaluate_negative_control_margin, build_negative_control_report


class TestNegativeControlReportNormal:
    def test_real_beats_control(self):
        result = evaluate_negative_control_margin(0.5, {"random": 0.1}, min_margin=0.1)
        assert result["passes"]

    def test_build_report(self):
        baselines = {"random": {"score": 0.1, "baseline_type": "random"}}
        report = build_negative_control_report("strat1", 0.5, baselines, min_margin=0.1, seed=42)
        assert report["passes_all_controls"]


class TestNegativeControlReportAdversarial:
    def test_real_fails_control(self):
        result = evaluate_negative_control_margin(0.05, {"random": 0.1}, min_margin=0.1)
        assert not result["passes"]

    def test_insufficient_margin_blocks(self):
        baselines = {"random": {"score": 0.45, "baseline_type": "random"}}
        report = build_negative_control_report("strat1", 0.5, baselines, min_margin=0.1, seed=42)
        assert not report["passes_all_controls"]
        assert "INSUFFICIENT_NEGATIVE_CONTROL_MARGIN" in report["hard_blocks"]


class TestNegativeControlReportSafetyBoundary:
    def test_report_safety(self):
        report = build_negative_control_report("s", 0.5, {}, seed=42)
        assert report["release_hold"] == "HOLD"
        assert report["advisory_only"] is True
