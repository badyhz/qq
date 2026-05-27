"""Transport-level circuit breaker — blocks requests after repeated failures.

Pure simulation — no real network calls.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum

from core.http_transport import HTTPTransport, TransportResponse

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"       # normal operation
    OPEN = "open"           # blocking requests
    HALF_OPEN = "half_open" # testing recovery


@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5
    recovery_timeout_seconds: float = 30.0
    half_open_max_requests: int = 1
    success_threshold: int = 2  # successes in half_open to close


@dataclass
class CircuitBreakerState:
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: float = 0.0
    half_open_requests: int = 0


class TransportCircuitBreaker(HTTPTransport):
    """Wraps HTTPTransport with circuit breaker pattern."""

    def __init__(
        self,
        inner: HTTPTransport,
        config: CircuitBreakerConfig | None = None,
    ) -> None:
        self._inner = inner
        self._config = config or CircuitBreakerConfig()
        self._state = CircuitBreakerState()
        self._blocked_count = 0

    @property
    def circuit_state(self) -> CircuitState:
        return self._state.state

    @property
    def failure_count(self) -> int:
        return self._state.failure_count

    @property
    def blocked_count(self) -> int:
        return self._blocked_count

    def reset(self) -> None:
        self._state = CircuitBreakerState()
        self._blocked_count = 0

    def _check_state(self) -> None:
        if self._state.state == CircuitState.OPEN:
            elapsed = time.monotonic() - self._state.last_failure_time
            if elapsed >= self._config.recovery_timeout_seconds:
                self._state.state = CircuitState.HALF_OPEN
                self._state.half_open_requests = 0
                self._state.success_count = 0
                logger.info("circuit breaker: OPEN -> HALF_OPEN")

    def _record_success(self) -> None:
        if self._state.state == CircuitState.HALF_OPEN:
            self._state.success_count += 1
            if self._state.success_count >= self._config.success_threshold:
                self._state.state = CircuitState.CLOSED
                self._state.failure_count = 0
                logger.info("circuit breaker: HALF_OPEN -> CLOSED")
        elif self._state.state == CircuitState.CLOSED:
            self._state.failure_count = max(0, self._state.failure_count - 1)

    def _record_failure(self) -> None:
        self._state.failure_count += 1
        self._state.last_failure_time = time.monotonic()

        if self._state.state == CircuitState.HALF_OPEN:
            self._state.state = CircuitState.OPEN
            logger.warning("circuit breaker: HALF_OPEN -> OPEN")
        elif self._state.failure_count >= self._config.failure_threshold:
            self._state.state = CircuitState.OPEN
            logger.warning("circuit breaker: CLOSED -> OPEN (failures=%d)", self._state.failure_count)

    async def request(
        self,
        method: str,
        url: str,
        headers: dict | None = None,
        body: dict | None = None,
        timeout_seconds: float = 30.0,
    ) -> TransportResponse:
        self._check_state()

        if self._state.state == CircuitState.OPEN:
            self._blocked_count += 1
            return TransportResponse(
                status_code=503,
                headers={},
                body={"error": "circuit_breaker_open", "failure_count": self._state.failure_count},
                duration_ms=0.0,
                success=False,
            )

        if self._state.state == CircuitState.HALF_OPEN:
            if self._state.half_open_requests >= self._config.half_open_max_requests:
                self._blocked_count += 1
                return TransportResponse(
                    status_code=503,
                    headers={},
                    body={"error": "circuit_breaker_half_open_limit"},
                    duration_ms=0.0,
                    success=False,
                )
            self._state.half_open_requests += 1

        response = await self._inner.request(
            method, url, headers=headers, body=body,
            timeout_seconds=timeout_seconds,
        )

        if response.success:
            self._record_success()
        else:
            self._record_failure()

        return response
