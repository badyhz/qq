"""T779 — Transport sandbox policy tests."""

import asyncio
import pytest
from core.http_transport import HTTPTransport, TransportResponse
from core.transport_sandbox import TransportSandbox, SandboxPolicy, SandboxMode


class PassTransport(HTTPTransport):
    async def request(self, method, url, headers=None, body=None, timeout_seconds=30.0):
        return TransportResponse(status_code=200, headers={}, body={"ok": True}, duration_ms=0.0, success=True)


def _run(coro):
    return asyncio.run(coro)


def test_sandbox_off_allows_all():
    async def go():
        t = TransportSandbox(PassTransport(), SandboxPolicy(mode=SandboxMode.OFF))
        r = await t.request("GET", "https://any-domain.com/path")
        assert r.status_code == 200
    _run(go())


def test_sandbox_restricted_allowlist():
    async def go():
        p = SandboxPolicy(mode=SandboxMode.RESTRICTED, allowed_domains={"api.binance.com"})
        t = TransportSandbox(PassTransport(), p)
        ok = await t.request("GET", "https://api.binance.com/v3/ticker")
        assert ok.status_code == 200
        blocked = await t.request("GET", "https://evil.com/steal")
        assert blocked.status_code == 403
        assert t.blocked_count == 1
    _run(go())


def test_sandbox_blocked_domain():
    async def go():
        p = SandboxPolicy(blocked_domains={"evil.com"})
        t = TransportSandbox(PassTransport(), p)
        ok = await t.request("GET", "https://good.com/data")
        assert ok.status_code == 200
        blocked = await t.request("GET", "https://evil.com/data")
        assert blocked.status_code == 403
    _run(go())


def test_sandbox_method_filter():
    async def go():
        p = SandboxPolicy(allowed_methods={"GET"})
        t = TransportSandbox(PassTransport(), p)
        ok = await t.request("GET", "https://example.com")
        assert ok.status_code == 200
        blocked = await t.request("POST", "https://example.com")
        assert blocked.status_code == 403
    _run(go())


def test_sandbox_simulation_blocks_all():
    async def go():
        t = TransportSandbox(PassTransport(), SandboxPolicy(mode=SandboxMode.SIMULATION))
        r = await t.request("GET", "https://example.com")
        assert r.status_code == 403
        assert "simulation" in r.body["detail"]
    _run(go())


def test_sandbox_url_length():
    async def go():
        p = SandboxPolicy(max_url_length=50)
        t = TransportSandbox(PassTransport(), p)
        ok = await t.request("GET", "https://example.com/short")
        assert ok.status_code == 200
        blocked = await t.request("GET", "https://example.com/" + "a" * 100)
        assert blocked.status_code == 403
    _run(go())
