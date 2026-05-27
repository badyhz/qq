"""T778 — Transport health check tests."""

import asyncio
import pytest
from core.http_transport import HTTPTransport, TransportResponse
from core.transport_health import TransportHealthCheck, HealthStatus


class HealthyTransport(HTTPTransport):
    async def request(self, method, url, headers=None, body=None, timeout_seconds=30.0):
        return TransportResponse(status_code=200, headers={}, body={"pong": True}, duration_ms=1.0, success=True)


class FailingTransport(HTTPTransport):
    async def request(self, method, url, headers=None, body=None, timeout_seconds=30.0):
        return TransportResponse(status_code=500, headers={}, body={"error": "down"}, duration_ms=0.0, success=False)


class ErroringTransport(HTTPTransport):
    async def request(self, method, url, headers=None, body=None, timeout_seconds=30.0):
        raise ConnectionError("refused")


def _run(coro):
    return asyncio.run(coro)


def test_health_check_healthy():
    async def go():
        hc = TransportHealthCheck(HealthyTransport())
        r = await hc.check()
        assert r.status == HealthStatus.HEALTHY
        assert r.error is None
    _run(go())


def test_health_check_unhealthy():
    async def go():
        hc = TransportHealthCheck(FailingTransport())
        r = await hc.check()
        assert r.status == HealthStatus.UNHEALTHY
        assert r.error is not None
    _run(go())


def test_health_check_exception():
    async def go():
        hc = TransportHealthCheck(ErroringTransport())
        r = await hc.check()
        assert r.status == HealthStatus.UNHEALTHY
        assert "refused" in r.error
    _run(go())


def test_health_check_history():
    async def go():
        hc = TransportHealthCheck(HealthyTransport())
        await hc.check()
        await hc.check()
        assert len(hc.history()) == 2
    _run(go())


def test_health_check_current_status():
    async def go():
        hc = TransportHealthCheck(HealthyTransport())
        assert hc.current_status() == HealthStatus.UNHEALTHY
        await hc.check()
        assert hc.current_status() == HealthStatus.HEALTHY
    _run(go())


def test_health_check_degraded():
    async def go():
        class SlowTransport(HTTPTransport):
            async def request(self, method, url, headers=None, body=None, timeout_seconds=30.0):
                await asyncio.sleep(0.05)
                return TransportResponse(status_code=200, headers={}, body={"ok": True}, duration_ms=50.0, success=True)
        hc = TransportHealthCheck(SlowTransport(), latency_threshold_ms=10.0)
        r = await hc.check()
        assert r.status == HealthStatus.DEGRADED
    _run(go())
