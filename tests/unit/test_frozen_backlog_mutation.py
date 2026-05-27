"""T1831 - Frozen Backlog Negative / Mutation Test Suite.

Tests that mutate JSON report fields and verify validator/diff/verdict
fail correctly. Each test copies valid fixture, mutates one field,
runs validator/diff/verdict, asserts expected failure/detection.
No I/O beyond fixture reads. No network.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from core.frozen_backlog_report_validator import validate_report_data
from core.frozen_backlog_diff_engine import diff_reports, has_changes
from core.frozen_backlog_verdict_engine import compute_verdict
from core.frozen_backlog_validation_result import build_validation_result

_FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "frozen_backlog_review"


def _load_valid_report() -> dict:
    """Load the valid report fixture."""
    path = _FIXTURES_DIR / "valid_report.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _mutate(data: dict, path: list, new_value) -> dict:
    """Mutate a nested field by path (list of keys). Returns mutated copy."""
    d = copy.deepcopy(data)
    obj = d
    for key in path[:-1]:
        obj = obj[key]
    obj[path[-1]] = new_value
    return d


# --- Validation mutation tests ---


def test_mutation_total_files_changed():
    data = _mutate(_load_valid_report(), ["summary", "total_files"], 99)
    result = validate_report_data(data)
    assert result.is_valid is False
    assert "total_files_count" in result.checks_failed


def test_mutation_high_risk_count_changed():
    data = _mutate(_load_valid_report(), ["summary", "high_risk_count"], 0)
    result = validate_report_data(data)
    assert result.is_valid is False
    assert "high_risk_count" in result.checks_failed


def test_mutation_medium_risk_count_changed():
    data = _mutate(_load_valid_report(), ["summary", "medium_risk_count"], 0)
    result = validate_report_data(data)
    assert result.is_valid is False
    assert "medium_risk_count" in result.checks_failed


def test_mutation_release_hold_not_hold():
    data = _mutate(_load_valid_report(), ["summary", "release_hold"], "RELEASED")
    result = validate_report_data(data)
    assert result.is_valid is False
    assert "summary_release_hold" in result.checks_failed


def test_mutation_no_live_false():
    data = _mutate(_load_valid_report(), ["summary", "no_live"], False)
    result = validate_report_data(data)
    assert result.is_valid is False
    assert "safety_no_live" in result.checks_failed


def test_mutation_no_submit_false():
    data = _mutate(_load_valid_report(), ["summary", "no_submit"], False)
    result = validate_report_data(data)
    assert result.is_valid is False
    assert "safety_no_submit" in result.checks_failed


def test_mutation_no_exchange_false():
    data = _mutate(_load_valid_report(), ["summary", "no_exchange"], False)
    result = validate_report_data(data)
    assert result.is_valid is False
    assert "safety_no_exchange" in result.checks_failed


def test_mutation_missing_required_evidence():
    data = copy.deepcopy(_load_valid_report())
    del data["records"][0]["required_evidence"]
    result = validate_report_data(data)
    assert result.is_valid is False
    assert "record_0_fields" in result.checks_failed


def test_mutation_path_removed_from_records():
    data = copy.deepcopy(_load_valid_report())
    del data["records"][0]["file_path"]
    result = validate_report_data(data)
    assert result.is_valid is False
    assert "record_0_fields" in result.checks_failed


# --- Diff mutation tests ---


def test_mutation_risk_class_changed_detected_by_diff():
    """Mutate risk_class in one record and verify diff detects it."""
    before = _load_valid_report()
    after = copy.deepcopy(before)
    after["records"][0]["risk_class"] = "MEDIUM"
    diff = diff_reports(before, after)
    assert has_changes(diff)
    assert len(diff.risk_class_changes) == 1
    assert diff.risk_class_changes[0].file_path == "core/live_runner.py"
    assert diff.risk_class_changes[0].old_value == "HIGH"
    assert diff.risk_class_changes[0].new_value == "MEDIUM"


def test_mutation_category_changed_detected_by_diff():
    """Mutate category in one record and verify diff detects it."""
    before = _load_valid_report()
    after = copy.deepcopy(before)
    after["records"][5]["category"] = "FLATTEN"
    diff = diff_reports(before, after)
    assert has_changes(diff)
    assert len(diff.category_changes) == 1
    assert diff.category_changes[0].old_value == "TESTNET_SMOKE"
    assert diff.category_changes[0].new_value == "FLATTEN"


def test_mutation_unlock_recommendation_changed_detected_by_diff():
    """Mutate unlock_recommendation and verify diff detects it."""
    before = _load_valid_report()
    after = copy.deepcopy(before)
    after["records"][0]["unlock_recommendation"] = "PROMOTE"
    diff = diff_reports(before, after)
    assert has_changes(diff)
    assert len(diff.recommendation_changes) == 1
    assert diff.recommendation_changes[0].old_value == "HOLD"
    assert diff.recommendation_changes[0].new_value == "PROMOTE"


# --- Verdict mutation tests ---


def test_mutation_validation_failure_gives_fail_verdict():
    """Validation failure should produce FAIL verdict."""
    data = _mutate(_load_valid_report(), ["summary", "total_files"], 99)
    validation = validate_report_data(data)
    before = _load_valid_report()
    diff = diff_reports(before, data)
    verdict = compute_verdict(diff, validation)
    assert verdict.verdict == "FAIL"
    assert verdict.risk_level == "CRITICAL"


def test_mutation_risk_class_change_gives_fail_verdict():
    """Risk class change should produce FAIL verdict."""
    before = _load_valid_report()
    after = copy.deepcopy(before)
    after["records"][0]["risk_class"] = "MEDIUM"
    validation = validate_report_data(after)
    diff = diff_reports(before, after)
    verdict = compute_verdict(diff, validation)
    assert verdict.verdict == "FAIL"
    assert verdict.risk_level == "CRITICAL"


def test_mutation_category_change_gives_partial_verdict():
    """Category change only should produce PARTIAL verdict."""
    before = _load_valid_report()
    after = copy.deepcopy(before)
    after["records"][0]["category"] = "FLATTEN"
    validation = validate_report_data(after)
    diff = diff_reports(before, after)
    verdict = compute_verdict(diff, validation)
    assert verdict.verdict == "PARTIAL"
    assert verdict.risk_level == "CAUTION"


def test_mutation_no_change_gives_pass_verdict():
    """No changes should produce PASS verdict."""
    before = _load_valid_report()
    after = copy.deepcopy(before)
    validation = validate_report_data(after)
    diff = diff_reports(before, after)
    verdict = compute_verdict(diff, validation)
    assert verdict.verdict == "PASS"
    assert verdict.risk_level == "SAFE"


def test_mutation_file_added_gives_fail_verdict():
    """File added should produce FAIL verdict."""
    before = _load_valid_report()
    after = copy.deepcopy(before)
    extra = copy.deepcopy(after["records"][0])
    extra["record_id"] = "report-9999"
    extra["file_path"] = "scripts/extra_file.py"
    after["records"].append(extra)
    after["summary"]["total_files"] = 23
    validation = validate_report_data(after)
    diff = diff_reports(before, after)
    verdict = compute_verdict(diff, validation)
    assert verdict.verdict == "FAIL"


def test_mutation_hold_change_gives_fail_verdict():
    """release_hold change should produce FAIL verdict."""
    before = _load_valid_report()
    after = copy.deepcopy(before)
    after["records"][0]["release_hold"] = "RELEASED"
    validation = validate_report_data(after)
    diff = diff_reports(before, after)
    verdict = compute_verdict(diff, validation)
    assert verdict.verdict == "FAIL"
    assert "release_hold" in str(verdict.changed_fields)
