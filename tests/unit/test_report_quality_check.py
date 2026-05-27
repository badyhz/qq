"""Tests for report quality check — T7801-T7840.

Complete, missing, empty sections tests.
"""
from __future__ import annotations

import pytest
from core.report_quality_check import (
    check_report_completeness, check_empty_nan_metrics, build_report_quality_check,
)


class TestReportQualityNormal:
    def test_complete_report(self):
        report = {s: True for s in ["summary", "data_quality", "split_leakage"]}
        result = check_report_completeness(report, ["summary", "data_quality", "split_leakage"])
        assert result["complete"]

    def test_clean_metrics(self):
        result = check_empty_nan_metrics({"composite_score": 0.7, "verdict": "PASS", "stability_score": 0.8})
        assert result["clean"]


class TestReportQualityEdge:
    def test_missing_section(self):
        result = check_report_completeness({}, ["summary"])
        assert not result["complete"]
        assert "summary" in result["missing_sections"]


class TestReportQualityAdversarial:
    def test_nan_metric(self):
        result = check_empty_nan_metrics({"composite_score": float("nan")})
        assert not result["clean"]

    def test_empty_metric(self):
        result = check_empty_nan_metrics({"verdict": ""})
        assert not result["clean"]


class TestReportQualityDeterministic:
    def test_build_deterministic(self):
        r1 = build_report_quality_check({"composite_score": 0.7, "verdict": "PASS", "stability_score": 0.8}, seed=42)
        r2 = build_report_quality_check({"composite_score": 0.7, "verdict": "PASS", "stability_score": 0.8}, seed=42)
        r1_copy = {k: v for k, v in r1.items() if k != "generated_at"}
        r2_copy = {k: v for k, v in r2.items() if k != "generated_at"}
        assert r1_copy == r2_copy


class TestReportQualitySafetyBoundary:
    def test_report_safety(self):
        r = build_report_quality_check({}, seed=42)
        assert r["release_hold"] == "HOLD"
        assert r["advisory_only"] is True
