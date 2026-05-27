"""T772 — Timeout matrix transport tests."""

import asyncio
import pytest

from core.http_transport import TransportResponse, HTTPTransport
from core.transport_timeout import TimeoutMatrix, TimeoutRule, TimeoutTransport


class RecordingTransport(HTTPTransport):
    def __init__(self):
        self.timeouts = []

    async def request(self, method, url, headers=None, body=None, timeout_seconds=30.0):
        self.timeouts.append(timeout_seconds)
        return TransportResponse(
            status_code=200, headers={}, body={"ok": True},
            duration_ms=0.0, success=True,
        )


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def test_matrix_default_timeout():
    m = TimeoutMatrix(default_timeout=15.0)
    assert m.resolve() == 15.0
    assert m.resolve(method="GET") == 15.0


def test_matrix_method_rule():
    m = TimeoutMatrix()
    m.add_rule(TimeoutRule(method="POST", timeout_seconds=60.0))
    assert m.resolve(method="GET") == 30.0
    assert m.resolve(method="POST") == 60.0


def test_matrix_domain_rule():
    m = TimeoutMatrix()
    m.add_rule(TimeoutRule(domain="api.binance.com", timeout_seconds=10.0))
    assert m.resolve(domain="api.binance.com") == 10.0
    assert m.resolve(domain="other.com") == 30.0


def test_matrix_priority_resolution():
    m = TimeoutMatrix()
    m.add_rule(TimeoutRule(method="POST", timeout_seconds=45.0, priority=1))
    m.add_rule(TimeoutRule(method="POST", domain="api.binance.com", timeout_seconds=5.0, priority=10))
    assert m.resolve(method="POST", domain="api.binance.com") == 5.0
    assert m.resolve(method="POST", domain="other.com") == 45.0


def test_matrix_adapter_rule():
    m = TimeoutMatrix()
    m.add_rule(TimeoutRule(adapter_id="claude", timeout_seconds=120.0))
    assert m.resolve(adapter_id="claude") == 120.0
    assert m.resolve(adapter_id="mimo") == 30.0


def test_timeout_transport_applies_matrix():
    async def go():
        m = TimeoutMatrix()
        m.add_rule(TimeoutRule(method="GET", domain="example.com", timeout_seconds=5.0))
        rec = RecordingTransport()
        t = TimeoutTransport(rec, m)
        await t.request("GET", "https://example.com/test")
        assert rec.timeouts == [5.0]
    _run(go())


def test_timeout_transport_different_domains():
    async def go():
        m = TimeoutMatrix()
        m.add_rule(TimeoutRule(domain="fast.com", timeout_seconds=2.0))
        m.add_rule(TimeoutRule(domain="slow.com", timeout_seconds=60.0))
        rec = RecordingTransport()
        t = TimeoutTransport(rec, m)
        await t.request("GET", "https://fast.com/a")
        await t.request("GET", "https://slow.com/b")
        assert rec.timeouts == [2.0, 60.0]
    _run(go())


def test_timeout_transport_fallback_to_input():
    async def go():
        rec = RecordingTransport()
        t = TimeoutTransport(rec, TimeoutMatrix())
        await t.request("GET", "https://example.com", timeout_seconds=99.0)
        assert rec.timeouts == [30.0]
    _run(go())


def test_extract_domain():
    from core.transport_timeout import _extract_domain
    assert _extract_domain("https://api.binance.com/v3/ticker") == "api.binance.com"
    assert _extract_domain("http://localhost:8080/health") == "localhost"
    assert _extract_domain("https://example.com") == "example.com"
