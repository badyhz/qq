"""Integration test: replay scenario matrix."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_mock_replay.replay_scenario_matrix import get_scenarios, render_report


def test_scenarios_present():
    scenarios = get_scenarios()
    assert len(scenarios) >= 13


def test_scenario_categories():
    scenarios = get_scenarios()
    categories = {s.category for s in scenarios}
    assert "submit" in categories
    assert "cancel" in categories
    assert "error" in categories
    assert "governance" in categories


def test_scenario_decisions():
    scenarios = get_scenarios()
    valid = ("MOCK_ACCEPTED", "MOCK_REJECTED", "BLOCKED", "NOT_READY", "DENY")
    for s in scenarios:
        assert s.expected_decision in valid


def test_report_flags():
    scenarios = get_scenarios()
    report = render_report(scenarios)
    assert "MOCK_ONLY" in report
    assert "MOCK_REPLAY_SCENARIO_MATRIX_READY" in report
    assert "TESTNET_SUBMIT_NOT_ALLOWED" in report
