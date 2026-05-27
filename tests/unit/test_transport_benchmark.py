"""T780 — Transport benchmark simulator tests."""

import asyncio
import pytest
from core.http_transport import HTTPTransport, TransportResponse
from core.transport_benchmark import BenchmarkTransport, run_benchmark


class InstantTransport(HTTPTransport):
    async def request(self, method, url, headers=None, body=None, timeout_seconds=30.0):
        return TransportResponse(status_code=200, headers={}, body={"ok": True}, duration_ms=0.0, success=True)


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def test_benchmark_records_latencies():
    async def go():
        t = BenchmarkTransport(InstantTransport())
        await t.request("GET", "https://example.com")
        await t.request("GET", "https://example.com")
        r = t.results()
        assert r.total_requests == 2
        assert r.avg_latency_ms >= 0
    _run(go())


def test_benchmark_results():
    async def go():
        t = BenchmarkTransport(InstantTransport())
        for _ in range(10):
            await t.request("GET", "https://example.com")
        r = t.results()
        assert r.total_requests == 10
        assert r.p50_latency_ms >= 0
        assert r.p95_latency_ms >= 0
        assert r.p99_latency_ms >= 0
        assert r.requests_per_second > 0
    _run(go())


def test_benchmark_reset():
    async def go():
        t = BenchmarkTransport(InstantTransport())
        await t.request("GET", "https://example.com")
        assert t.results().total_requests == 1
        t.reset()
        assert t.results().total_requests == 0
    _run(go())


def test_run_benchmark():
    async def go():
        r = await run_benchmark(InstantTransport(), "GET", "https://example.com", concurrency=2, total_requests=5)
        assert r.total_requests == 5
    _run(go())
