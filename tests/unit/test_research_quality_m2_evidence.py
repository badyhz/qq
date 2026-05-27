"""Tests for M2 evidence — T5561-T5600.

Data quality evidence completeness tests.
"""
from __future__ import annotations

import pytest
from core.data_quality_deep_audit import audit_ohlcv_rows, build_audit_result
from core.data_quality_deep_audit_timestamps import audit_timestamps
from core.data_quality_coverage_audit import assess_coverage
from core.data_quality_fixture_corruption import check_fixture_corruption
from core.data_quality_deep_audit_report import build_data_quality_report


class TestM2Evidence:
    def test_audit_rows(self):
        findings = audit_ohlcv_rows([])
        assert findings == ()

    def test_audit_timestamps(self):
        findings = audit_timestamps([])
        assert findings == ()

    def test_coverage_assessment(self):
        s = assess_coverage(100, "BTC", "5m")
        assert s.coverage_status == "FRESH"

    def test_report_safety(self):
        result = build_audit_result((), total_rows=0)
        report = build_data_quality_report(result, seed=42)
        assert report["release_hold"] == "HOLD"
        assert report["advisory_only"] is True
