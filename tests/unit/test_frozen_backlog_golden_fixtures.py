"""T1815 - Frozen Backlog Golden Fixture tests.

Verify all fixtures exist, are valid JSON, and have expected top-level keys.
No I/O beyond fixture reads. No network.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

_FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "frozen_backlog_review"

_EXPECTED_FIXTURES = [
    "valid_report.json",
    "invalid_counts.json",
    "release_hold_changed.json",
    "risk_class_changed.json",
    "safety_flag_false.json",
    "file_removed.json",
    "file_added.json",
    "valid_snapshot.json",
    "valid_diff.json",
]


def _load_fixture(name: str) -> dict:
    """Load a fixture by name. Raises on missing or invalid JSON."""
    path = _FIXTURES_DIR / name
    assert path.exists(), f"Fixture not found: {path}"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data, dict), f"Fixture {name} is not a dict"
    return data


# --- Existence tests ---


@pytest.mark.parametrize("filename", _EXPECTED_FIXTURES)
def test_fixture_exists(filename: str):
    path = _FIXTURES_DIR / filename
    assert path.exists(), f"Missing fixture: {filename}"


# --- Valid JSON tests ---


@pytest.mark.parametrize("filename", _EXPECTED_FIXTURES)
def test_fixture_is_valid_json(filename: str):
    data = _load_fixture(filename)
    assert isinstance(data, dict)


# --- Top-level key tests ---


def test_valid_report_has_summary_and_records():
    data = _load_fixture("valid_report.json")
    assert "summary" in data
    assert "records" in data


def test_valid_report_summary_keys():
    data = _load_fixture("valid_report.json")
    summary = data["summary"]
    expected = {
        "summary_id", "total_files", "high_risk_count", "medium_risk_count",
        "release_hold", "no_live", "no_submit", "no_exchange",
        "no_runtime_integration", "no_planner_integration",
    }
    assert set(summary.keys()) == expected


def test_valid_report_record_keys():
    data = _load_fixture("valid_report.json")
    for record in data["records"]:
        expected = {
            "record_id", "file_path", "risk_class", "category",
            "allowed_actions", "forbidden_actions", "required_evidence",
            "readiness_score", "unlock_recommendation", "release_hold",
        }
        assert set(record.keys()) == expected


def test_invalid_counts_has_summary_and_records():
    data = _load_fixture("invalid_counts.json")
    assert "summary" in data
    assert "records" in data


def test_release_hold_changed_has_summary_and_records():
    data = _load_fixture("release_hold_changed.json")
    assert "summary" in data
    assert "records" in data
    assert data["summary"]["release_hold"] != "HOLD"


def test_risk_class_changed_has_summary_and_records():
    data = _load_fixture("risk_class_changed.json")
    assert "summary" in data
    assert "records" in data
    assert data["records"][0]["risk_class"] == "MEDIUM"


def test_safety_flag_false_has_summary_and_records():
    data = _load_fixture("safety_flag_false.json")
    assert "summary" in data
    assert "records" in data
    assert data["summary"]["no_live"] is False


def test_file_removed_has_summary_and_records():
    data = _load_fixture("file_removed.json")
    assert "summary" in data
    assert "records" in data
    assert data["summary"]["total_files"] == 21


def test_file_added_has_summary_and_records():
    data = _load_fixture("file_added.json")
    assert "summary" in data
    assert "records" in data
    assert data["summary"]["total_files"] == 23


def test_valid_snapshot_keys():
    data = _load_fixture("valid_snapshot.json")
    expected = {"snapshot_id", "report_data", "created_at_iso", "version"}
    assert set(data.keys()) == expected


def test_valid_diff_keys():
    data = _load_fixture("valid_diff.json")
    expected = {
        "diff_id", "before_snapshot_id", "after_snapshot_id",
        "added_files", "removed_files",
        "risk_class_changes", "category_changes",
        "recommendation_changes", "safety_flag_changes", "hold_changes",
    }
    assert set(data.keys()) == expected


def test_valid_diff_has_no_changes():
    data = _load_fixture("valid_diff.json")
    assert data["added_files"] == []
    assert data["removed_files"] == []
    assert data["risk_class_changes"] == []
    assert data["category_changes"] == []
    assert data["recommendation_changes"] == []
    assert data["safety_flag_changes"] == []
    assert data["hold_changes"] == []
