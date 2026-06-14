"""Integration test: network-on blocker drill."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_readonly_final_approval_simulator.network_on_blocker_drill import (
    create_drill, count_blocked, count_by_severity, count_by_risk_category, has_unblocked_case
)


def test_drill_pass():
    drill = create_drill()
    assert "NETWORK_ON_BLOCKER_DRILL_PASS" in drill.final_verdict


def test_all_scenarios_blocked():
    drill = create_drill()
    assert all(s.blocked for s in drill.scenarios)


def test_drill_scenario_count():
    drill = create_drill()
    assert len(drill.scenarios) >= 15


def test_no_unblocked_cases():
    drill = create_drill()
    assert has_unblocked_case(drill.scenarios) is False
    assert count_blocked(drill.scenarios) == len(drill.scenarios)


def test_critical_severity_count():
    drill = create_drill()
    by_sev = count_by_severity(drill.scenarios)
    assert by_sev.get("CRITICAL", 0) >= 3


def test_partial_network_scenario_exists():
    drill = create_drill()
    types = [s.request_type for s in drill.scenarios]
    assert "REQUEST_PARTIAL_NETWORK_ENABLEMENT" in types


def test_timeout_retry_scenario_exists():
    drill = create_drill()
    types = [s.request_type for s in drill.scenarios]
    assert "REQUEST_NETWORK_TIMEOUT_RETRY" in types


def test_auth_failure_retry_scenario_exists():
    drill = create_drill()
    types = [s.request_type for s in drill.scenarios]
    assert "REQUEST_AUTH_FAILURE_RETRY" in types


def test_rate_limit_retry_scenario_exists():
    drill = create_drill()
    types = [s.request_type for s in drill.scenarios]
    assert "REQUEST_RATE_LIMIT_RETRY" in types


def test_credential_scope_escalation_exists():
    drill = create_drill()
    types = [s.request_type for s in drill.scenarios]
    assert "REQUEST_CREDENTIAL_SCOPE_ESCALATION" in types


def test_readonly_to_submit_escalation_exists():
    drill = create_drill()
    types = [s.request_type for s in drill.scenarios]
    assert "REQUEST_READONLY_TO_SUBMIT_ESCALATION" in types


def test_all_decisions_include_blocked():
    drill = create_drill()
    for s in drill.scenarios:
        assert s.actual_result == "BLOCKED"
        assert "REAL_NETWORK_STILL_BLOCKED" in s.final_decision
        assert "TESTNET_SUBMIT_NOT_ALLOWED" in s.final_decision


def test_risk_category_distribution():
    drill = create_drill()
    by_cat = count_by_risk_category(drill.scenarios)
    assert len(by_cat) >= 5
