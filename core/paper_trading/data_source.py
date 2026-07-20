"""Readonly data source abstraction — no network, no account, no orders."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import math
from typing import Any, Dict, List, Optional, Union


CLOSED_BAR_CONTRACT_VERSION = "closed_bar_v1"
_FIXED_INTERVAL_SECONDS = {
    "1m": 60,
    "3m": 180,
    "5m": 300,
    "15m": 900,
    "30m": 1800,
    "1h": 3600,
    "4h": 14400,
    "1d": 86400,
}


@dataclass(frozen=True)
class MarketBar:
    """Single K-line bar — readonly."""
    timestamp: float
    open: float
    high: float
    low: float
    close: float
    volume: float
    symbol: str = ""
    timeframe: str = ""
    close_time: Optional[datetime] = None
    provider_closed: Optional[bool] = None


@dataclass(frozen=True)
class ClosedBarResult:
    """Canonical closed bars and summary-level rejection diagnostics."""
    bars: List[MarketBar]
    decision_cutoff: str
    raw_count: int
    eligible_count: int
    rejected_forming_or_future: int
    rejected_malformed: int
    rejected_conflicting_duplicate: int
    signal_bar_close_time: Optional[str]
    contract_version: str = CLOSED_BAR_CONTRACT_VERSION


def parse_aware_utc(value: Union[datetime, str], label: str) -> datetime:
    """Parse an explicitly timezone-aware timestamp and normalize it to UTC."""
    parsed = value
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(f"{label} is invalid") from exc
    if not isinstance(parsed, datetime) or parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{label} must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def format_utc_timestamp(value: datetime) -> str:
    """Serialize contract timestamps in one stable UTC RFC3339 representation."""
    return parse_aware_utc(value, "timestamp").isoformat(timespec="milliseconds")


def utc_datetime_from_epoch_ms(value: Any) -> datetime:
    """Convert provider epoch milliseconds to an aware UTC datetime."""
    return datetime.fromtimestamp(float(value) / 1000.0, timezone.utc)


def _resolved_close_time(bar: MarketBar) -> datetime:
    """Resolve authoritative/derived close time and verify interval consistency."""
    interval_seconds = _FIXED_INTERVAL_SECONDS.get(str(bar.timeframe).lower())
    if interval_seconds is None:
        raise ValueError("unsupported or missing timeframe")
    try:
        opened = datetime.fromtimestamp(float(bar.timestamp), timezone.utc)
    except (TypeError, ValueError, OSError, OverflowError) as exc:
        raise ValueError("invalid open timestamp") from exc
    expected_exclusive = opened + timedelta(seconds=interval_seconds)
    if bar.close_time is None:
        return expected_exclusive
    explicit = parse_aware_utc(bar.close_time, "bar.close_time")
    # Binance reports the inclusive end millisecond; derived fixtures use the
    # exclusive interval boundary. Both must describe the same declared bar.
    if abs((explicit - expected_exclusive).total_seconds()) > 1.0:
        raise ValueError("close time is inconsistent with open time and interval")
    return explicit


def select_closed_bars(
    bars: List[MarketBar],
    decision_cutoff: Union[datetime, str],
) -> ClosedBarResult:
    """Canonicalize and select bars closed at the inclusive decision boundary.

    Eligibility is uniformly ``bar.close_time <= decision_cutoff``. Validation,
    ordering, duplicate handling and the cutoff all happen before indicators.
    Conflicting rows for one open-time identity are excluded as a group.
    """
    cutoff = parse_aware_utc(decision_cutoff, "decision_cutoff")
    canonical: dict[tuple[str, str, float], tuple[MarketBar, datetime, tuple[Any, ...]]] = {}
    conflicts: set[tuple[str, str, float]] = set()
    malformed = 0

    for bar in bars:
        try:
            opened = float(bar.timestamp)
            close_time = _resolved_close_time(bar)
            key = (str(bar.symbol).upper(), str(bar.timeframe).lower(), opened)
            numeric = (
                float(bar.open), float(bar.high), float(bar.low),
                float(bar.close), float(bar.volume),
            )
            if not all(math.isfinite(value) for value in (opened, *numeric)):
                raise ValueError("non-finite candle value")
            open_price, high, low, close_price, volume = numeric
            if (
                min(open_price, high, low, close_price) <= 0
                or volume < 0
                or high < max(open_price, close_price, low)
                or low > min(open_price, close_price, high)
            ):
                raise ValueError("invalid OHLCV candle")
            content = (
                *numeric, format_utc_timestamp(close_time), bar.provider_closed,
            )
        except (TypeError, ValueError, OSError, OverflowError):
            malformed += 1
            continue
        previous = canonical.get(key)
        if previous is not None and previous[2] != content:
            conflicts.add(key)
            continue
        canonical[key] = (bar, close_time, content)

    for key in conflicts:
        canonical.pop(key, None)

    eligible: List[tuple[float, MarketBar, datetime]] = []
    future_or_forming = 0
    for (_symbol, _timeframe, opened), (bar, close_time, _content) in canonical.items():
        if bar.provider_closed is False or close_time > cutoff:
            future_or_forming += 1
            continue
        eligible.append((opened, bar, close_time))
    eligible.sort(key=lambda item: item[0])

    normalized = [
        MarketBar(
            timestamp=bar.timestamp,
            open=bar.open,
            high=bar.high,
            low=bar.low,
            close=bar.close,
            volume=bar.volume,
            symbol=bar.symbol,
            timeframe=bar.timeframe,
            close_time=close_time,
            provider_closed=True,
        )
        for _opened, bar, close_time in eligible
    ]
    final_close = format_utc_timestamp(eligible[-1][2]) if eligible else None
    return ClosedBarResult(
        bars=normalized,
        decision_cutoff=format_utc_timestamp(cutoff),
        raw_count=len(bars),
        eligible_count=len(normalized),
        rejected_forming_or_future=future_or_forming,
        rejected_malformed=malformed,
        rejected_conflicting_duplicate=len(conflicts),
        signal_bar_close_time=final_close,
    )


@dataclass(frozen=True)
class MarketSnapshot:
    """Point-in-time market snapshot — readonly."""
    symbol: str
    price: float
    timestamp: float
    bid: float = 0.0
    ask: float = 0.0
    volume_24h: float = 0.0
    source: str = ""


@dataclass(frozen=True)
class DataSourceConfig:
    """Data source configuration — readonly."""
    mode: str = "fixture"  # "fixture" or "snapshot"
    fixture_path: Optional[str] = None
    symbol: str = "BTCUSDT"
    timeframe: str = "1h"
    network_enabled: bool = False


class DataSource(ABC):
    """Abstract base for readonly data sources.

    Only provides market data. No account, no balance, no position,
    no order, no cancel, no fill, no execution.
    """

    @abstractmethod
    def get_bars(self, symbol: str, timeframe: str = "1h", limit: int = 100) -> List[MarketBar]:
        """Get historical K-line bars — readonly."""
        ...

    @abstractmethod
    def get_snapshot(self, symbol: str) -> Optional[MarketSnapshot]:
        """Get current market snapshot — readonly."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if data source is available."""
        ...

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Data source identifier."""
        ...


def create_data_source(config: DataSourceConfig) -> DataSource:
    """Factory for data sources. No network, no secret, no order."""
    if config.mode == "fixture":
        from core.paper_trading.fixture_adapter import FixtureDataSource
        return FixtureDataSource(config)
    elif config.mode == "snapshot":
        from core.paper_trading.snapshot_adapter import SnapshotAdapter
        return SnapshotAdapter(config)
    else:
        raise ValueError(f"Unknown data source mode: {config.mode}")
