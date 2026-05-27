"""Transport metrics collector — request counts, latency, error rates.

Pure simulation — no real network calls.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List

from core.http_transport import HTTPTransport, TransportResponse

logger = logging.getLogger(__name__)


@dataclass
class RequestMetric:
    method: str
    url: str
    status_code: int
    duration_ms: float
    success: bool
    timestamp: float


@dataclass
class EndpointStats:
    request_count: int = 0
    success_count: int = 0
    error_count: int = 0
    total_duration_ms: float = 0.0
    min_duration_ms: float = float("inf")
    max_duration_ms: float = 0.0

    @property
    def avg_duration_ms(self) -> float:
        if self.request_count == 0:
            return 0.0
        return self.total_duration_ms / self.request_count

    @property
    def error_rate(self) -> float:
        if self.request_count == 0:
            return 0.0
        return self.error_count / self.request_count


class TransportMetrics(HTTPTransport):
    """Wraps HTTPTransport with metrics collection."""

    def __init__(self, inner: HTTPTransport) -> None:
        self._inner = inner
        self._metrics: List[RequestMetric] = []
        self._endpoint_stats: Dict[str, EndpointStats] = defaultdict(EndpointStats)

    def metrics(self) -> List[RequestMetric]:
        return list(self._metrics)

    def endpoint_stats(self) -> Dict[str, EndpointStats]:
        return dict(self._endpoint_stats)

    def global_stats(self) -> EndpointStats:
        total = EndpointStats()
        for stats in self._endpoint_stats.values():
            total.request_count += stats.request_count
            total.success_count += stats.success_count
            total.error_count += stats.error_count
            total.total_duration_ms += stats.total_duration_ms
            total.min_duration_ms = min(total.min_duration_ms, stats.min_duration_ms)
            total.max_duration_ms = max(total.max_duration_ms, stats.max_duration_ms)
        return total

    def reset(self) -> None:
        self._metrics.clear()
        self._endpoint_stats.clear()

    async def request(
        self,
        method: str,
        url: str,
        headers: dict | None = None,
        body: dict | None = None,
        timeout_seconds: float = 30.0,
    ) -> TransportResponse:
        start = time.monotonic()
        response = await self._inner.request(
            method, url, headers=headers, body=body,
            timeout_seconds=timeout_seconds,
        )
        elapsed = (time.monotonic() - start) * 1000

        metric = RequestMetric(
            method=method, url=url,
            status_code=response.status_code,
            duration_ms=elapsed,
            success=response.success,
            timestamp=time.time(),
        )
        self._metrics.append(metric)

        endpoint = f"{method} {_normalize_url(url)}"
        stats = self._endpoint_stats[endpoint]
        stats.request_count += 1
        if response.success:
            stats.success_count += 1
        else:
            stats.error_count += 1
        stats.total_duration_ms += elapsed
        stats.min_duration_ms = min(stats.min_duration_ms, elapsed)
        stats.max_duration_ms = max(stats.max_duration_ms, elapsed)

        return response


def _normalize_url(url: str) -> str:
    """Normalize URL to path only for grouping."""
    without_proto = url.split("://", 1)[-1] if "://" in url else url
    path = without_proto.split("/", 1)[-1] if "/" in without_proto else ""
    return "/" + path
