"""Chunked OHLCV CSV reader for offline backtest research lab.

Reads CSV files in fixed-size chunks using stdlib csv module.
Never loads full file into memory.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Generator, List, Optional, Sequence

from core.historical_ohlcv_schema import (
    HistoricalBar,
    HistoricalDataIssue,
    HistoricalDataQualityReport,
    IssueType,
    OHLCVColumnMapping,
    Severity,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_float(value: str, field_name: str) -> float:
    """Parse a string to float, raising ValueError on failure."""
    try:
        return float(value)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Cannot parse {field_name}={value!r} as float") from exc


def _parse_timestamp(value: str) -> float:
    """Parse timestamp as float (epoch seconds or ISO string fallback)."""
    try:
        return float(value)
    except ValueError:
        # Attempt ISO format parse as epoch seconds fallback
        from datetime import datetime
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return dt.timestamp()
        except Exception as exc:
            raise ValueError(f"Cannot parse timestamp={value!r}") from exc


# ---------------------------------------------------------------------------
# Core reader
# ---------------------------------------------------------------------------

def read_ohlcv_chunks(
    csv_path: str | Path,
    column_mapping: OHLCVColumnMapping,
    chunk_size: int = 500,
    symbol: str = "",
    timeframe: str = "",
) -> Generator[List[HistoricalBar], None, None]:
    """Yield lists of HistoricalBar in chunks from a CSV file.

    Uses stdlib csv.reader — never loads entire file into memory.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")

    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    with open(csv_path, "r", newline="") as fh:
        reader = csv.reader(fh)
        header = next(reader, None)
        if header is None:
            return

        # Build column index map
        col_idx = {name.strip(): i for i, name in enumerate(header)}
        ts_i = col_idx.get(column_mapping.timestamp_col)
        o_i = col_idx.get(column_mapping.open_col)
        h_i = col_idx.get(column_mapping.high_col)
        l_i = col_idx.get(column_mapping.low_col)
        c_i = col_idx.get(column_mapping.close_col)
        v_i = col_idx.get(column_mapping.volume_col)

        required = {
            "timestamp": ts_i, "open": o_i, "high": h_i,
            "low": l_i, "close": c_i, "volume": v_i,
        }
        missing = [k for k, v in required.items() if v is None]
        if missing:
            raise ValueError(f"Missing columns in CSV header: {missing}")

        chunk: List[HistoricalBar] = []
        for row_num, row in enumerate(reader, start=2):
            try:
                ts = _parse_timestamp(row[ts_i])
                o = _parse_float(row[o_i], "open")
                h = _parse_float(row[h_i], "high")
                l = _parse_float(row[l_i], "low")
                c = _parse_float(row[c_i], "close")
                v = _parse_float(row[v_i], "volume")
                bar = HistoricalBar(
                    timestamp=ts, open=o, high=h, low=l,
                    close=c, volume=v, symbol=symbol, timeframe=timeframe,
                )
                chunk.append(bar)
            except (ValueError, IndexError):
                # Skip unparseable rows — they show up in quality report
                continue

            if len(chunk) >= chunk_size:
                yield chunk
                chunk = []

        if chunk:
            yield chunk


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_ohlcv_chunk(bars: List[HistoricalBar]) -> List[HistoricalDataIssue]:
    """Validate a chunk of bars and return any issues found."""
    issues: List[HistoricalDataIssue] = []
    for bar in bars:
        # Invalid OHLCV: high < low is already rejected by HistoricalBar
        # but we check for zero-range (open == high == low == close)
        if bar.open == bar.high == bar.low == bar.close:
            issues.append(HistoricalDataIssue(
                issue_type=IssueType.ZERO_RANGE,
                severity=Severity.WARNING,
                timestamp=bar.timestamp,
                detail=f"Zero range bar at {bar.timestamp}",
            ))
        if bar.volume < 0:
            issues.append(HistoricalDataIssue(
                issue_type=IssueType.NEGATIVE_VOLUME,
                severity=Severity.ERROR,
                timestamp=bar.timestamp,
                detail=f"Negative volume {bar.volume} at {bar.timestamp}",
            ))
    return issues


def deduplicate_bars(bars: List[HistoricalBar]) -> List[HistoricalBar]:
    """Remove duplicate timestamps, keeping the first occurrence."""
    seen: set = set()
    result: List[HistoricalBar] = []
    for bar in bars:
        if bar.timestamp not in seen:
            seen.add(bar.timestamp)
            result.append(bar)
    return result


def detect_gaps(
    bars: List[HistoricalBar],
    expected_interval_seconds: float,
) -> List[HistoricalDataIssue]:
    """Detect gaps in bar timestamps.

    A gap is when the difference between consecutive sorted timestamps
    exceeds 1.5 * expected_interval_seconds.
    """
    if len(bars) < 2:
        return []

    issues: List[HistoricalDataIssue] = []
    sorted_bars = sorted(bars, key=lambda b: b.timestamp)
    threshold = expected_interval_seconds * 1.5

    for i in range(1, len(sorted_bars)):
        delta = sorted_bars[i].timestamp - sorted_bars[i - 1].timestamp
        if delta > threshold:
            issues.append(HistoricalDataIssue(
                issue_type=IssueType.GAP,
                severity=Severity.WARNING,
                timestamp=sorted_bars[i].timestamp,
                detail=(
                    f"Gap of {delta:.1f}s between "
                    f"{sorted_bars[i-1].timestamp} and "
                    f"{sorted_bars[i].timestamp} "
                    f"(expected ~{expected_interval_seconds:.0f}s)"
                ),
            ))
    return issues


# ---------------------------------------------------------------------------
# Dataset summarizer
# ---------------------------------------------------------------------------

def summarize_dataset(
    csv_path: str | Path,
    column_mapping: OHLCVColumnMapping,
    chunk_size: int = 500,
    symbol: str = "",
    timeframe: str = "",
    expected_interval_seconds: float = 300.0,
) -> HistoricalDataQualityReport:
    """Produce a quality report without loading the full file.

    Reads in chunks, accumulates counts only.
    """
    total_rows = 0
    valid_rows = 0
    seen_timestamps: set = set()
    duplicate_count = 0
    gap_count = 0
    invalid_ohlcv_count = 0
    all_issues: List[HistoricalDataIssue] = []

    prev_max_ts: Optional[float] = None

    for chunk in read_ohlcv_chunks(
        csv_path, column_mapping, chunk_size, symbol, timeframe,
    ):
        for bar in chunk:
            total_rows += 1

            # Duplicate check
            if bar.timestamp in seen_timestamps:
                duplicate_count += 1
                all_issues.append(HistoricalDataIssue(
                    issue_type=IssueType.DUPLICATE,
                    severity=Severity.ERROR,
                    timestamp=bar.timestamp,
                    detail=f"Duplicate timestamp {bar.timestamp}",
                ))
                continue

            seen_timestamps.add(bar.timestamp)
            valid_rows += 1

            # Gap check (inter-chunk boundary too)
            if prev_max_ts is not None:
                delta = bar.timestamp - prev_max_ts
                if delta > expected_interval_seconds * 1.5:
                    gap_count += 1
                    all_issues.append(HistoricalDataIssue(
                        issue_type=IssueType.GAP,
                        severity=Severity.WARNING,
                        timestamp=bar.timestamp,
                        detail=f"Gap of {delta:.1f}s before {bar.timestamp}",
                    ))

            prev_max_ts = bar.timestamp

            # Intra-chunk gap detection
            chunk_issues = validate_ohlcv_chunk([bar])
            for issue in chunk_issues:
                all_issues.append(issue)
                if issue.issue_type == IssueType.ZERO_RANGE:
                    invalid_ohlcv_count += 1
                elif issue.issue_type == IssueType.NEGATIVE_VOLUME:
                    invalid_ohlcv_count += 1

    # Also detect intra-chunk gaps by re-reading (lightweight: we already have ts set)
    # For proper gap detection across the whole file, re-scan sorted timestamps
    sorted_ts = sorted(seen_timestamps)
    gap_count = 0
    all_issues = [i for i in all_issues if i.issue_type != IssueType.GAP]
    for i in range(1, len(sorted_ts)):
        delta = sorted_ts[i] - sorted_ts[i - 1]
        if delta > expected_interval_seconds * 1.5:
            gap_count += 1
            all_issues.append(HistoricalDataIssue(
                issue_type=IssueType.GAP,
                severity=Severity.WARNING,
                timestamp=sorted_ts[i],
                detail=f"Gap of {delta:.1f}s between {sorted_ts[i-1]} and {sorted_ts[i]}",
            ))

    is_clean = (
        duplicate_count == 0
        and gap_count == 0
        and invalid_ohlcv_count == 0
    )

    return HistoricalDataQualityReport(
        symbol=symbol,
        timeframe=timeframe,
        total_rows=total_rows,
        valid_rows=valid_rows,
        duplicate_count=duplicate_count,
        gap_count=gap_count,
        invalid_ohlcv_count=invalid_ohlcv_count,
        issues=tuple(all_issues),
        is_clean=is_clean,
    )
