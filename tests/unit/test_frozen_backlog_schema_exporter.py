"""T1801 - Frozen Backlog Schema Exporter tests.

Tests for core.frozen_backlog_schema_exporter.
Pure schema structure validation. No I/O. No network.
"""
from __future__ import annotations

import pytest

from core.frozen_backlog_schema_exporter import (
    export_audit_schema,
    export_diff_schema,
    export_report_schema,
    export_snapshot_schema,
    export_verdict_schema,
)


def _assert_dict_schema(schema: dict, required_keys: list[str]) -> None:
    """Assert schema is a dict with required top-level keys."""
    assert isinstance(schema, dict)
    for key in required_keys:
        assert key in schema, f"Missing top-level key: {key}"


def _assert_has_definitions(schema: dict, definition_names: list[str]) -> None:
    """Assert schema has expected definitions."""
    defs = schema.get("definitions", {})
    for name in definition_names:
        assert name in defs, f"Missing definition: {name}"


# --- Report schema ---


def test_report_schema_top_level():
    schema = export_report_schema()
    _assert_dict_schema(schema, ["$schema", "title", "type", "required", "properties", "definitions"])


def test_report_schema_required_keys():
    schema = export_report_schema()
    assert "summary" in schema["required"]
    assert "records" in schema["required"]


def test_report_schema_definitions():
    schema = export_report_schema()
    _assert_has_definitions(schema, ["FrozenBacklogReportSummary", "FrozenBacklogReportRecord"])


def test_report_schema_summary_fields():
    schema = export_report_schema()
    summary_props = schema["definitions"]["FrozenBacklogReportSummary"]["properties"]
    expected = {
        "summary_id", "total_files", "high_risk_count", "medium_risk_count",
        "release_hold", "no_live", "no_submit", "no_exchange",
        "no_runtime_integration", "no_planner_integration",
    }
    assert set(summary_props.keys()) == expected


def test_report_schema_record_fields():
    schema = export_report_schema()
    record_props = schema["definitions"]["FrozenBacklogReportRecord"]["properties"]
    expected = {
        "record_id", "file_path", "risk_class", "category",
        "allowed_actions", "forbidden_actions", "required_evidence",
        "readiness_score", "unlock_recommendation", "release_hold",
    }
    assert set(record_props.keys()) == expected


def test_report_schema_deterministic():
    s1 = export_report_schema()
    s2 = export_report_schema()
    assert s1 == s2


# --- Snapshot schema ---


def test_snapshot_schema_top_level():
    schema = export_snapshot_schema()
    _assert_dict_schema(schema, ["$schema", "title", "type", "required", "properties"])


def test_snapshot_schema_required_keys():
    schema = export_snapshot_schema()
    assert "snapshot_id" in schema["required"]
    assert "report_data" in schema["required"]
    assert "created_at_iso" in schema["required"]
    assert "version" in schema["required"]


# --- Diff schema ---


def test_diff_schema_top_level():
    schema = export_diff_schema()
    _assert_dict_schema(schema, ["$schema", "title", "type", "required", "properties", "definitions"])


def test_diff_schema_required_keys():
    schema = export_diff_schema()
    expected = {
        "diff_id", "before_snapshot_id", "after_snapshot_id",
        "added_files", "removed_files",
        "risk_class_changes", "category_changes",
        "recommendation_changes", "safety_flag_changes", "hold_changes",
    }
    assert set(schema["required"]) == expected


def test_diff_schema_definitions():
    schema = export_diff_schema()
    _assert_has_definitions(schema, ["FrozenDiffChange"])


# --- Verdict schema ---


def test_verdict_schema_top_level():
    schema = export_verdict_schema()
    _assert_dict_schema(schema, ["$schema", "title", "type", "required", "properties"])


def test_verdict_schema_required_keys():
    schema = export_verdict_schema()
    assert set(schema["required"]) == {"verdict", "notes", "changed_fields", "risk_level"}


def test_verdict_schema_verdict_enum():
    schema = export_verdict_schema()
    assert schema["properties"]["verdict"]["enum"] == ["PASS", "PARTIAL", "FAIL"]


def test_verdict_schema_risk_level_enum():
    schema = export_verdict_schema()
    assert schema["properties"]["risk_level"]["enum"] == ["SAFE", "CAUTION", "CRITICAL"]


# --- Audit schema ---


def test_audit_schema_top_level():
    schema = export_audit_schema()
    _assert_dict_schema(schema, ["$schema", "title", "type", "required", "properties", "definitions"])


def test_audit_schema_required_keys():
    schema = export_audit_schema()
    expected = {
        "audit_id", "validation_result", "diff_summary", "verdict", "snapshot_ids",
    }
    assert set(schema["required"]) == expected


def test_audit_schema_validation_result_fields():
    schema = export_audit_schema()
    vr = schema["properties"]["validation_result"]
    assert set(vr["required"]) == {
        "is_valid", "checks_passed", "checks_failed", "error_message",
    }


def test_audit_schema_deterministic():
    s1 = export_audit_schema()
    s2 = export_audit_schema()
    assert s1 == s2
