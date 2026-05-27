"""Research workbench performance guard — chunk-size and max rows enforcement.

Ensures large fixtures are not fully loaded, chunked processing enforced.
Pure functions, no network, no exchange.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class PerformanceGuardResult:
    """Result of a performance guard check."""
    allowed: bool
    chunk_size: int
    requested_rows: int
    max_rows: int
    warnings: List[str]


def check_performance_guard(
    requested_rows: int,
    chunk_size: int = 25,
    max_rows: int = 10000,
) -> PerformanceGuardResult:
    """Check if row count is within performance guard limits.

    Pure function. No I/O.
    """
    warnings: List[str] = []
    allowed = True

    if requested_rows > max_rows:
        allowed = False
        warnings.append(f"MAX_ROWS_EXCEEDED: {requested_rows} > {max_rows}")

    if chunk_size <= 0:
        warnings.append("INVALID_CHUNK_SIZE")

    return PerformanceGuardResult(
        allowed=allowed,
        chunk_size=chunk_size,
        requested_rows=requested_rows,
        max_rows=max_rows,
        warnings=warnings,
    )
