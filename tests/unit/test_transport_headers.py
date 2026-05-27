"""T776 — Header normalization layer tests."""

import asyncio
import pytest
from core.http_transport import HTTPTransport, TransportResponse
from core.transport_headers import HeaderNormalizer, HeaderPolicy, HeaderNormalizationTransport


class CapturingTransport(HTTPTransport):
    def __init__(self):
        self.captured_headers = None

    async def request(self, method, url, headers=None, body=None, timeout_seconds=30.0):
        self.captured_headers = headers
        return TransportResponse(status_code=200, headers={}, body={"ok": True}, duration_ms=0.0, success=True)


def _run(coro):
    return asyncio.run(coro)


def test_canonicalize_casing():
    n = HeaderNormalizer()
    r = n.normalize_request_headers({"content-type": "application/json"})
    assert "Content-Type" in r
    assert r["Content-Type"] == "application/json"


def test_preserve_unknown_headers():
    n = HeaderNormalizer()
    r = n.normalize_request_headers({"X-Custom-Header": "value"})
    assert r["X-Custom-Header"] == "value"


def test_required_headers_injected():
    n = HeaderNormalizer(HeaderPolicy(required_headers={"Accept": "application/json"}))
    r = n.normalize_request_headers({})
    assert r["Accept"] == "application/json"


def test_required_headers_overridden():
    n = HeaderNormalizer(HeaderPolicy(required_headers={"Accept": "application/json"}))
    r = n.normalize_request_headers({"Accept": "text/html"})
    assert r["Accept"] == "text/html"


def test_forbidden_headers_stripped():
    n = HeaderNormalizer(HeaderPolicy(forbidden_headers={"x-debug"}))
    r = n.normalize_request_headers({"X-Debug": "true", "Accept": "json"})
    assert "X-Debug" not in r
    assert r["Accept"] == "json"


def test_max_value_length_truncated():
    n = HeaderNormalizer(HeaderPolicy(max_header_value_length=10))
    r = n.normalize_request_headers({"X-Long": "a" * 100})
    assert len(r["X-Long"]) == 10


def test_redact_sensitive_headers():
    n = HeaderNormalizer()
    h = {"Authorization": "Bearer secret123", "Content-Type": "json"}
    redacted = n.redact_for_logging(h)
    assert redacted["Authorization"] == "***REDACTED***"
    assert redacted["Content-Type"] == "json"


def test_redact_disabled():
    n = HeaderNormalizer(HeaderPolicy(redact_sensitive=False))
    redacted = n.redact_for_logging({"Authorization": "Bearer secret123"})
    assert redacted["Authorization"] == "Bearer secret123"


def test_normalize_response_headers():
    n = HeaderNormalizer()
    r = n.normalize_response_headers({"content-type": "application/json"})
    assert "Content-Type" in r


def test_no_canonicalization():
    n = HeaderNormalizer(HeaderPolicy(canonicalize_casing=False))
    r = n.normalize_request_headers({"content-type": "application/json"})
    assert "content-type" in r
    assert "Content-Type" not in r


def test_normalization_transport():
    async def go():
        cap = CapturingTransport()
        t = HeaderNormalizationTransport(cap, HeaderNormalizer())
        await t.request("GET", "https://example.com", headers={"content-type": "json"})
        assert "Content-Type" in cap.captured_headers
    _run(go())
