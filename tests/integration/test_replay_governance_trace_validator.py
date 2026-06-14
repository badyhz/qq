"""Integration test: replay-to-governance trace validator."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_mock_replay.replay_governance_trace_validator import (
    validate_traces, validate_evidence_bundle, validate_approval_packet
)


def test_validate_traces_valid():
    traces = [
        {"scenario_id": "test", "final_decision": "MOCK_ACCEPTED", "signing_fixture_status": "FIXTURE_ONLY", "vault_stub_status": "STUB_ONLY", "governance_status": {"blockers_present": True}},
    ]
    checks = validate_traces(traces)
    passed = sum(1 for c in checks if c.passed)
    assert passed == len(checks)


def test_validate_traces_forbidden_decision():
    traces = [
        {"scenario_id": "test", "final_decision": f"REAL_{'SUBMITTED'}", "signing_fixture_status": "FIXTURE_ONLY", "vault_stub_status": "STUB_ONLY", "governance_status": {"blockers_present": True}},
    ]
    checks = validate_traces(traces)
    no_forbidden = [c for c in checks if c.check_id == "no_forbidden_decisions"]
    assert len(no_forbidden) == 1
    assert no_forbidden[0].passed is False


def test_validate_evidence_bundle():
    bundle = {"items": [{"content": "THIS_IS_MOCK_EVIDENCE_ONLY"}, {"content": "safety report"}, {"content": "replay summary"}, {"content": "vault report"}, {"content": "signing report"}]}
    checks = validate_evidence_bundle(bundle)
    passed = sum(1 for c in checks if c.passed)
    assert passed == len(checks)


def test_validate_approval_packet():
    packet = {"submit_unlock_blocked": True, "human_approval_required": True, "decision": "APPROVAL_PACKET_GENERATED"}
    checks = validate_approval_packet(packet)
    passed = sum(1 for c in checks if c.passed)
    assert passed == len(checks)
