"""Transport header normalization — canonical casing, required headers, sanitization.

Pure simulation — no real network calls.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from core.http_transport import HTTPTransport, TransportResponse

logger = logging.getLogger(__name__)


# Standard header canonical forms (lowercase -> canonical)
_CANONICAL_HEADERS = {
    "content-type": "Content-Type",
    "authorization": "Authorization",
    "accept": "Accept",
    "user-agent": "User-Agent",
    "x-api-key": "X-API-Key",
    "x-request-id": "X-Request-ID",
    "cache-control": "Cache-Control",
    "x-ratelimit-remaining": "X-RateLimit-Remaining",
    "x-ratelimit-reset": "X-RateLimit-Reset",
    "retry-after": "Retry-After",
    "content-length": "Content-Length",
}

# Headers that must never be logged (redacted)
_SENSITIVE_HEADERS = {"authorization", "x-api-key", "cookie", "set-cookie"}


@dataclass
class HeaderPolicy:
    """Rules for header normalization."""
    canonicalize_casing: bool = True
    required_headers: Dict[str, str] = field(default_factory=dict)
    forbidden_headers: Set[str] = field(default_factory=set)
    max_header_value_length: int = 4096
    redact_sensitive: bool = True


class HeaderNormalizer:
    """Normalizes request/response headers according to policy."""

    def __init__(self, policy: HeaderPolicy | None = None) -> None:
        self._policy = policy or HeaderPolicy()

    def normalize_request_headers(
        self, headers: dict[str, str] | None
    ) -> dict[str, str]:
        result: dict[str, str] = {}

        # Add required headers first
        result.update(self._policy.required_headers)

        for key, value in (headers or {}).items():
            lower = key.lower()

            # Skip forbidden headers
            if lower in self._policy.forbidden_headers:
                logger.warning("stripped forbidden header: %s", key)
                continue

            # Canonicalize casing
            if self._policy.canonicalize_casing:
                canonical = _CANONICAL_HEADERS.get(lower, key)
            else:
                canonical = key

            # Truncate long values
            if len(value) > self._policy.max_header_value_length:
                value = value[: self._policy.max_header_value_length]
                logger.debug("truncated header %s to %d chars", canonical, self._policy.max_header_value_length)

            result[canonical] = value

        return result

    def normalize_response_headers(
        self, headers: dict[str, str]
    ) -> dict[str, str]:
        result: dict[str, str] = {}
        for key, value in headers.items():
            lower = key.lower()
            if self._policy.canonicalize_casing:
                canonical = _CANONICAL_HEADERS.get(lower, key)
            else:
                canonical = key
            result[canonical] = value
        return result

    def redact_for_logging(self, headers: dict[str, str]) -> dict[str, str]:
        if not self._policy.redact_sensitive:
            return headers
        return {
            k: "***REDACTED***" if k.lower() in _SENSITIVE_HEADERS else v
            for k, v in headers.items()
        }


class HeaderNormalizationTransport(HTTPTransport):
    """Wraps HTTPTransport with header normalization."""

    def __init__(
        self,
        inner: HTTPTransport,
        normalizer: HeaderNormalizer | None = None,
    ) -> None:
        self._inner = inner
        self._normalizer = normalizer or HeaderNormalizer()

    async def request(
        self,
        method: str,
        url: str,
        headers: dict | None = None,
        body: dict | None = None,
        timeout_seconds: float = 30.0,
    ) -> TransportResponse:
        normalized = self._normalizer.normalize_request_headers(headers)
        return await self._inner.request(
            method, url, headers=normalized, body=body,
            timeout_seconds=timeout_seconds,
        )
