"""Integration test: mock replay harness."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_mock_replay.mock_replay_harness import (
    build_request_envelope, run_replay, validate_trace, render_report
)


def test_envelope_created():
    env = build_request_envelope("POST", "/api/v3/order", '{"symbol":"BTCUSDT"}')
    assert env["request_id"].startswith("REQ_")
    assert env["headers"]["X-Mock-Transport"] == "true"


def test_replay_returns_trace():
    trace = run_replay("test_scenario", "POST", "/api/v3/order", '{}', "order_accepted", 200, {"orderId": "MOCK_001"}, "MOCK_ACCEPTED")
    assert trace.scenario_id == "test_scenario"
    assert trace.final_decision == "MOCK_ACCEPTED"
    assert trace.signing_fixture_status == "FIXTURE_ONLY"
    assert trace.vault_stub_status == "STUB_ONLY"


def test_trace_valid():
    trace = run_replay("test", "GET", "/api/v3/account", "", "balance_mock", 200, {"balances": []}, "MOCK_ACCEPTED")
    result = validate_trace(trace)
    assert result["valid"] is True
    assert len(result["errors"]) == 0


def test_trace_rejects_forbidden_decision():
    trace = run_replay("test", "GET", "/api/v3/account", "", "balance_mock", 200, {"balances": []}, "MOCK_ACCEPTED")
    d = trace.to_dict()
    d["final_decision"] = f"REAL_{'SUBMITTED'}"
    from src.runtime_integrations.testnet_mock_replay.mock_replay_harness import ReplayTrace
    bad_trace = ReplayTrace(**d)
    result = validate_trace(bad_trace)
    assert result["valid"] is False


def test_report_flags():
    report = render_report()
    assert "MOCK_ONLY" in report
    assert "submit_allowed=false" in report
    assert "MOCK_REPLAY_HARNESS_READY" in report
