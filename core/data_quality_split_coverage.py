"""Data quality split coverage — detect inconsistent split coverage.

Pure functions. No network.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


@dataclass(frozen=True)
class SplitCoverageResult:
    """Split coverage validation result."""
    split_id: str
    symbol: str
    timeframe: str
    aligned: bool
    row_count: int
    expected_rows: int
    mismatch: bool
    block_promotion: bool


def validate_split_coverage(
    splits: List[Dict[str, Any]],
    expected_rows_per_split: int = 0,
) -> Tuple[SplitCoverageResult, ...]:
    """Validate that all splits have consistent coverage."""
    results = []
    for s in splits:
        row_count = s.get("row_count", 0)
        expected = expected_rows_per_split or row_count
        mismatch = abs(row_count - expected) > max(1, expected * 0.1)
        results.append(SplitCoverageResult(
            split_id=s.get("split_id", ""),
            symbol=s.get("symbol", ""),
            timeframe=s.get("timeframe", ""),
            aligned=not mismatch,
            row_count=row_count,
            expected_rows=expected,
            mismatch=mismatch,
            block_promotion=mismatch and row_count < expected * 0.5,
        ))
    return tuple(results)


def split_coverage_to_dict(results: Tuple[SplitCoverageResult, ...]) -> Dict:
    return {
        "splits": [
            {
                "split_id": r.split_id, "symbol": r.symbol,
                "timeframe": r.timeframe, "aligned": r.aligned,
                "row_count": r.row_count, "expected_rows": r.expected_rows,
                "mismatch": r.mismatch, "block_promotion": r.block_promotion,
            }
            for r in results
        ],
        "total_splits": len(results),
        "aligned_count": sum(1 for r in results if r.aligned),
        "mismatch_count": sum(1 for r in results if r.mismatch),
    }
