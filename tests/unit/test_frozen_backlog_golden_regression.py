"""T1821 - Frozen Backlog Golden Snapshot Regression Tests.

Generate report from FROZEN_BACKLOG_INVENTORY and compare structure
to golden expected values. Deterministic. Not brittle on formatting.
"""
from __future__ import annotations

import pytest

from core.frozen_backlog_inventory import FROZEN_BACKLOG_INVENTORY
from core.frozen_backlog_report_materializer import materialize_full_report
from core.frozen_backlog_report_json import render_summary_dict, render_record_dict

# --- Expected constants from inventory ---

_EXPECTED_TOTAL_FILES = 22
_EXPECTED_HIGH_RISK_COUNT = 9
_EXPECTED_MEDIUM_RISK_COUNT = 13
_EXPECTED_RELEASE_HOLD = "HOLD"

_EXPECTED_SUMMARY_KEYS = {
    "summary_id", "total_files", "high_risk_count", "medium_risk_count",
    "release_hold", "no_live", "no_submit", "no_exchange",
    "no_runtime_integration", "no_planner_integration",
}

_EXPECTED_RECORD_KEYS = {
    "record_id", "file_path", "risk_class", "category",
    "allowed_actions", "forbidden_actions", "required_evidence",
    "readiness_score", "unlock_recommendation", "release_hold",
}

_EXPECTED_HIGH_RISK_CATEGORIES = {
    "LIVE_RUNNER", "LIVE_PLAYBOOK", "SUBMIT", "TESTNET_SMOKE",
    "FLATTEN", "REPLAY_SUBMIT",
}

_EXPECTED_MEDIUM_RISK_CATEGORIES = {
    "OPERATIONAL_SHADOW", "VERIFICATION",
}


@pytest.fixture
def report():
    """Generate report from real inventory."""
    summary, records = materialize_full_report(FROZEN_BACKLOG_INVENTORY)
    return summary, records


@pytest.fixture
def report_dict(report):
    """Render report as dict."""
    summary, records = report
    return {
        "summary": render_summary_dict(summary),
        "records": [render_record_dict(r) for r in records],
    }


# --- Structure tests ---


def test_golden_total_files(report):
    summary, _ = report
    assert summary.total_files == _EXPECTED_TOTAL_FILES


def test_golden_high_risk_count(report):
    summary, _ = report
    assert summary.high_risk_count == _EXPECTED_HIGH_RISK_COUNT


def test_golden_medium_risk_count(report):
    summary, _ = report
    assert summary.medium_risk_count == _EXPECTED_MEDIUM_RISK_COUNT


def test_golden_release_hold(report):
    summary, _ = report
    assert summary.release_hold == _EXPECTED_RELEASE_HOLD


def test_golden_record_count_matches_total(report):
    summary, records = report
    assert len(records) == summary.total_files


def test_golden_inventory_record_count(report):
    _, records = report
    assert len(records) == len(FROZEN_BACKLOG_INVENTORY.records)


# --- Summary field tests ---


def test_golden_summary_has_all_keys(report_dict):
    summary = report_dict["summary"]
    assert set(summary.keys()) == _EXPECTED_SUMMARY_KEYS


def test_golden_safety_flags_all_true(report_dict):
    summary = report_dict["summary"]
    for flag in ("no_live", "no_submit", "no_exchange",
                 "no_runtime_integration", "no_planner_integration"):
        assert summary[flag] is True, f"{flag} should be True"


# --- Record field tests ---


def test_golden_all_records_have_required_fields(report_dict):
    records = report_dict["records"]
    for record in records:
        assert set(record.keys()) == _EXPECTED_RECORD_KEYS


def test_golden_all_records_have_hold(report):
    _, records = report
    for record in records:
        assert record.release_hold == _EXPECTED_RELEASE_HOLD


def test_golden_all_records_have_hold_in_dict(report_dict):
    records = report_dict["records"]
    for record in records:
        assert record["release_hold"] == _EXPECTED_RELEASE_HOLD


# --- Forbidden action pattern tests ---


def test_golden_no_records_have_forbidden_live_imports(report_dict):
    """No record should have execute/submit as allowed actions."""
    records = report_dict["records"]
    for record in records:
        allowed = set(record["allowed_actions"])
        assert "execute" not in allowed, f"{record['file_path']} allows execute"
        assert "submit" not in allowed, f"{record['file_path']} allows submit"


def test_golden_high_risk_records_have_human_approval_evidence(report):
    """HIGH risk records require human_approval evidence."""
    _, records = report
    for record in records:
        if record.risk_class == "HIGH":
            assert "human_approval" in record.required_evidence


def test_golden_high_risk_readiness_is_zero(report):
    """HIGH risk records have readiness_score=0.0."""
    _, records = report
    for record in records:
        if record.risk_class == "HIGH":
            assert record.readiness_score == 0.0


def test_golden_unlock_recommendation_is_hold(report):
    """All records have unlock_recommendation=HOLD."""
    _, records = report
    for record in records:
        assert record.unlock_recommendation == "HOLD"


# --- Category coverage tests ---


def test_golden_high_risk_categories_present(report):
    """Verify expected HIGH risk categories are in the report."""
    _, records = report
    high_cats = {r.category for r in records if r.risk_class == "HIGH"}
    assert high_cats == _EXPECTED_HIGH_RISK_CATEGORIES


def test_golden_medium_risk_categories_present(report):
    """Verify expected MEDIUM risk categories are in the report."""
    _, records = report
    med_cats = {r.category for r in records if r.risk_class == "MEDIUM"}
    assert med_cats == _EXPECTED_MEDIUM_RISK_CATEGORIES


# --- Determinism test ---


def test_golden_report_is_deterministic(report_dict):
    """Two generations produce identical dicts."""
    summary, records = materialize_full_report(FROZEN_BACKLOG_INVENTORY)
    d2 = {
        "summary": render_summary_dict(summary),
        "records": [render_record_dict(r) for r in records],
    }
    assert report_dict == d2
