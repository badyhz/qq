"""Integration test: request signing fixture."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_mock_transport.request_signing_fixture import (
    build_fixture_envelope, validate_envelope, render_report
)


def test_envelope_created():
    env = build_fixture_envelope("POST", "/api/v3/order", '{"symbol":"BTCUSDT"}')
    assert env.envelope_id.startswith("ENV_")
    assert env.method == "POST"
    assert env.path == "/api/v3/order"
    assert env.real_signing is False


def test_envelope_not_real_signing():
    env = build_fixture_envelope("GET", "/api/v3/account")
    assert env.real_signing is False
    assert "****" in env.key_id


def test_envelope_valid():
    env = build_fixture_envelope("POST", "/api/v3/order")
    assert validate_envelope(env.to_dict()) is True


def test_report_flags():
    report = render_report()
    assert "FIXTURE_ONLY" in report
    assert "real_secret_used=false" in report
    assert "request_sendable=false" in report
    assert "submit_allowed=false" in report
    assert "REAL_SIGNING_NOT_ALLOWED" in report


def test_reject_real_signing():
    env = build_fixture_envelope("POST", "/api/v3/order")
    d = env.to_dict()
    d["real_signing"] = True
    assert validate_envelope(d) is False
