"""Transport health check — lightweight readiness probe.

Pure simulation — no real network calls.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import List

from core.http_transport import HTTPTransport, TransportResponse

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class HealthCheckResult:
    status: HealthStatus
    latency_ms: float
    timestamp: float
    error: str | None = None


class TransportHealthCheck:
    """Periodic health probe against a transport endpoint."""

    def __init__(
        self,
        transport: HTTPTransport,
        health_url: str = "https://health.local/ping",
        timeout_seconds: float = 5.0,
        latency_threshold_ms: float = 1000.0,
    ) -> None:
        self._transport = transport
        self._health_url = health_url
        self._timeout = timeout_seconds
        self._latency_threshold = latency_threshold_ms
        self._history: List[HealthCheckResult] = []

    def history(self) -> List[HealthCheckResult]:
        return list(self._history)

    def current_status(self) -> HealthStatus:
        if not self._history:
            return HealthStatus.UNHEALTHY
        return self._history[-1].status

    async def check(self) -> HealthCheckResult:
        start = time.monotonic()
        try:
            response = await self._transport.request(
                "GET", self._health_url,
                timeout_seconds=self._timeout,
            )
            latency = (time.monotonic() - start) * 1000

            if not response.success:
                result = HealthCheckResult(
                    status=HealthStatus.UNHEALTHY,
                    latency_ms=latency,
                    timestamp=time.time(),
                    error=f"status {response.status_code}",
                )
            elif latency > self._latency_threshold:
                result = HealthCheckResult(
                    status=HealthStatus.DEGRADED,
                    latency_ms=latency,
                    timestamp=time.time(),
                )
            else:
                result = HealthCheckResult(
                    status=HealthStatus.HEALTHY,
                    latency_ms=latency,
                    timestamp=time.time(),
                )

        except Exception as exc:
            latency = (time.monotonic() - start) * 1000
            result = HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                latency_ms=latency,
                timestamp=time.time(),
                error=str(exc),
            )

        self._history.append(result)
        return result
