"""Transport sandbox policy — domain/method/size constraints for transport layer.

Pure simulation — no real network calls.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Set

from core.http_transport import HTTPTransport, TransportResponse

logger = logging.getLogger(__name__)


class SandboxMode(Enum):
    OFF = "off"            # no restrictions
    RESTRICTED = "restricted"  # allowlist only
    SIMULATION = "simulation"  # block all, return simulated


@dataclass
class SandboxPolicy:
    mode: SandboxMode = SandboxMode.OFF
    allowed_domains: Set[str] = field(default_factory=set)
    blocked_domains: Set[str] = field(default_factory=set)
    allowed_methods: Set[str] = field(default_factory=lambda: {"GET", "POST", "PUT", "DELETE"})
    max_body_bytes: int = 1_048_576  # 1MB
    max_url_length: int = 2048


class TransportSandbox(HTTPTransport):
    """Enforces sandbox policy on transport requests."""

    def __init__(
        self,
        inner: HTTPTransport,
        policy: SandboxPolicy | None = None,
    ) -> None:
        self._inner = inner
        self._policy = policy or SandboxPolicy()
        self._blocked_count = 0

    @property
    def blocked_count(self) -> int:
        return self._blocked_count

    def _extract_domain(self, url: str) -> str:
        without_proto = url.split("://", 1)[-1] if "://" in url else url
        return without_proto.split("/", 1)[0].split(":", 1)[0]

    def _check(self, method: str, url: str, body: dict | None) -> str | None:
        """Return error message if blocked, None if allowed."""
        p = self._policy

        if p.mode == SandboxMode.SIMULATION:
            return "simulation mode blocks all requests"

        if len(url) > p.max_url_length:
            return f"url length {len(url)} exceeds max {p.max_url_length}"

        if method not in p.allowed_methods:
            return f"method {method} not in allowed set"

        domain = self._extract_domain(url)

        if domain in p.blocked_domains:
            return f"domain {domain} is blocked"

        if p.mode == SandboxMode.RESTRICTED and p.allowed_domains:
            if domain not in p.allowed_domains:
                return f"domain {domain} not in allowlist"

        if body:
            import json
            body_size = len(json.dumps(body, default=str).encode())
            if body_size > p.max_body_bytes:
                return f"body size {body_size} exceeds max {p.max_body_bytes}"

        return None

    async def request(
        self,
        method: str,
        url: str,
        headers: dict | None = None,
        body: dict | None = None,
        timeout_seconds: float = 30.0,
    ) -> TransportResponse:
        error = self._check(method, url, body)
        if error:
            self._blocked_count += 1
            logger.warning("sandbox blocked: %s %s — %s", method, url, error)
            return TransportResponse(
                status_code=403,
                headers={},
                body={"error": "sandbox_violation", "detail": error},
                duration_ms=0.0,
                success=False,
            )

        return await self._inner.request(
            method, url, headers=headers, body=body,
            timeout_seconds=timeout_seconds,
        )
