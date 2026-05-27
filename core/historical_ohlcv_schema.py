"""Historical OHLCV schema models for offline backtest research lab.

Pure frozen dataclasses — no I/O, no network, no side effects.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Sequence


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class IssueType(str, Enum):
    GAP = "GAP"
    DUPLICATE = "DUPLICATE"
    INVALID_OHLCV = "INVALID_OHLCV"
    NEGATIVE_VOLUME = "NEGATIVE_VOLUME"
    ZERO_RANGE = "ZERO_RANGE"


class Severity(str, Enum):
    WARNING = "WARNING"
    ERROR = "ERROR"


# ---------------------------------------------------------------------------
# Core models
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class HistoricalTimeframe:
    """Describes a candle timeframe."""
    label: str
    minutes: int

    def __post_init__(self) -> None:
        if not self.label or not isinstance(self.label, str):
            raise ValueError("label must be a non-empty string")
        if not isinstance(self.minutes, int) or self.minutes <= 0:
            raise ValueError("minutes must be a positive integer")


@dataclass(frozen=True)
class HistoricalBar:
    """Single historical OHLCV bar."""
    timestamp: float
    open: float
    high: float
    low: float
    close: float
    volume: float
    symbol: str
    timeframe: str

    def __post_init__(self) -> None:
        if not self.symbol:
            raise ValueError("symbol must be non-empty")
        if not self.timeframe:
            raise ValueError("timeframe must be non-empty")
        if self.high < self.low:
            raise ValueError(
                f"high ({self.high}) must be >= low ({self.low})"
            )
        if self.volume < 0:
            raise ValueError(
                f"volume ({self.volume}) must be non-negative"
            )


@dataclass(frozen=True)
class HistoricalDataIssue:
    """A single data quality issue found during validation."""
    issue_type: IssueType
    severity: Severity
    timestamp: float
    detail: str

    def __post_init__(self) -> None:
        if not isinstance(self.issue_type, IssueType):
            raise ValueError("issue_type must be an IssueType enum")
        if not isinstance(self.severity, Severity):
            raise ValueError("severity must be a Severity enum")
        if not self.detail:
            raise ValueError("detail must be non-empty")


@dataclass(frozen=True)
class HistoricalDataQualityReport:
    """Aggregate quality report for a symbol/timeframe dataset."""
    symbol: str
    timeframe: str
    total_rows: int
    valid_rows: int
    duplicate_count: int
    gap_count: int
    invalid_ohlcv_count: int
    issues: tuple  # tuple[HistoricalDataIssue, ...]
    is_clean: bool

    def __post_init__(self) -> None:
        if not self.symbol:
            raise ValueError("symbol must be non-empty")
        if not self.timeframe:
            raise ValueError("timeframe must be non-empty")
        if self.total_rows < 0:
            raise ValueError("total_rows must be >= 0")
        if self.valid_rows < 0:
            raise ValueError("valid_rows must be >= 0")
        if self.valid_rows > self.total_rows:
            raise ValueError("valid_rows cannot exceed total_rows")
        if self.duplicate_count < 0:
            raise ValueError("duplicate_count must be >= 0")
        if self.gap_count < 0:
            raise ValueError("gap_count must be >= 0")
        if self.invalid_ohlcv_count < 0:
            raise ValueError("invalid_ohlcv_count must be >= 0")
        # is_clean consistency: clean means no issues at all
        expected_clean = (
            self.duplicate_count == 0
            and self.gap_count == 0
            and self.invalid_ohlcv_count == 0
        )
        if self.is_clean != expected_clean:
            raise ValueError(
                f"is_clean={self.is_clean} inconsistent with issue counts "
                f"(dup={self.duplicate_count}, gap={self.gap_count}, "
                f"invalid={self.invalid_ohlcv_count})"
            )


@dataclass(frozen=True)
class HistoricalSymbolDataset:
    """A complete loaded dataset for one symbol/timeframe."""
    symbol: str
    timeframe: str
    bars: tuple  # tuple[HistoricalBar, ...]
    bar_count: int

    def __post_init__(self) -> None:
        if not self.symbol:
            raise ValueError("symbol must be non-empty")
        if not self.timeframe:
            raise ValueError("timeframe must be non-empty")
        if self.bar_count != len(self.bars):
            raise ValueError(
                f"bar_count ({self.bar_count}) != len(bars) ({len(self.bars)})"
            )


@dataclass(frozen=True)
class OHLCVColumnMapping:
    """Column name mapping for CSV ingestion."""
    timestamp_col: str
    open_col: str
    high_col: str
    low_col: str
    close_col: str
    volume_col: str

    def __post_init__(self) -> None:
        for name in (
            "timestamp_col", "open_col", "high_col",
            "low_col", "close_col", "volume_col",
        ):
            val = getattr(self, name)
            if not val or not isinstance(val, str):
                raise ValueError(f"{name} must be a non-empty string")
