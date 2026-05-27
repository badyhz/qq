"""Tests for portfolio overlap risk — T6721-T6760.

No-overlap, high-overlap, collision fixtures.
"""
from __future__ import annotations

import pytest
from core.portfolio_overlap_risk import compute_overlap, build_overlap_risk_report


class TestOverlapRiskNormal:
    def test_no_overlap(self):
        overlap = compute_overlap([0, 0, 0], [1, 1, 1], "a", "b")
        assert overlap.overlap_score == 0.0

    def test_full_overlap(self):
        overlap = compute_overlap([1, 1, 1], [1, 1, 1], "a", "b")
        assert overlap.overlap_score == 1.0


class TestOverlapRiskEdge:
    def test_empty_signals(self):
        overlap = compute_overlap([], [], "a", "b")
        assert overlap.overlap_score == 0.0


class TestOverlapRiskSafetyBoundary:
    def test_report_safety(self):
        report = build_overlap_risk_report([], seed=42)
        assert report["release_hold"] == "HOLD"
        assert report["advisory_only"] is True
