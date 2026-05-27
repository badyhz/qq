"""Transport request deduplication — coalesce identical in-flight requests.

Pure simulation — no real network calls.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from typing import Dict

from core.http_transport import HTTPTransport, TransportResponse

logger = logging.getLogger(__name__)


def _request_key(method: str, url: str, body: dict | None) -> str:
    """Generate dedup key from request params."""
    raw = f"{method}:{url}:{json.dumps(body, sort_keys=True, default=str)}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


class DedupTransport(HTTPTransport):
    """Coalesces identical in-flight requests into a single call."""

    def __init__(self, inner: HTTPTransport) -> None:
        self._inner = inner
        self._in_flight: Dict[str, asyncio.Future[TransportResponse]] = {}
        self._dedup_count = 0

    @property
    def dedup_count(self) -> int:
        return self._dedup_count

    async def request(
        self,
        method: str,
        url: str,
        headers: dict | None = None,
        body: dict | None = None,
        timeout_seconds: float = 30.0,
    ) -> TransportResponse:
        key = _request_key(method, url, body)

        if key in self._in_flight:
            self._dedup_count += 1
            logger.debug("dedup hit: %s %s", method, url)
            return await self._in_flight[key]

        future: asyncio.Future[TransportResponse] = asyncio.get_event_loop().create_future()
        self._in_flight[key] = future

        try:
            response = await self._inner.request(
                method, url, headers=headers, body=body,
                timeout_seconds=timeout_seconds,
            )
            future.set_result(response)
            return response
        except Exception as exc:
            future.set_exception(exc)
            raise
        finally:
            self._in_flight.pop(key, None)
