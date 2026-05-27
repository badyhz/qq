"""Timeout matrix transport — per-method, per-domain, per-adapter timeouts.

Pure simulation — no real network calls.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, Optional

from core.http_transport import HTTPTransport, TransportResponse

logger = logging.getLogger(__name__)


@dataclass
class TimeoutRule:
    method: str | None = None
    domain: str | None = None
    adapter_id: str | None = None
    timeout_seconds: float = 30.0
    priority: int = 0  # higher = more specific


class TimeoutMatrix:
    """Manages timeout rules with priority-based resolution."""

    def __init__(self, default_timeout: float = 30.0) -> None:
        self._default = default_timeout
        self._rules: list[TimeoutRule] = []

    def add_rule(self, rule: TimeoutRule) -> None:
        self._rules.append(rule)
        self._rules.sort(key=lambda r: r.priority, reverse=True)

    def resolve(
        self,
        method: str | None = None,
        domain: str | None = None,
        adapter_id: str | None = None,
    ) -> float:
        for rule in self._rules:
            if rule.method and rule.method != method:
                continue
            if rule.domain and rule.domain != domain:
                continue
            if rule.adapter_id and rule.adapter_id != adapter_id:
                continue
            return rule.timeout_seconds
        return self._default

    def rules(self) -> list[TimeoutRule]:
        return list(self._rules)


class TimeoutTransport(HTTPTransport):
    """Wraps HTTPTransport with per-request timeout resolution from matrix."""

    def __init__(
        self,
        inner: HTTPTransport,
        matrix: TimeoutMatrix | None = None,
    ) -> None:
        self._inner = inner
        self._matrix = matrix or TimeoutMatrix()

    @property
    def matrix(self) -> TimeoutMatrix:
        return self._matrix

    async def request(
        self,
        method: str,
        url: str,
        headers: dict | None = None,
        body: dict | None = None,
        timeout_seconds: float = 30.0,
    ) -> TransportResponse:
        domain = _extract_domain(url)
        resolved = self._matrix.resolve(method=method, domain=domain)

        logger.debug("timeout resolved: %s %s -> %.1fs", method, url, resolved)

        return await self._inner.request(
            method, url, headers=headers, body=body,
            timeout_seconds=resolved,
        )


def _extract_domain(url: str) -> str:
    """Extract domain from URL."""
    without_proto = url.split("://", 1)[-1] if "://" in url else url
    return without_proto.split("/", 1)[0].split(":", 1)[0]
