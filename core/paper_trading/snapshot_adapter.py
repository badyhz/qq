"""Snapshot data source adapter — skeleton only, no network, no real HTTP."""
from __future__ import annotations

from typing import List, Optional

from core.paper_trading.data_source import (
    DataSource, DataSourceConfig, MarketBar, MarketSnapshot,
)


class SnapshotAdapter(DataSource):
    """Skeleton readonly snapshot adapter.

    Does NOT connect to any external service.
    Does NOT import requests/httpx/aiohttp/websocket.
    Does NOT read secrets or API keys.
    Returns local sample data only.
    """

    def __init__(self, config: DataSourceConfig):
        self._config = config
        self._network_enabled = False  # Always disabled

    def get_bars(self, symbol: str, timeframe: str = "1h", limit: int = 100) -> List[MarketBar]:
        """Return empty bars — skeleton only, no real data."""
        return []

    def get_snapshot(self, symbol: str) -> Optional[MarketSnapshot]:
        """Return sample snapshot — skeleton only, no real data."""
        return MarketSnapshot(
            symbol=symbol,
            price=0.0,
            timestamp=0.0,
            source="skeleton",
        )

    def is_available(self) -> bool:
        """Skeleton is always available but returns no real data."""
        return True

    @property
    def source_name(self) -> str:
        return "snapshot"

    @property
    def network_enabled(self) -> bool:
        """Network is always disabled."""
        return self._network_enabled
