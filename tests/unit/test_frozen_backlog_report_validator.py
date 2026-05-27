"""T1604 - Frozen Backlog Report Validator tests.

Tests for core.frozen_backlog_report_validator.
Pure validation logic. No network. No live. No submit.
"""
from __future__ import annotations

import copy

import pytest

from core.frozen_backlog_report_validator import validate_report_data

# --- Canonical correct report dict ---

_CORRECT_SUMMARY = {
    "summary_id": "summary-frozen-backlog-batch1",
    "total_files": 22,
    "high_risk_count": 9,
    "medium_risk_count": 13,
    "release_hold": "HOLD",
    "no_live": True,
    "no_submit": True,
    "no_exchange": True,
    "no_runtime_integration": True,
    "no_planner_integration": True,
}

_CORRECT_RECORD_TEMPLATE = {
    "record_id": "report-0000",
    "file_path": "core/live_runner.py",
    "risk_class": "HIGH",
    "category": "LIVE_RUNNER",
    "allowed_actions": ["review", "read", "lint", "typecheck"],
    "forbidden_actions": ["execute", "import_runtime", "submit", "modify"],
    "required_evidence": ["dry_run_log", "risk_review", "human_approval"],
    "readiness_score": 0.0,
    "unlock_recommendation": "HOLD",
    "release_hold": "HOLD",
}


def _make_correct_report() -> dict:
    """Build a valid 22-record report dict."""
    records = []
    for i in range(22):
        rec = copy.deepcopy(_CORRECT_RECORD_TEMPLATE)
        rec["record_id"] = f"report-{i:04d}"
        records.append(rec)
    return {
        "summary": copy.deepcopy(_CORRECT_SUMMARY),
        "records": records,
    }


# --- Tests ---


def test_valid_report_is_valid():
    data = _make_correct_report()
    result = validate_report_data(data)
    assert result.is_valid is True
    assert len(result.checks_failed) == 0


def test_wrong_total_files():
    data = _make_correct_report()
    data["summary"]["total_files"] = 99
    result = validate_report_data(data)
    assert result.is_valid is False
    assert "total_files_count" in result.checks_failed


def test_wrong_high_risk_count():
    data = _make_correct_report()
    data["summary"]["high_risk_count"] = 0
    result = validate_report_data(data)
    assert result.is_valid is False
    assert "high_risk_count" in result.checks_failed


def test_wrong_medium_risk_count():
    data = _make_correct_report()
    data["summary"]["medium_risk_count"] = 0
    result = validate_report_data(data)
    assert result.is_valid is False
    assert "medium_risk_count" in result.checks_failed


def test_release_hold_not_hold():
    data = _make_correct_report()
    data["summary"]["release_hold"] = "RELEASED"
    result = validate_report_data(data)
    assert result.is_valid is False
    assert "summary_release_hold" in result.checks_failed


def test_no_live_false():
    data = _make_correct_report()
    data["summary"]["no_live"] = False
    result = validate_report_data(data)
    assert result.is_valid is False
    assert "safety_no_live" in result.checks_failed


def test_no_submit_false():
    data = _make_correct_report()
    data["summary"]["no_submit"] = False
    result = validate_report_data(data)
    assert result.is_valid is False
    assert "safety_no_submit" in result.checks_failed


def test_no_exchange_false():
    data = _make_correct_report()
    data["summary"]["no_exchange"] = False
    result = validate_report_data(data)
    assert result.is_valid is False
    assert "safety_no_exchange" in result.checks_failed


def test_missing_record_field():
    data = _make_correct_report()
    del data["records"][0]["release_hold"]
    result = validate_report_data(data)
    assert result.is_valid is False
    assert "record_0_fields" in result.checks_failed


def test_record_wrong_release_hold():
    data = _make_correct_report()
    data["records"][5]["release_hold"] = "OPEN"
    result = validate_report_data(data)
    assert result.is_valid is False
    assert "record_5_release_hold" in result.checks_failed


def test_extra_records():
    data = _make_correct_report()
    data["records"].append(copy.deepcopy(_CORRECT_RECORD_TEMPLATE))
    result = validate_report_data(data)
    assert result.is_valid is False
    assert "records_count_match" in result.checks_failed


def test_missing_summary_key():
    data = {"records": []}
    result = validate_report_data(data)
    assert result.is_valid is False
    assert "missing_summary_key" in result.checks_failed


def test_missing_records_key():
    data = {"summary": copy.deepcopy(_CORRECT_SUMMARY)}
    result = validate_report_data(data)
    assert result.is_valid is False
    assert "missing_records_key" in result.checks_failed


def test_deterministic_output():
    data = _make_correct_report()
    r1 = validate_report_data(data)
    r2 = validate_report_data(data)
    assert r1.is_valid == r2.is_valid
    assert r1.checks_passed == r2.checks_passed
    assert r1.checks_failed == r2.checks_failed
    assert r1.error_message == r2.error_message
