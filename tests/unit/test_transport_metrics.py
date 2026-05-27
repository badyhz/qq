"""T774 — Transport metrics collector tests."""

import asyncio
import pytest
from core.http_transport import HTTPTransport, TransportResponse
from core.transport_metrics import TransportMetrics, EndpointStats


class FixedTransport(HTTPTransport):
    def __init__(self, status=200):
        self._status = status

    async def request(self, method, url, headers=None, body=None, timeout_seconds=30.0):
        return TransportResponse(
            status_code=self._status, headers={},
            body={"ok": self._status == 200}, duration_ms=1.0,
            success=200 <= self._status < 400,
        )


def _run(coro):
    return asyncio.run(coro)


def test_metrics_records_requests():
    async def go():
        t = TransportMetrics(FixedTransport())
        await t.request("GET", "https://example.com/a")
        await t.request("POST", "https://example.com/b")
        assert len(t.metrics()) == 2
        assert t.metrics()[0].method == "GET"
        assert t.metrics()[1].method == "POST"
    _run(go())


def test_metrics_endpoint_stats():
    async def go():
        t = TransportMetrics(FixedTransport())
        await t.request("GET", "https://example.com/api")
        await t.request("GET", "https://example.com/api")
        stats = t.endpoint_stats()
        assert stats["GET /api"].request_count == 2
        assert stats["GET /api"].success_count == 2
    _run(go())


def test_metrics_error_tracking():
    async def go():
        t = TransportMetrics(FixedTransport(status=500))
        await t.request("GET", "https://example.com/fail")
        stats = t.endpoint_stats()
        assert stats["GET /fail"].error_count == 1
        assert stats["GET /fail"].error_rate == 1.0
    _run(go())


def test_metrics_global_stats():
    async def go():
        t = TransportMetrics(FixedTransport())
        await t.request("GET", "https://example.com/a")
        await t.request("POST", "https://example.com/b")
        g = t.global_stats()
        assert g.request_count == 2
        assert g.success_count == 2
    _run(go())


def test_metrics_reset():
    async def go():
        t = TransportMetrics(FixedTransport())
        await t.request("GET", "https://example.com/test")
        assert len(t.metrics()) == 1
        t.reset()
        assert len(t.metrics()) == 0
        assert len(t.endpoint_stats()) == 0
    _run(go())


def test_endpoint_stats_empty():
    s = EndpointStats()
    assert s.avg_duration_ms == 0.0
    assert s.error_rate == 0.0


def test_endpoint_stats_calculations():
    s = EndpointStats(request_count=10, success_count=8, error_count=2, total_duration_ms=100.0, min_duration_ms=5.0, max_duration_ms=30.0)
    assert s.avg_duration_ms == 10.0
    assert s.error_rate == 0.2
