"""HTTP transport abstraction — no real outbound requests.

Defines transport interface for HTTP communication.
All implementations are pure abstraction; no network calls.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ── response / error dataclasses ────────────────────────────────────


@dataclass
class TransportResponse:
    """Response from an HTTP transport call."""

    status_code: int
    headers: dict
    body: dict | str
    duration_ms: float
    success: bool


@dataclass
class TransportError:
    """Error from an HTTP transport call."""

    message: str
    status_code: int | None
    retryable: bool


@dataclass
class _RecordedRequest:
    """Internal record of a request made through a transport."""

    method: str
    url: str
    headers: dict
    body: dict | None
    timeout_seconds: float


# ── ABC ─────────────────────────────────────────────────────────────


class HTTPTransport(ABC):
    """Abstract base for HTTP transport implementations.

    No real outbound requests. Pure interface contract.
    """

    @abstractmethod
    async def request(
        self,
        method: str,
        url: str,
        headers: dict | None = None,
        body: dict | None = None,
        timeout_seconds: float = 30.0,
    ) -> TransportResponse:
        ...

    async def get(
        self,
        url: str,
        headers: dict | None = None,
        timeout_seconds: float = 30.0,
    ) -> TransportResponse:
        return await self.request("GET", url, headers=headers, timeout_seconds=timeout_seconds)

    async def post(
        self,
        url: str,
        headers: dict | None = None,
        body: dict | None = None,
        timeout_seconds: float = 30.0,
    ) -> TransportResponse:
        return await self.request("POST", url, headers=headers, body=body, timeout_seconds=timeout_seconds)


# ── MockTransport ───────────────────────────────────────────────────


class MockTransport(HTTPTransport):
    """Stores requests in memory. Returns configurable responses.

    Default response: 200, {"status": "ok"}.
    """

    def __init__(self) -> None:
        self._requests: List[_RecordedRequest] = []
        self._status_code: int = 200
        self._body: dict | str = {"status": "ok"}
        self._headers: dict = {}

    def set_response(
        self,
        status_code: int = 200,
        body: dict | str | None = None,
        headers: dict | None = None,
    ) -> None:
        """Configure the response returned by subsequent requests."""
        self._status_code = status_code
        self._body = body if body is not None else {"status": "ok"}
        self._headers = headers or {}

    def requests(self) -> List[_RecordedRequest]:
        """Return list of all recorded requests."""
        return list(self._requests)

    async def request(
        self,
        method: str,
        url: str,
        headers: dict | None = None,
        body: dict | None = None,
        timeout_seconds: float = 30.0,
    ) -> TransportResponse:
        self._requests.append(
            _RecordedRequest(
                method=method,
                url=url,
                headers=headers or {},
                body=body,
                timeout_seconds=timeout_seconds,
            )
        )
        return TransportResponse(
            status_code=self._status_code,
            headers=dict(self._headers),
            body=self._body,
            duration_ms=0.0,
            success=200 <= self._status_code < 400,
        )


# ── DryRunTransport ─────────────────────────────────────────────────


class DryRunTransport(HTTPTransport):
    """Logs what WOULD be sent. Never touches the network.

    Returns a simulated 200 response for every request.
    """

    SIMULATED_BODY: dict = {"status": "dry_run_ok"}

    def __init__(self) -> None:
        self._log: List[_RecordedRequest] = []

    def dry_run_log(self) -> List[_RecordedRequest]:
        """Return list of would-be requests."""
        return list(self._log)

    async def request(
        self,
        method: str,
        url: str,
        headers: dict | None = None,
        body: dict | None = None,
        timeout_seconds: float = 30.0,
    ) -> TransportResponse:
        self._log.append(
            _RecordedRequest(
                method=method,
                url=url,
                headers=headers or {},
                body=body,
                timeout_seconds=timeout_seconds,
            )
        )
        return TransportResponse(
            status_code=200,
            headers={},
            body=self.SIMULATED_BODY,
            duration_ms=0.0,
            success=True,
        )
