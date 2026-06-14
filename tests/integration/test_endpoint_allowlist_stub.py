"""Integration test: endpoint allowlist stub."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_readonly_dry_execution_rehearsal.endpoint_allowlist_stub import create_stub


def test_allowlist_ready():
    stub = create_stub()
    assert "ENDPOINT_ALLOWLIST_STUB_READY" in stub.final_verdict


def test_real_endpoints_blocked():
    stub = create_stub()
    real_eps = [e for e in stub.entries if e.category in ("MARKET_DATA", "ORDER", "ACCOUNT")]
    assert all(not e.allowed for e in real_eps)


def test_mock_endpoints_allowed():
    stub = create_stub()
    mock_eps = [e for e in stub.entries if e.category in ("MOCK_DATA", "MOCK_ORDER", "LOCAL_FIXTURE")]
    assert all(e.allowed for e in mock_eps)
