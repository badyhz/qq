"""Tests for research safety regression report — T8561-T8600.

All flags, wrong flag, missing flag tests.
"""
from __future__ import annotations

import pytest
from core.research_safety_regression_report import build_safety_regression_report


class TestSafetyRegressionReportNormal:
    def test_all_correct(self):
        r = build_safety_regression_report()
        assert r["verdict"] == "PASS"
        assert r["flags_correct"] is True

    def test_report_has_safety_flags(self):
        r = build_safety_regression_report()
        assert r["release_hold"] == "HOLD"
        assert r["advisory_only"] is True
        assert r["human_review_required"] is True


class TestSafetyRegressionReportAdversarial:
    def test_wrong_hold(self):
        r = build_safety_regression_report(release_hold="BAD")
        assert r["verdict"] == "FAIL"

    def test_frozen_violation(self):
        r = build_safety_regression_report(frozen_violations=("file.py",))
        assert r["verdict"] == "FAIL"

    def test_forbidden_imports(self):
        r = build_safety_regression_report(forbidden_imports=("binance",))
        assert r["verdict"] == "FAIL"

    def test_git_add_dot(self):
        r = build_safety_regression_report(git_add_dot=True)
        assert r["verdict"] in ("FAIL", "PARTIAL")


class TestSafetyRegressionReportSafetyBoundary:
    def test_report_safety(self):
        r = build_safety_regression_report()
        assert r["release_hold"] == "HOLD"
        assert r["advisory_only"] is True
        assert r["human_review_required"] is True
