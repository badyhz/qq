"""Integration test: operator runbook."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_mock_transport.operator_runbook import get_steps, render_report


def test_steps_present():
    steps = get_steps()
    assert len(steps) >= 9


def test_step_categories():
    steps = get_steps()
    categories = {s.category for s in steps}
    assert "preflight" in categories
    assert "verification" in categories
    assert "emergency" in categories


def test_report_flags():
    steps = get_steps()
    report = render_report(steps)
    assert "DRAFT_ONLY" in report
    assert "submit_allowed=false" in report
    assert "OPERATOR_RUNBOOK_DRAFT_READY" in report


def test_steps_required():
    steps = get_steps()
    required = [s for s in steps if s.required]
    assert len(required) >= 7
