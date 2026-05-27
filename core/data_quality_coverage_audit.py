"""Data quality coverage audit — symbol/timeframe/stale coverage.

Pure functions. No network.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


@dataclass(frozen=True)
class CoverageStatus:
    """Coverage status for a symbol/timeframe pair."""
    symbol: str
    timeframe: str
    row_count: int
    coverage_status: str  # FRESH, STALE, PARTIAL, INSUFFICIENT, EMPTY
    last_timestamp: float = 0
    warnings: Tuple[str, ...] = ()


def assess_coverage(
    row_count: int,
    symbol: str = "",
    timeframe: str = "",
    last_timestamp: float = 0,
    min_rows: int = 10,
    stale_threshold_s: float = 86400 * 7,
) -> CoverageStatus:
    """Assess coverage status."""
    if row_count == 0:
        return CoverageStatus(symbol, timeframe, 0, "EMPTY", last_timestamp, ("EMPTY_FIXTURE",))
    elif row_count < min_rows:
        return CoverageStatus(symbol, timeframe, row_count, "INSUFFICIENT", last_timestamp,
                              (f"Only {row_count} rows, need {min_rows}",))
    elif row_count < min_rows * 3:
        return CoverageStatus(symbol, timeframe, row_count, "PARTIAL", last_timestamp,
                              (f"Low coverage: {row_count} rows",))
    else:
        return CoverageStatus(symbol, timeframe, row_count, "FRESH", last_timestamp)


def audit_coverage(
    coverage_map: Dict[Tuple[str, str], int],
    min_rows: int = 10,
) -> Tuple[CoverageStatus, ...]:
    """Audit coverage across all symbol/timeframe pairs."""
    results = []
    for (sym, tf), count in sorted(coverage_map.items()):
        results.append(assess_coverage(count, sym, tf, min_rows=min_rows))
    return tuple(results)


def coverage_audit_to_dict(statuses: Tuple[CoverageStatus, ...]) -> Dict:
    return {
        "coverage": [
            {
                "symbol": s.symbol, "timeframe": s.timeframe,
                "row_count": s.row_count, "coverage_status": s.coverage_status,
                "last_timestamp": s.last_timestamp,
                "warnings": list(s.warnings),
            }
            for s in statuses
        ],
        "total_pairs": len(statuses),
        "fresh_count": sum(1 for s in statuses if s.coverage_status == "FRESH"),
        "stale_count": sum(1 for s in statuses if s.coverage_status == "STALE"),
        "insufficient_count": sum(1 for s in statuses if s.coverage_status == "INSUFFICIENT"),
    }
