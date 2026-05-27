"""Data quality timestamp audit — monotonicity, duplicates, gaps.

Pure functions. No network.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Sequence, Tuple

from core.data_quality_deep_audit import DataQualityFinding


def audit_timestamps(
    bars: Sequence[Dict[str, Any]],
    symbol: str = "",
    timeframe: str = "",
    split_id: str = "",
    expected_interval_ms: float = 0,
) -> Tuple[DataQualityFinding, ...]:
    """Audit timestamps for monotonicity, duplicates, gaps."""
    findings = []
    if not bars:
        return ()

    timestamps = []
    for bar in bars:
        ts = bar.get("timestamp", bar.get("open_time", 0))
        if ts is not None:
            timestamps.append(float(ts))

    if len(timestamps) < 2:
        return ()

    # Duplicate detection
    seen = set()
    dupes = 0
    for ts in timestamps:
        if ts in seen:
            dupes += 1
        seen.add(ts)

    if dupes > 0:
        findings.append(DataQualityFinding(
            severity="HARD_BLOCK", reason_code="DUPLICATE_TIMESTAMPS",
            affected_symbol=symbol, affected_timeframe=timeframe,
            affected_split=split_id, count=dupes,
            block_promotion=True,
            details=f"{dupes} duplicate timestamps detected",
        ))

    # Non-monotonic detection
    non_mono = 0
    for i in range(1, len(timestamps)):
        if timestamps[i] < timestamps[i - 1]:
            non_mono += 1

    if non_mono > 0:
        findings.append(DataQualityFinding(
            severity="HARD_BLOCK", reason_code="NON_MONOTONIC_TIMESTAMPS",
            affected_symbol=symbol, affected_timeframe=timeframe,
            affected_split=split_id, count=non_mono,
            block_promotion=True,
            details=f"{non_mono} non-monotonic timestamp transitions",
        ))

    # Gap detection (if expected interval provided)
    if expected_interval_ms > 0:
        gaps = 0
        for i in range(1, len(timestamps)):
            diff = timestamps[i] - timestamps[i - 1]
            if diff > expected_interval_ms * 1.5:
                gaps += 1

        if gaps > 0:
            findings.append(DataQualityFinding(
                severity="WARNING", reason_code="MISSING_BARS",
                affected_symbol=symbol, affected_timeframe=timeframe,
                affected_split=split_id, count=gaps,
                block_promotion=False,
                details=f"{gaps} potential missing bars (gaps > 1.5x interval)",
            ))

    return tuple(findings)
