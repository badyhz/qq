"""Transport middleware chain — composable request/response interceptors.

Pure simulation — no real network calls.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, List

from core.http_transport import HTTPTransport, TransportResponse

logger = logging.getLogger(__name__)


class TransportMiddleware(ABC):
    """Base middleware. Override request_hook and/or response_hook."""

    async def request_hook(
        self,
        method: str,
        url: str,
        headers: dict | None,
        body: dict | None,
        timeout_seconds: float,
    ) -> tuple[str, str, dict | None, dict | None, float]:
        """Transform request. Return (method, url, headers, body, timeout)."""
        return method, url, headers, body, timeout_seconds

    async def response_hook(
        self,
        response: TransportResponse,
        method: str,
        url: str,
    ) -> TransportResponse:
        """Transform response. Return (possibly modified) response."""
        return response


class HeaderInjectionMiddleware(TransportMiddleware):
    """Injects headers into every request."""

    def __init__(self, headers: dict[str, str]) -> None:
        self._headers = headers

    async def request_hook(self, method, url, headers, body, timeout_seconds):
        merged = dict(self._headers)
        merged.update(headers or {})
        return method, url, merged, body, timeout_seconds


class RequestLoggingMiddleware(TransportMiddleware):
    """Logs all requests and responses."""

    def __init__(self) -> None:
        self.log: list[dict[str, Any]] = []

    async def request_hook(self, method, url, headers, body, timeout_seconds):
        self.log.append({"phase": "request", "method": method, "url": url})
        return method, url, headers, body, timeout_seconds

    async def response_hook(self, response, method, url):
        self.log.append({
            "phase": "response", "method": method, "url": url,
            "status": response.status_code,
        })
        return response


class ResponseTransformMiddleware(TransportMiddleware):
    """Transforms response body via a callable."""

    def __init__(self, transform: Callable[[dict | str], dict | str]) -> None:
        self._transform = transform

    async def response_hook(self, response, method, url):
        return TransportResponse(
            status_code=response.status_code,
            headers=response.headers,
            body=self._transform(response.body),
            duration_ms=response.duration_ms,
            success=response.success,
        )


class MiddlewareTransport(HTTPTransport):
    """Wraps HTTPTransport with a chain of middleware."""

    def __init__(
        self,
        inner: HTTPTransport,
        middleware: list[TransportMiddleware] | None = None,
    ) -> None:
        self._inner = inner
        self._middleware = list(middleware or [])

    def add_middleware(self, mw: TransportMiddleware) -> None:
        self._middleware.append(mw)

    async def request(
        self,
        method: str,
        url: str,
        headers: dict | None = None,
        body: dict | None = None,
        timeout_seconds: float = 30.0,
    ) -> TransportResponse:
        # Request hooks (forward order)
        for mw in self._middleware:
            method, url, headers, body, timeout_seconds = await mw.request_hook(
                method, url, headers, body, timeout_seconds,
            )

        response = await self._inner.request(
            method, url, headers=headers, body=body,
            timeout_seconds=timeout_seconds,
        )

        # Response hooks (forward order)
        for mw in self._middleware:
            response = await mw.response_hook(response, method, url)

        return response
