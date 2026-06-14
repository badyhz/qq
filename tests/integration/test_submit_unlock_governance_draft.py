"""Integration test: submit unlock governance draft."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_adapter_spec.submit_unlock_governance import get_items, render_report
from src.runtime_integrations.testnet_adapter_spec.submit_unlock_governance_validator import validate_governance


def test_governance_items_present():
    items = get_items()
    assert len(items) >= 15


def test_governance_report_flags():
    items = get_items()
    report = render_report(items)
    assert "DRAFT_ONLY" in report
    assert "submit_gate_state=LOCKED" in report
    assert "testnet_submit_allowed=false" in report
    assert "real_submit_allowed=false" in report


def test_governance_validator_passes():
    items = get_items()
    report = render_report(items)
    checks = validate_governance(report)
    passed = sum(1 for c in checks if c.passed)
    assert passed == len(checks)


def test_governance_has_kill_switch():
    items = get_items()
    report = render_report(items)
    assert "kill switch" in report.lower()
