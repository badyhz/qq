"""Integration test: field-test governance pack."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_mock_transport.field_test_governance_pack import get_checklists, render_report


def test_checklists_present():
    items = get_checklists()
    assert len(items) >= 12


def test_checklist_categories():
    items = get_checklists()
    categories = {c.category for c in items}
    assert "scope" in categories
    assert "approval" in categories
    assert "safety" in categories


def test_report_flags():
    items = get_checklists()
    report = render_report(items)
    assert "PACK_ONLY" in report
    assert "field_test_executed=false" in report
    assert "submit_allowed=false" in report
    assert "FIELD_TEST_GOVERNANCE_PACK_READY" in report


def test_checklists_required():
    items = get_checklists()
    required = [c for c in items if c.required]
    assert len(required) >= 10
