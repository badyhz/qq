"""T777 — Transport request deduplication tests."""

import asyncio
import pytest
from core.http_transport import HTTPTransport, TransportResponse
from core.transport_dedup import DedupTransport, _request_key


class SlowCountingTransport(HTTPTransport):
    def __init__(self, delay=0.05):
        self.call_count = 0
        self._delay = delay

    async def request(self, method, url, headers=None, body=None, timeout_seconds=30.0):
        self.call_count += 1
        await asyncio.sleep(self._delay)
        return TransportResponse(status_code=200, headers={}, body={"count": self.call_count}, duration_ms=0.0, success=True)


class CountingTransport(HTTPTransport):
    def __init__(self):
        self.call_count = 0

    async def request(self, method, url, headers=None, body=None, timeout_seconds=30.0):
        self.call_count += 1
        return TransportResponse(status_code=200, headers={}, body={"count": self.call_count}, duration_ms=0.0, success=True)


def _run(coro):
    return asyncio.run(coro)


def test_dedup_coalesces_concurrent_requests():
    async def go():
        inner = SlowCountingTransport(delay=0.05)
        t = DedupTransport(inner)
        results = await asyncio.gather(
            t.request("GET", "https://example.com/api"),
            t.request("GET", "https://example.com/api"),
            t.request("GET", "https://example.com/api"),
        )
        assert inner.call_count == 1
        assert t.dedup_count == 2
        assert all(r.body["count"] == 1 for r in results)
    _run(go())


def test_different_requests_not_deduped():
    async def go():
        inner = CountingTransport()
        t = DedupTransport(inner)
        await t.request("GET", "https://example.com/a")
        await t.request("GET", "https://example.com/b")
        assert inner.call_count == 2
        assert t.dedup_count == 0
    _run(go())


def test_different_methods_not_deduped():
    async def go():
        inner = SlowCountingTransport()
        t = DedupTransport(inner)
        await asyncio.gather(
            t.request("GET", "https://example.com/api"),
            t.request("POST", "https://example.com/api"),
        )
        assert inner.call_count == 2
    _run(go())


def test_dedup_after_first_completes():
    async def go():
        inner = CountingTransport()
        t = DedupTransport(inner)
        await t.request("GET", "https://example.com/api")
        await t.request("GET", "https://example.com/api")
        assert inner.call_count == 2
        assert t.dedup_count == 0
    _run(go())


def test_request_key_deterministic():
    k1 = _request_key("GET", "https://example.com", None)
    k2 = _request_key("GET", "https://example.com", None)
    assert k1 == k2


def test_request_key_differs_by_body():
    k1 = _request_key("POST", "https://example.com", {"a": 1})
    k2 = _request_key("POST", "https://example.com", {"a": 2})
    assert k1 != k2
