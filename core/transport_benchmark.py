"""Transport benchmark simulator — latency/throughput simulation.

Pure simulation — no real network calls.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import List

from core.http_transport import HTTPTransport, TransportResponse

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    total_requests: int
    successful: int
    failed: int
    total_duration_ms: float
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    requests_per_second: float


class BenchmarkTransport(HTTPTransport):
    """Wraps transport with benchmark measurement."""

    def __init__(self, inner: HTTPTransport) -> None:
        self._inner = inner
        self._latencies: List[float] = []

    def results(self) -> BenchmarkResult:
        if not self._latencies:
            return BenchmarkResult(0, 0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

        sorted_lat = sorted(self._latencies)
        n = len(sorted_lat)
        total = sum(sorted_lat)

        return BenchmarkResult(
            total_requests=n,
            successful=n,  # caller tracks failures separately
            failed=0,
            total_duration_ms=total,
            avg_latency_ms=total / n,
            p50_latency_ms=sorted_lat[n // 2],
            p95_latency_ms=sorted_lat[int(n * 0.95)],
            p99_latency_ms=sorted_lat[int(n * 0.99)],
            requests_per_second=(n / (total / 1000)) if total > 0 else 0.0,
        )

    def reset(self) -> None:
        self._latencies.clear()

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
        elapsed_ms = (time.monotonic() - start) * 1000
        self._latencies.append(elapsed_ms)
        return response


async def run_benchmark(
    transport: HTTPTransport,
    method: str,
    url: str,
    concurrency: int = 1,
    total_requests: int = 10,
    headers: dict | None = None,
    body: dict | None = None,
) -> BenchmarkResult:
    """Run a benchmark against a transport."""
    benchmark = BenchmarkTransport(transport)

    async def single_request():
        await benchmark.request(method, url, headers=headers, body=body)

    # Run with concurrency limit
    sem = asyncio.Semaphore(concurrency)

    async def bounded():
        async with sem:
            await single_request()

    await asyncio.gather(*[bounded() for _ in range(total_requests)])
    return benchmark.results()
