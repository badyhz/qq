"""Tests for data quality deep audit rows — T5281-T5310.

Valid, edge, corrupted, deterministic tests.
"""
from __future__ import annotations

import pytest
from core.data_quality_deep_audit import (
    audit_ohlcv_rows, build_audit_result, audit_result_to_dict,
    DataQualityFinding,
)


def _make_bar(o=100, h=110, l=90, c=105, v=1000, ts=1):
    return {"timestamp": ts, "open": o, "high": h, "low": l, "close": c, "volume": v}


class TestAuditRowsNormal:
    def test_valid_bars_no_findings(self):
        bars = [_make_bar() for _ in range(10)]
        findings = audit_ohlcv_rows(bars)
        assert findings == ()

    def test_audit_result_pass(self):
        result = build_audit_result((), total_rows=10)
        assert result.verdict == "PASS"
        assert result.total_findings == 0

    def test_audit_result_to_dict(self):
        result = build_audit_result((), total_rows=5)
        d = audit_result_to_dict(result)
        assert d["verdict"] == "PASS"


class TestAuditRowsEdge:
    def test_empty_bars(self):
        findings = audit_ohlcv_rows([])
        assert findings == ()

    def test_single_bar(self):
        findings = audit_ohlcv_rows([_make_bar()])
        assert findings == ()

    def test_zero_volume_warning(self):
        bars = [_make_bar(v=0)]
        findings = audit_ohlcv_rows(bars)
        assert any(f.reason_code == "ZERO_VOLUME" for f in findings)
        assert any(not f.block_promotion for f in findings)


class TestAuditRowsAdversarial:
    def test_impossible_ohlc_low_gt_high(self):
        bars = [_make_bar(l=200, h=100)]
        findings = audit_ohlcv_rows(bars)
        assert any(f.reason_code == "IMPOSSIBLE_OHLC" for f in findings)

    def test_missing_field(self):
        bars = [{"timestamp": 1, "open": 100}]  # missing high, low, close, volume
        findings = audit_ohlcv_rows(bars)
        assert any(f.reason_code == "MISSING_OHLCV_FIELDS" for f in findings)

    def test_nan_value(self):
        bars = [_make_bar(o=float("nan"))]
        findings = audit_ohlcv_rows(bars)
        assert any(f.reason_code == "NAN_METRICS" for f in findings)

    def test_hard_blocks_promotion(self):
        bars = [_make_bar(l=200, h=100)]
        result = build_audit_result(audit_ohlcv_rows(bars), total_rows=1)
        assert result.verdict == "FAIL"
        assert len(result.hard_blocks) > 0


class TestAuditRowsDeterministic:
    def test_deterministic_findings(self):
        bars = [_make_bar(v=0), _make_bar(l=200, h=100)]
        f1 = audit_ohlcv_rows(bars, symbol="BTC", timeframe="5m")
        f2 = audit_ohlcv_rows(bars, symbol="BTC", timeframe="5m")
        assert len(f1) == len(f2)


class TestAuditRowsSafetyBoundary:
    def test_no_network(self):
        import core.data_quality_deep_audit as mod
        src = open(mod.__file__).read()
        assert "requests" not in src
        assert "urllib" not in src
