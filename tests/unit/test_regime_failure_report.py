"""Tests for regime failure report — T7601-T7640.

Single regime failure, concentration tests.
"""
from __future__ import annotations

import pytest
from core.regime_failure_report import detect_regime_failure, build_regime_failure_report


class TestRegimeFailureNormal:
    def test_no_failure(self):
        result = detect_regime_failure({"TREND": 0.1, "CHOP": 0.05})
        assert not result["has_failure"]

    def test_failure_detected(self):
        result = detect_regime_failure({"TREND": 0.1, "CHOP": -0.1})
        assert result["has_failure"]


class TestRegimeFailureAdversarial:
    def test_concentration_warning(self):
        report = build_regime_failure_report("s", {"TREND": 0.9, "CHOP": 0.1}, seed=42)
        assert len(report["warnings"]) > 0


class TestRegimeFailureSafetyBoundary:
    def test_report_safety(self):
        report = build_regime_failure_report("s", {}, seed=42)
        assert report["release_hold"] == "HOLD"
        assert report["advisory_only"] is True
