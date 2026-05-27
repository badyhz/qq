"""Research workbench data quality — validate local OHLCV fixture quality.

Checks for missing fields, duplicate timestamps, non-monotonic timestamps,
null OHLCV values, and chunked summary.

Pure functions, no network, no exchange.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence


@dataclass(frozen=True)
class DataQualityReport:
    """Report on data quality of a fixture."""
    row_count: int
    missing_required_fields: int
    duplicate_timestamps: int
    non_monotonic_timestamps: int
    null_ohlcv_count: int
    min_timestamp: Optional[float]
    max_timestamp: Optional[float]
    coverage_status: str  # "OK", "PARTIAL", "EMPTY"
    warnings: List[str]


REQUIRED_FIELDS = ("timestamp", "open", "high", "low", "close", "volume")


def check_data_quality(
    bars: Sequence[Dict[str, Any]],
    max_rows: int = 0,
) -> DataQualityReport:
    """Check data quality of OHLCV bars.

    Pure function. No I/O. Deterministic.
    """
    if not bars:
        return DataQualityReport(
            row_count=0,
            missing_required_fields=0,
            duplicate_timestamps=0,
            non_monotonic_timestamps=0,
            null_ohlcv_count=0,
            min_timestamp=None,
            max_timestamp=None,
            coverage_status="EMPTY",
            warnings=["EMPTY_FIXTURE"],
        )

    warnings: List[str] = []
    missing_required = 0
    null_ohlcv = 0
    timestamps: List[float] = []

    for i, bar in enumerate(bars):
        # Check required fields
        for field in REQUIRED_FIELDS:
            if field not in bar or bar[field] is None:
                missing_required += 1

        # Check null OHLCV
        for field in ("open", "high", "low", "close", "volume"):
            val = bar.get(field)
            if val is None or val == 0:
                null_ohlcv += 1

        # Collect timestamps
        ts = bar.get("timestamp")
        if ts is not None:
            timestamps.append(float(ts))

    # Duplicate timestamps
    dup_count = 0
    if timestamps:
        seen = set()
        for ts in timestamps:
            if ts in seen:
                dup_count += 1
            seen.add(ts)

    # Non-monotonic timestamps
    non_monotonic = 0
    for i in range(1, len(timestamps)):
        if timestamps[i] < timestamps[i - 1]:
            non_monotonic += 1

    # Coverage status
    if len(bars) == 0:
        status = "EMPTY"
    elif missing_required > 0 or null_ohlcv > 0:
        status = "PARTIAL"
    else:
        status = "OK"

    if missing_required > 0:
        warnings.append(f"MISSING_REQUIRED_FIELDS: {missing_required}")
    if dup_count > 0:
        warnings.append(f"DUPLICATE_TIMESTAMPS: {dup_count}")
    if non_monotonic > 0:
        warnings.append(f"NON_MONOTONIC_TIMESTAMPS: {non_monotonic}")
    if null_ohlcv > 0:
        warnings.append(f"NULL_OHLCV: {null_ohlcv}")

    return DataQualityReport(
        row_count=len(bars),
        missing_required_fields=missing_required,
        duplicate_timestamps=dup_count,
        non_monotonic_timestamps=non_monotonic,
        null_ohlcv_count=null_ohlcv,
        min_timestamp=min(timestamps) if timestamps else None,
        max_timestamp=max(timestamps) if timestamps else None,
        coverage_status=status,
        warnings=warnings,
    )


def data_quality_to_dict(report: DataQualityReport) -> Dict[str, Any]:
    """Serialize data quality report to dict."""
    return {
        "row_count": report.row_count,
        "missing_required_fields": report.missing_required_fields,
        "duplicate_timestamps": report.duplicate_timestamps,
        "non_monotonic_timestamps": report.non_monotonic_timestamps,
        "null_ohlcv_count": report.null_ohlcv_count,
        "min_timestamp": report.min_timestamp,
        "max_timestamp": report.max_timestamp,
        "coverage_status": report.coverage_status,
        "warnings": list(report.warnings),
    }
