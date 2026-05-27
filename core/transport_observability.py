"""Transport observability hooks — event emission for transport lifecycle.

Pure simulation — no real network calls.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from core.http_transport import HTTPTransport, TransportResponse

logger = logging.getLogger(__name__)


class TransportEvent(Enum):
    REQUEST_STARTED = "request_started"
    REQUEST_COMPLETED = "request_completed"
    REQUEST_FAILED = "request_failed"
    RETRY_ATTEMPTED = "retry_attempted"
    CIRCUIT_OPENED = "circuit_opened"
    RATE_LIMITED = "rate_limited"
    GOVERNANCE_BLOCKED = "governance_blocked"
    SANDBOX_BLOCKED = "sandbox_blocked"
    HEALTH_CHECK = "health_check"


@dataclass
class TransportObservation:
    event: TransportEvent
    timestamp: float
    method: str
    url: str
    adapter_id: str | None = None
    status_code: int | None = None
    duration_ms: float | None = None
    error: str | None = None
    metadata: Dict[str, Any] = field(default_factory=dict)


EventHandler = Callable[[TransportObservation], None]


class TransportObservability(HTTPTransport):
    """Wraps transport with observability event emission."""

    def __init__(self, inner: HTTPTransport, adapter_id: str | None = None) -> None:
        self._inner = inner
        self._adapter_id = adapter_id
        self._handlers: List[EventHandler] = []
        self._observations: List[TransportObservation] = []

    def add_handler(self, handler: EventHandler) -> None:
        self._handlers.append(handler)

    def observations(self) -> List[TransportObservation]:
        return list(self._observations)

    def _emit(self, obs: TransportObservation) -> None:
        self._observations.append(obs)
        for handler in self._handlers:
            try:
                handler(obs)
            except Exception as exc:
                logger.error("observability handler error: %s", exc)

    async def request(
        self,
        method: str,
        url: str,
        headers: dict | None = None,
        body: dict | None = None,
        timeout_seconds: float = 30.0,
    ) -> TransportResponse:
        start = time.monotonic()

        self._emit(TransportObservation(
            event=TransportEvent.REQUEST_STARTED,
            timestamp=time.time(),
            method=method, url=url,
            adapter_id=self._adapter_id,
        ))

        try:
            response = await self._inner.request(
                method, url, headers=headers, body=body,
                timeout_seconds=timeout_seconds,
            )
            elapsed = (time.monotonic() - start) * 1000

            event = TransportEvent.REQUEST_COMPLETED if response.success else TransportEvent.REQUEST_FAILED
            self._emit(TransportObservation(
                event=event,
                timestamp=time.time(),
                method=method, url=url,
                adapter_id=self._adapter_id,
                status_code=response.status_code,
                duration_ms=elapsed,
            ))

            return response

        except Exception as exc:
            elapsed = (time.monotonic() - start) * 1000
            self._emit(TransportObservation(
                event=TransportEvent.REQUEST_FAILED,
                timestamp=time.time(),
                method=method, url=url,
                adapter_id=self._adapter_id,
                duration_ms=elapsed,
                error=str(exc),
            ))
            raise
