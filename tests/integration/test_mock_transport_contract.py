"""Integration test: mock transport contract."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_mock_transport.mock_transport_contract import (
    get_available_fixtures, create_request_envelope, dispatch_mock, render_report
)
from src.runtime_integrations.testnet_mock_transport.mock_transport_validator import validate_contract


def test_fixtures_available():
    fixtures = get_available_fixtures()
    assert len(fixtures) >= 11
    assert "order_accepted" in fixtures
    assert "order_rejected" in fixtures
    assert "cancel_success" in fixtures


def test_dispatch_returns_response():
    env = create_request_envelope("GET", "/api/v3/order")
    resp = dispatch_mock("order_accepted", env.request_id)
    assert resp.status_code == 200
    assert resp.fixture_name == "order_accepted"
    assert resp.request_id == env.request_id


def test_dispatch_unknown_fixture():
    env = create_request_envelope("GET", "/api/v3/unknown")
    resp = dispatch_mock("nonexistent", env.request_id)
    assert resp.status_code == 404


def test_report_flags():
    report = render_report()
    assert "MOCK_ONLY" in report
    assert "network_client_implemented=false" in report
    assert "submit_allowed=false" in report


def test_validator_passes():
    report = render_report()
    checks = validate_contract(report)
    passed = sum(1 for c in checks if c.passed)
    assert passed == len(checks)


def test_envelope_has_mock_header():
    env = create_request_envelope("POST", "/api/v3/order", '{"symbol":"BTCUSDT"}')
    headers = dict(env.headers)
    assert headers.get("X-Mock-Transport") == "true"
