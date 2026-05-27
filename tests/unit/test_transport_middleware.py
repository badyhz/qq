"""T773 — Transport middleware chain tests."""

import asyncio
import pytest
from core.http_transport import HTTPTransport, TransportResponse
from core.transport_middleware import (
    MiddlewareTransport, HeaderInjectionMiddleware,
    RequestLoggingMiddleware, ResponseTransformMiddleware,
    TransportMiddleware,
)


class StubTransport(HTTPTransport):
    def __init__(self):
        self.last_headers = None

    async def request(self, method, url, headers=None, body=None, timeout_seconds=30.0):
        self.last_headers = headers
        return TransportResponse(
            status_code=200, headers={}, body={"ok": True},
            duration_ms=0.0, success=True,
        )


def _run(coro):
    return asyncio.run(coro)


def test_header_injection():
    async def go():
        stub = StubTransport()
        mw = HeaderInjectionMiddleware({"X-Custom": "value123"})
        t = MiddlewareTransport(stub, [mw])
        await t.request("GET", "https://example.com")
        assert stub.last_headers["X-Custom"] == "value123"
    _run(go())


def test_header_injection_merges():
    async def go():
        stub = StubTransport()
        mw = HeaderInjectionMiddleware({"X-Injected": "yes"})
        t = MiddlewareTransport(stub, [mw])
        await t.request("GET", "https://example.com", headers={"X-Original": "no"})
        assert stub.last_headers["X-Injected"] == "yes"
        assert stub.last_headers["X-Original"] == "no"
    _run(go())


def test_request_logging():
    async def go():
        stub = StubTransport()
        logger_mw = RequestLoggingMiddleware()
        t = MiddlewareTransport(stub, [logger_mw])
        await t.request("POST", "https://api.test.com/data")
        assert len(logger_mw.log) == 2
        assert logger_mw.log[0]["phase"] == "request"
        assert logger_mw.log[1]["phase"] == "response"
        assert logger_mw.log[1]["status"] == 200
    _run(go())


def test_response_transform():
    async def go():
        stub = StubTransport()
        transform = ResponseTransformMiddleware(lambda body: {"transformed": True, **(body if isinstance(body, dict) else {})})
        t = MiddlewareTransport(stub, [transform])
        r = await t.request("GET", "https://example.com")
        assert r.body["transformed"] is True
    _run(go())


def test_middleware_chain_order():
    async def go():
        stub = StubTransport()
        log = []

        class OrderTracker(TransportMiddleware):
            def __init__(self, name):
                self.name = name
            async def request_hook(self, method, url, headers, body, timeout):
                log.append(f"req:{self.name}")
                return method, url, headers, body, timeout
            async def response_hook(self, response, method, url):
                log.append(f"res:{self.name}")
                return response

        t = MiddlewareTransport(stub, [OrderTracker("first"), OrderTracker("second")])
        await t.request("GET", "https://example.com")
        assert log == ["req:first", "req:second", "res:first", "res:second"]
    _run(go())


def test_add_middleware_dynamically():
    async def go():
        stub = StubTransport()
        t = MiddlewareTransport(stub)
        t.add_middleware(HeaderInjectionMiddleware({"X-Dynamic": "added"}))
        await t.request("GET", "https://example.com")
        assert stub.last_headers["X-Dynamic"] == "added"
    _run(go())
