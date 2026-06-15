"""Market data contract — typed containers for candle/market data.

All data flowing through the system must use these types.
Fixture/mock data MUST set is_fixture=True, is_live=False.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class Candle:
    """Single OHLCV candle."""
    symbol: str
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    timeframe: str = "15m"
    is_fixture: bool = True
    is_live: bool = False
    source: str = "fixture"

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "timeframe": self.timeframe,
            "is_fixture": self.is_fixture,
            "is_live": self.is_live,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Candle:
        return cls(
            symbol=data["symbol"],
            timestamp=data["timestamp"],
            open=float(data["open"]),
            high=float(data["high"]),
            low=float(data["low"]),
            close=float(data["close"]),
            volume=float(data["volume"]),
            timeframe=data.get("timeframe", "15m"),
            is_fixture=data.get("is_fixture", True),
            is_live=data.get("is_live", False),
            source=data.get("source", "fixture"),
        )

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.symbol:
            errors.append("symbol is required")
        if not self.timestamp:
            errors.append("timestamp is required")
        if self.high < self.low:
            errors.append(f"high ({self.high}) < low ({self.low})")
        if self.close <= 0:
            errors.append("close must be > 0")
        if self.volume < 0:
            errors.append("volume must be >= 0")
        if self.is_live:
            errors.append("is_live must be False for fixture/mock data")
        if not self.is_fixture and self.source in ("fixture", "mock", "sample", "local"):
            errors.append("is_fixture must be True when source is fixture/mock/sample/local")
        return errors


@dataclass
class CandleSeries:
    """Ordered series of candles for a single symbol."""
    symbol: str
    timeframe: str = "15m"
    candles: list[Candle] = field(default_factory=list)
    is_fixture: bool = True
    is_live: bool = False
    source: str = "fixture"

    @property
    def count(self) -> int:
        return len(self.candles)

    @property
    def is_empty(self) -> bool:
        return len(self.candles) == 0

    @property
    def closes(self) -> list[float]:
        return [c.close for c in self.candles]

    @property
    def highs(self) -> list[float]:
        return [c.high for c in self.candles]

    @property
    def lows(self) -> list[float]:
        return [c.low for c in self.candles]

    @property
    def volumes(self) -> list[float]:
        return [c.volume for c in self.candles]

    @property
    def timestamps(self) -> list[str]:
        return [c.timestamp for c in self.candles]

    def to_dicts(self) -> list[dict[str, Any]]:
        return [c.to_dict() for c in self.candles]

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.symbol:
            errors.append("symbol is required")
        if self.is_live:
            errors.append("is_live must be False")
        for i, candle in enumerate(self.candles):
            candle_errors = candle.validate()
            for err in candle_errors:
                errors.append(f"candle[{i}]: {err}")
        return errors


@dataclass
class MarketDataBatch:
    """Batch of candle series for multiple symbols."""
    series: dict[str, CandleSeries] = field(default_factory=dict)
    batch_id: str = ""
    loaded_at: str = field(default_factory=_utc_now_iso)
    is_fixture: bool = True
    is_live: bool = False
    source: str = "fixture"

    @property
    def symbols(self) -> list[str]:
        return list(self.series.keys())

    @property
    def total_candles(self) -> int:
        return sum(s.count for s in self.series.values())

    def get_series(self, symbol: str) -> CandleSeries | None:
        return self.series.get(symbol)

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.is_live:
            errors.append("is_live must be False")
        if not self.series:
            errors.append("batch is empty")
        for sym, s in self.series.items():
            series_errors = s.validate()
            for err in series_errors:
                errors.append(f"{sym}: {err}")
        return errors

    def to_dict(self) -> dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "loaded_at": self.loaded_at,
            "is_fixture": self.is_fixture,
            "is_live": self.is_live,
            "source": self.source,
            "symbols": self.symbols,
            "total_candles": self.total_candles,
            "series": {sym: s.to_dicts() for sym, s in self.series.items()},
        }


@dataclass
class DataFeedMetadata:
    """Metadata about a data feed source."""
    feed_id: str
    feed_type: str  # fixture | mock | live
    is_fixture: bool = True
    is_live: bool = False
    source: str = "fixture"
    symbols: list[str] = field(default_factory=list)
    timeframe: str = "15m"
    created_at: str = field(default_factory=_utc_now_iso)
    candle_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "feed_id": self.feed_id,
            "feed_type": self.feed_type,
            "is_fixture": self.is_fixture,
            "is_live": self.is_live,
            "source": self.source,
            "symbols": self.symbols,
            "timeframe": self.timeframe,
            "created_at": self.created_at,
            "candle_count": self.candle_count,
        }
