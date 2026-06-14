"""Integration test: field-test acceptance criteria."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_adapter_spec.field_test_acceptance_criteria import get_criteria, render_report
from src.runtime_integrations.testnet_adapter_spec.field_test_validator import validate_criteria


def test_criteria_present():
    criteria = get_criteria()
    assert len(criteria) >= 15


def test_criteria_report_flags():
    criteria = get_criteria()
    report = render_report(criteria)
    assert "CRITERIA_ONLY" in report
    assert "field_test_executed=false" in report
    assert "submit_allowed=false" in report


def test_criteria_validator_passes():
    criteria = get_criteria()
    report = render_report(criteria)
    checks = validate_criteria(report)
    passed = sum(1 for c in checks if c.passed)
    assert passed == len(checks)


def test_criteria_has_kill_switch():
    criteria = get_criteria()
    report = render_report(criteria)
    assert "kill switch" in report.lower()
