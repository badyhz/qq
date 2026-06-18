"""Readonly data source abstraction — no network, no account, no orders."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


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
