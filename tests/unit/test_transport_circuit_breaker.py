"""T775 — Transport circuit breaker tests."""

import asyncio
import time
import pytest
from core.http_transport import HTTPTransport, TransportResponse
from core.transport_circuit_breaker import TransportCircuitBreaker, CircuitBreakerConfig, CircuitState


class FailTransport(HTTPTransport):
    def __init__(self, fail_count=0, fail_status=500):
        self._fail_count = fail_count
        self._fail_status = fail_status
        self._calls = 0

    async def request(self, method, url, headers=None, body=None, timeout_seconds=30.0):
        self._calls += 1
        if self._calls <= self._fail_count:
            return TransportResponse(status_code=self._fail_status, headers={}, body={"error": "fail"}, duration_ms=0.0, success=False)
        return TransportResponse(status_code=200, headers={}, body={"ok": True}, duration_ms=0.0, success=True)


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def test_circuit_starts_closed():
    cb = TransportCircuitBreaker(FailTransport())
    assert cb.circuit_state == CircuitState.CLOSED


def test_circuit_opens_after_threshold():
    async def go():
        cfg = CircuitBreakerConfig(failure_threshold=3)
        inner = FailTransport(fail_count=10)
        cb = TransportCircuitBreaker(inner, cfg)
        for _ in range(3):
            await cb.request("GET", "https://example.com")
        assert cb.circuit_state == CircuitState.OPEN
    _run(go())


def test_circuit_blocks_when_open():
    async def go():
        cfg = CircuitBreakerConfig(failure_threshold=2)
        inner = FailTransport(fail_count=10)
        cb = TransportCircuitBreaker(inner, cfg)
        for _ in range(2):
            await cb.request("GET", "https://example.com")
        assert cb.circuit_state == CircuitState.OPEN
        r = await cb.request("GET", "https://example.com")
        assert r.status_code == 503
        assert "circuit_breaker_open" in r.body["error"]
        assert cb.blocked_count == 1
    _run(go())


def test_circuit_half_open_after_timeout():
    async def go():
        cfg = CircuitBreakerConfig(failure_threshold=2, recovery_timeout_seconds=0.01, half_open_max_requests=1, success_threshold=1)
        inner = FailTransport(fail_count=2)
        cb = TransportCircuitBreaker(inner, cfg)
        for _ in range(2):
            await cb.request("GET", "https://example.com")
        assert cb.circuit_state == CircuitState.OPEN
        await asyncio.sleep(0.02)
        inner._fail_count = 0
        r = await cb.request("GET", "https://example.com")
        assert r.status_code == 200
    _run(go())


def test_circuit_closes_from_half_open():
    async def go():
        cfg = CircuitBreakerConfig(failure_threshold=2, recovery_timeout_seconds=0.01, half_open_max_requests=2, success_threshold=2)
        inner = FailTransport(fail_count=2)
        cb = TransportCircuitBreaker(inner, cfg)
        for _ in range(2):
            await cb.request("GET", "https://example.com")
        await asyncio.sleep(0.02)
        inner._fail_count = 0
        await cb.request("GET", "https://example.com")
        await cb.request("GET", "https://example.com")
        assert cb.circuit_state == CircuitState.CLOSED
    _run(go())


def test_circuit_reset():
    async def go():
        cfg = CircuitBreakerConfig(failure_threshold=2)
        cb = TransportCircuitBreaker(FailTransport(fail_count=10), cfg)
        for _ in range(2):
            await cb.request("GET", "https://example.com")
        assert cb.circuit_state == CircuitState.OPEN
        cb.reset()
        assert cb.circuit_state == CircuitState.CLOSED
        assert cb.failure_count == 0
        assert cb.blocked_count == 0
    _run(go())
