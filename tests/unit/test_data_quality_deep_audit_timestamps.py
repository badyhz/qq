"""Tests for data quality timestamp audit — T5311-T5340.

Gap, duplicate, non-monotonic fixtures.
"""
from __future__ import annotations

import pytest
from core.data_quality_deep_audit_timestamps import audit_timestamps


def _bars(ts_list):
    return [{"timestamp": ts, "open": 1, "high": 2, "low": 0, "close": 1, "volume": 100}
            for ts in ts_list]


class TestTimestampAuditNormal:
    def test_monotonic_no_issues(self):
        findings = audit_timestamps(_bars([1, 2, 3, 4, 5]))
        assert findings == ()

    def test_empty_bars(self):
        findings = audit_timestamps([])
        assert findings == ()


class TestTimestampAuditEdge:
    def test_single_bar(self):
        findings = audit_timestamps(_bars([1]))
        assert findings == ()


class TestTimestampAuditAdversarial:
    def test_duplicate_timestamps(self):
        findings = audit_timestamps(_bars([1, 1, 2, 3]))
        assert any(f.reason_code == "DUPLICATE_TIMESTAMPS" for f in findings)

    def test_non_monotonic(self):
        findings = audit_timestamps(_bars([1, 3, 2, 4]))
        assert any(f.reason_code == "NON_MONOTONIC_TIMESTAMPS" for f in findings)

    def test_gap_detection(self):
        findings = audit_timestamps(_bars([100, 200, 300, 1000]), expected_interval_ms=100)
        assert any(f.reason_code == "MISSING_BARS" for f in findings)


class TestTimestampAuditDeterministic:
    def test_deterministic(self):
        bars = _bars([1, 1, 3, 2])
        f1 = audit_timestamps(bars, symbol="BTC", timeframe="5m")
        f2 = audit_timestamps(bars, symbol="BTC", timeframe="5m")
        assert len(f1) == len(f2)
