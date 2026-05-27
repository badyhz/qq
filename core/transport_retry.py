"""Retry transport wrapper with configurable backoff strategies.

Wraps any HTTPTransport with retry logic for transient failures.
No real network calls — pure simulation layer.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, List

from core.http_transport import HTTPTransport, TransportResponse, TransportError

logger = logging.getLogger(__name__)


class BackoffStrategy(Enum):
    FIXED = "fixed"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"


@dataclass
class RetryConfig:
    max_retries: int = 3
    base_delay_seconds: float = 0.1
    max_delay_seconds: float = 30.0
    backoff: BackoffStrategy = BackoffStrategy.EXPONENTIAL
    retryable_status_codes: tuple[int, ...] = (429, 500, 502, 503, 504)
    jitter: bool = False


@dataclass
class RetryAttempt:
    attempt_number: int
    status_code: int | None
    error: str | None
    delay_seconds: float


class RetryTransport(HTTPTransport):
    """Wraps an HTTPTransport with automatic retry on transient failures."""

    def __init__(
        self,
        inner: HTTPTransport,
        config: RetryConfig | None = None,
    ) -> None:
        self._inner = inner
        self._config = config or RetryConfig()
        self._attempt_log: List[RetryAttempt] = []

    def attempt_log(self) -> List[RetryAttempt]:
        return list(self._attempt_log)

    def _compute_delay(self, attempt: int) -> float:
        cfg = self._config
        if cfg.backoff == BackoffStrategy.FIXED:
            delay = cfg.base_delay_seconds
        elif cfg.backoff == BackoffStrategy.LINEAR:
            delay = cfg.base_delay_seconds * (attempt + 1)
        else:  # EXPONENTIAL
            delay = cfg.base_delay_seconds * (2 ** attempt)
        return min(delay, cfg.max_delay_seconds)

    def _is_retryable(self, response: TransportResponse | None, error: Exception | None) -> bool:
        if error is not None:
            return True  # transport exceptions are retryable
        if response is not None:
            return response.status_code in self._config.retryable_status_codes
        return False

    async def request(
        self,
        method: str,
        url: str,
        headers: dict | None = None,
        body: dict | None = None,
        timeout_seconds: float = 30.0,
    ) -> TransportResponse:
        last_response: TransportResponse | None = None
        last_error: Exception | None = None

        for attempt in range(self._config.max_retries + 1):
            try:
                response = await self._inner.request(
                    method, url, headers=headers, body=body,
                    timeout_seconds=timeout_seconds,
                )

                if not self._is_retryable(response, None) or attempt == self._config.max_retries:
                    self._attempt_log.append(RetryAttempt(
                        attempt_number=attempt,
                        status_code=response.status_code,
                        error=None,
                        delay_seconds=0.0,
                    ))
                    return response

                last_response = response
                delay = self._compute_delay(attempt)
                self._attempt_log.append(RetryAttempt(
                    attempt_number=attempt,
                    status_code=response.status_code,
                    error=f"retryable status {response.status_code}",
                    delay_seconds=delay,
                ))
                await asyncio.sleep(delay)

            except Exception as exc:
                last_error = exc
                if attempt == self._config.max_retries:
                    self._attempt_log.append(RetryAttempt(
                        attempt_number=attempt,
                        status_code=None,
                        error=str(exc),
                        delay_seconds=0.0,
                    ))
                    raise

                delay = self._compute_delay(attempt)
                self._attempt_log.append(RetryAttempt(
                    attempt_number=attempt,
                    status_code=None,
                    error=str(exc),
                    delay_seconds=delay,
                ))
                await asyncio.sleep(delay)

        # All retries exhausted — return last response or raise last error
        if last_response is not None:
            return last_response
        raise last_error  # type: ignore[misc]
