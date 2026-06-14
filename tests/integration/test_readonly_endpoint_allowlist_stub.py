"""Integration test: endpoint allowlist stub (per-module)."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_readonly_dry_execution_rehearsal.endpoint_allowlist_stub import (
    create_stub, EndpointAllowlistStub
)


def test_stub_ready():
    stub = create_stub()
    assert "ENDPOINT_ALLOWLIST_STUB_READY" in stub.final_verdict


def test_placeholder_mock_labels_allowed():
    stub = create_stub()
    allowed = [e for e in stub.entries if e.allowed]
    assert len(allowed) >= 3
    for e in allowed:
        assert "mock" in e.url_pattern.lower() or "file" in e.url_pattern.lower() or "fixture" in e.url_pattern.lower()


def test_real_exchange_hostnames_blocked():
    stub = create_stub()
    blocked = [e for e in stub.entries if not e.allowed]
    for e in blocked:
        assert "REAL_EXCHANGE" in e.url_pattern or "TESTNET_EXCHANGE" in e.url_pattern


def test_no_real_http_url_accepted():
    stub = create_stub()
    for e in stub.entries:
        if e.allowed:
            assert not e.url_pattern.startswith("http://"), f"Real HTTP URL accepted: {e.url_pattern}"
            assert not e.url_pattern.startswith("https://"), f"Real HTTPS URL accepted: {e.url_pattern}"


def test_submit_order_endpoint_category_blocked():
    stub = create_stub()
    order_entries = [e for e in stub.entries if e.category == "ORDER"]
    for e in order_entries:
        assert not e.allowed, f"Order endpoint should be blocked: {e.endpoint_id}"


def test_entry_count():
    stub = create_stub()
    assert len(stub.entries) >= 8


def test_allowed_blocked_distribution():
    stub = create_stub()
    allowed = sum(1 for e in stub.entries if e.allowed)
    blocked = sum(1 for e in stub.entries if not e.allowed)
    assert allowed >= 3
    assert blocked >= 4
