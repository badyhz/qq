"""Tests for core.http_transport — MockTransport, DryRunTransport, dataclasses."""

from __future__ import annotations

import pytest

from core.http_transport import (
    DryRunTransport,
    MockTransport,
    TransportError,
    TransportResponse,
)


# ── TransportResponse ───────────────────────────────────────────────


class TestTransportResponse:
    def test_fields(self) -> None:
        r = TransportResponse(
            status_code=200, headers={"x": "1"}, body={"ok": True}, duration_ms=1.23, success=True
        )
        assert r.status_code == 200
        assert r.headers == {"x": "1"}
        assert r.body == {"ok": True}
        assert r.duration_ms == 1.23
        assert r.success is True

    def test_string_body(self) -> None:
        r = TransportResponse(status_code=200, headers={}, body="raw", duration_ms=0, success=True)
        assert r.body == "raw"


# ── TransportError ──────────────────────────────────────────────────


class TestTransportError:
    def test_fields(self) -> None:
        e = TransportError(message="timeout", status_code=None, retryable=True)
        assert e.message == "timeout"
        assert e.status_code is None
        assert e.retryable is True

    def test_with_status(self) -> None:
        e = TransportError(message="bad", status_code=503, retryable=False)
        assert e.status_code == 503
        assert e.retryable is False


# ── MockTransport ───────────────────────────────────────────────────


class TestMockTransport:
    @pytest.fixture
    def t(self) -> MockTransport:
        return MockTransport()

    @pytest.mark.anyio
    async def test_default_200(self, t: MockTransport) -> None:
        r = await t.get("https://example.com")
        assert r.status_code == 200
        assert r.body == {"status": "ok"}
        assert r.success is True

    @pytest.mark.anyio
    async def test_set_response(self, t: MockTransport) -> None:
        t.set_response(status_code=404, body={"error": "not found"})
        r = await t.get("https://example.com")
        assert r.status_code == 404
        assert r.body == {"error": "not found"}
        assert r.success is False

    @pytest.mark.anyio
    async def test_records_requests(self, t: MockTransport) -> None:
        await t.get("https://a.com")
        await t.post("https://b.com", body={"x": 1})
        recs = t.requests()
        assert len(recs) == 2
        assert recs[0].method == "GET"
        assert recs[1].method == "POST"
        assert recs[1].body == {"x": 1}

    @pytest.mark.anyio
    async def test_get_stores_method(self, t: MockTransport) -> None:
        await t.get("https://x.com")
        assert t.requests()[0].method == "GET"

    @pytest.mark.anyio
    async def test_post_stores_method_and_body(self, t: MockTransport) -> None:
        await t.post("https://x.com", body={"k": "v"})
        rec = t.requests()[0]
        assert rec.method == "POST"
        assert rec.body == {"k": "v"}

    @pytest.mark.anyio
    async def test_headers_passthrough(self, t: MockTransport) -> None:
        await t.get("https://x.com", headers={"auth": "tok"})
        assert t.requests()[0].headers == {"auth": "tok"}

    @pytest.mark.anyio
    async def test_timeout_passthrough(self, t: MockTransport) -> None:
        await t.get("https://x.com", timeout_seconds=5.0)
        assert t.requests()[0].timeout_seconds == 5.0

    @pytest.mark.anyio
    async def test_multiple_tracked(self, t: MockTransport) -> None:
        for _ in range(5):
            await t.get("https://x.com")
        assert len(t.requests()) == 5

    @pytest.mark.anyio
    async def test_set_response_with_headers(self, t: MockTransport) -> None:
        t.set_response(status_code=200, body="ok", headers={"h": "1"})
        r = await t.get("https://x.com")
        assert r.headers == {"h": "1"}


# ── DryRunTransport ─────────────────────────────────────────────────


class TestDryRunTransport:
    @pytest.fixture
    def t(self) -> DryRunTransport:
        return DryRunTransport()

    @pytest.mark.anyio
    async def test_logs_without_sending(self, t: DryRunTransport) -> None:
        r = await t.get("https://example.com")
        assert r.status_code == 200
        assert r.body == {"status": "dry_run_ok"}
        assert r.success is True

    @pytest.mark.anyio
    async def test_dry_run_log_records(self, t: DryRunTransport) -> None:
        await t.get("https://a.com")
        await t.post("https://b.com", body={"x": 1})
        log = t.dry_run_log()
        assert len(log) == 2
        assert log[0].method == "GET"
        assert log[1].method == "POST"
        assert log[1].body == {"x": 1}

    @pytest.mark.anyio
    async def test_never_uses_network(self, t: DryRunTransport) -> None:
        # All calls return immediately with simulated body
        for _ in range(10):
            r = await t.get("https://anywhere.invalid")
            assert r.success is True
        assert len(t.dry_run_log()) == 10

    @pytest.mark.anyio
    async def test_headers_recorded(self, t: DryRunTransport) -> None:
        await t.post("https://x.com", headers={"k": "v"})
        assert t.dry_run_log()[0].headers == {"k": "v"}

    @pytest.mark.anyio
    async def test_timeout_recorded(self, t: DryRunTransport) -> None:
        await t.get("https://x.com", timeout_seconds=3.0)
        assert t.dry_run_log()[0].timeout_seconds == 3.0
