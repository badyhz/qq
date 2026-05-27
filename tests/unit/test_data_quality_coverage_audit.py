"""Tests for data quality coverage audit — T5341-T5370.

Fresh, stale, partial, insufficient coverage tests.
"""
from __future__ import annotations

import pytest
from core.data_quality_coverage_audit import assess_coverage, audit_coverage, coverage_audit_to_dict


class TestCoverageAuditNormal:
    def test_fresh_coverage(self):
        s = assess_coverage(100, "BTCUSDT", "5m")
        assert s.coverage_status == "FRESH"

    def test_audit_coverage(self):
        results = audit_coverage({("BTCUSDT", "5m"): 100, ("ETHUSDT", "5m"): 50})
        assert len(results) == 2


class TestCoverageAuditEdge:
    def test_empty_coverage(self):
        s = assess_coverage(0, "BTCUSDT", "5m")
        assert s.coverage_status == "EMPTY"

    def test_insufficient_coverage(self):
        s = assess_coverage(3, "BTCUSDT", "5m", min_rows=10)
        assert s.coverage_status == "INSUFFICIENT"


class TestCoverageAuditAdversarial:
    def test_partial_coverage(self):
        s = assess_coverage(15, "BTCUSDT", "5m", min_rows=10)
        assert s.coverage_status == "PARTIAL"


class TestCoverageAuditDeterministic:
    def test_deterministic(self):
        results = audit_coverage({("BTCUSDT", "5m"): 100})
        d1 = coverage_audit_to_dict(results)
        d2 = coverage_audit_to_dict(results)
        assert d1 == d2
