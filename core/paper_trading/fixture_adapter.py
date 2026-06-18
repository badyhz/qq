"""Fixture data source adapter — wraps existing fixture JSON, no network."""
from __future__ import annotations

import json
import os
from typing import List, Optional

from core.paper_trading.data_source import (
    DataSource, DataSourceConfig, MarketBar, MarketSnapshot,
)


class FixtureDataSource(DataSource):
    """Readonly data source from local JSON fixtures.

    No network, no secret, no order, no account.
    """

    def __init__(self, config: DataSourceConfig):
        self._config = config
        self._fixture_path = config.fixture_path

    def get_bars(self, symbol: str, timeframe: str = "1h", limit: int = 100) -> List[MarketBar]:
        """Load bars from fixture JSON file."""
        if not self._fixture_path or not os.path.isfile(self._fixture_path):
            return []

        with open(self._fixture_path) as f:
            data = json.load(f)

        bars_raw = data if isinstance(data, list) else data.get("bars", data.get("klines", []))
        bars: List[MarketBar] = []
        for i, bar in enumerate(bars_raw):
            if i >= limit:
                break
            try:
                bars.append(MarketBar(
                    timestamp=float(bar.get("timestamp", bar.get("t", i))),
                    open=float(bar.get("open", bar.get("o", 0))),
                    high=float(bar.get("high", bar.get("h", 0))),
                    low=float(bar.get("low", bar.get("l", 0))),
                    close=float(bar.get("close", bar.get("c", 0))),
                    volume=float(bar.get("volume", bar.get("v", 0))),
                    symbol=symbol,
                    timeframe=timeframe,
                ))
            except (ValueError, TypeError, KeyError):
                continue
        return bars

    def get_snapshot(self, symbol: str) -> Optional[MarketSnapshot]:
        """Return last bar as snapshot, or None if no data."""
        bars = self.get_bars(symbol, limit=10000)
        if not bars:
            return None
        bar = bars[-1]
        return MarketSnapshot(
            symbol=bar.symbol,
            price=bar.close,
            timestamp=bar.timestamp,
            source="fixture",
        )

    def is_available(self) -> bool:
        """Check if fixture file exists."""
        return self._fixture_path is not None and os.path.isfile(self._fixture_path)

    @property
    def source_name(self) -> str:
        return "fixture"
