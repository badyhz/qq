"""T783 — Transport observability hooks tests."""

import asyncio
import pytest
from core.http_transport import HTTPTransport, TransportResponse
from core.transport_observability import TransportObservability, TransportEvent, TransportObservation


class StubTransport(HTTPTransport):
    def __init__(self, status=200):
        self._status = status

    async def request(self, method, url, headers=None, body=None, timeout_seconds=30.0):
        return TransportResponse(status_code=self._status, headers={}, body={"ok": self._status == 200}, duration_ms=1.0, success=200 <= self._status < 400)


class ErrorTransport(HTTPTransport):
    async def request(self, method, url, headers=None, body=None, timeout_seconds=30.0):
        raise ConnectionError("refused")


def _run(coro):
    return asyncio.run(coro)


def test_emits_start_and_complete():
    async def go():
        obs = TransportObservability(StubTransport())
        await obs.request("GET", "https://example.com")
        events = obs.observations()
        assert events[0].event == TransportEvent.REQUEST_STARTED
        assert events[1].event == TransportEvent.REQUEST_COMPLETED
    _run(go())


def test_emits_failure_on_error_status():
    async def go():
        obs = TransportObservability(StubTransport(status=500))
        await obs.request("GET", "https://example.com")
        events = obs.observations()
        assert events[-1].event == TransportEvent.REQUEST_FAILED
        assert events[-1].status_code == 500
    _run(go())


def test_emits_failure_on_exception():
    async def go():
        obs = TransportObservability(ErrorTransport())
        with pytest.raises(ConnectionError):
            await obs.request("GET", "https://example.com")
        events = obs.observations()
        assert events[-1].event == TransportEvent.REQUEST_FAILED
        assert "refused" in events[-1].error
    _run(go())


def test_custom_handler_called():
    async def go():
        captured = []
        def handler(o):
            captured.append(o)
        obs = TransportObservability(StubTransport())
        obs.add_handler(handler)
        await obs.request("POST", "https://example.com")
        assert len(captured) == 2
        assert captured[0].event == TransportEvent.REQUEST_STARTED
    _run(go())


def test_adapter_id_recorded():
    async def go():
        obs = TransportObservability(StubTransport(), adapter_id="claude")
        await obs.request("GET", "https://example.com")
        assert all(e.adapter_id == "claude" for e in obs.observations())
    _run(go())


def test_handler_error_does_not_propagate():
    async def go():
        def bad_handler(o):
            raise RuntimeError("handler crash")
        obs = TransportObservability(StubTransport())
        obs.add_handler(bad_handler)
        r = await obs.request("GET", "https://example.com")
        assert r.status_code == 200
    _run(go())
