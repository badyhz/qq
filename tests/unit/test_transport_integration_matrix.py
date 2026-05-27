"""T784 — Transport integration matrix tests.

Tests composing multiple transport layers together.
"""

import asyncio
import pytest
from core.http_transport import HTTPTransport, TransportResponse
from core.transport_retry import RetryTransport, RetryConfig, BackoffStrategy
from core.transport_circuit_breaker import TransportCircuitBreaker, CircuitBreakerConfig
from core.transport_metrics import TransportMetrics
from core.transport_middleware import MiddlewareTransport, HeaderInjectionMiddleware, RequestLoggingMiddleware
from core.transport_sandbox import TransportSandbox, SandboxPolicy, SandboxMode
from core.transport_observability import TransportObservability, TransportEvent
from core.transport_dedup import DedupTransport


class FlakyTransport(HTTPTransport):
    def __init__(self, fail_count=0, fail_status=500, delay=0.0):
        self._fail_count = fail_count
        self._fail_status = fail_status
        self._delay = delay
        self._calls = 0

    async def request(self, method, url, headers=None, body=None, timeout_seconds=30.0):
        self._calls += 1
        if self._delay > 0:
            await asyncio.sleep(self._delay)
        if self._calls <= self._fail_count:
            return TransportResponse(status_code=self._fail_status, headers={}, body={}, duration_ms=0.0, success=False)
        return TransportResponse(status_code=200, headers={}, body={"ok": True}, duration_ms=0.0, success=True)


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def test_retry_with_metrics():
    async def go():
        inner = FlakyTransport(fail_count=2, fail_status=503)
        retry = RetryTransport(inner, RetryConfig(max_retries=3, base_delay_seconds=0.01, backoff=BackoffStrategy.FIXED))
        metrics = TransportMetrics(retry)
        r = await metrics.request("GET", "https://example.com")
        assert r.status_code == 200
        assert len(metrics.metrics()) == 1
        assert inner._calls == 3
    _run(go())


def test_sandbox_with_retry():
    async def go():
        inner = FlakyTransport(fail_count=5)
        retry = RetryTransport(inner, RetryConfig(max_retries=3, base_delay_seconds=0.01))
        sandbox = TransportSandbox(retry, SandboxPolicy(mode=SandboxMode.SIMULATION))
        r = await sandbox.request("GET", "https://example.com")
        assert r.status_code == 403
        assert inner._calls == 0
    _run(go())


def test_circuit_breaker_with_retry():
    async def go():
        inner = FlakyTransport(fail_count=100, fail_status=500)
        retry = RetryTransport(inner, RetryConfig(max_retries=2, base_delay_seconds=0.01))
        cb = TransportCircuitBreaker(retry, CircuitBreakerConfig(failure_threshold=3))
        for _ in range(3):
            await cb.request("GET", "https://example.com")
        assert cb.circuit_state.value == "open"
        r = await cb.request("GET", "https://example.com")
        assert r.status_code == 503
    _run(go())


def test_middleware_with_metrics():
    async def go():
        inner = FlakyTransport(fail_count=0)
        mw = MiddlewareTransport(inner, [
            HeaderInjectionMiddleware({"X-Trace": "test123"}),
            RequestLoggingMiddleware(),
        ])
        metrics = TransportMetrics(mw)
        r = await metrics.request("GET", "https://example.com")
        assert r.status_code == 200
        assert len(metrics.metrics()) == 1
    _run(go())


def test_observability_with_retry():
    async def go():
        inner = FlakyTransport(fail_count=2, fail_status=503)
        retry = RetryTransport(inner, RetryConfig(max_retries=3, base_delay_seconds=0.01))
        obs = TransportObservability(retry)
        await obs.request("GET", "https://example.com")
        events = obs.observations()
        assert any(e.event == TransportEvent.REQUEST_STARTED for e in events)
        assert any(e.event == TransportEvent.REQUEST_COMPLETED for e in events)
    _run(go())


def test_full_stack_composition():
    async def go():
        inner = FlakyTransport(fail_count=1, fail_status=503)
        metrics = TransportMetrics(inner)
        mw = MiddlewareTransport(metrics, [HeaderInjectionMiddleware({"X-Stack": "full"})])
        retry = RetryTransport(mw, RetryConfig(max_retries=3, base_delay_seconds=0.01))
        cb = TransportCircuitBreaker(retry, CircuitBreakerConfig(failure_threshold=10))
        sandbox = TransportSandbox(cb, SandboxPolicy(mode=SandboxMode.OFF))
        r = await sandbox.request("GET", "https://example.com/api")
        assert r.status_code == 200
        assert len(metrics.metrics()) >= 1
    _run(go())


def test_dedup_with_retry():
    async def go():
        inner = FlakyTransport(fail_count=0, delay=0.05)
        retry = RetryTransport(inner, RetryConfig(max_retries=3, base_delay_seconds=0.01))
        dedup = DedupTransport(retry)
        results = await asyncio.gather(
            dedup.request("GET", "https://example.com/same"),
            dedup.request("GET", "https://example.com/same"),
        )
        assert inner._calls == 1
        assert dedup.dedup_count == 1
    _run(go())
