"""Public readonly market data adapter — Binance USDS-M klines only. No secret, no orders."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import List, Optional
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import urlencode

from core.paper_trading.data_source import (
    DataSource, DataSourceConfig, MarketBar, MarketSnapshot,
    utc_datetime_from_epoch_ms,
)

DEFAULT_BASE_URL = "https://fapi.binance.com"
DEFAULT_TIMEOUT = 10
DEFAULT_LIMIT = 100
VALID_INTERVALS = {"1m", "3m", "5m", "15m", "30m", "1h", "4h", "1d"}
MAX_LIMIT = 1500


def _validate_symbol(symbol: str) -> bool:
    """Validate symbol format: uppercase letters/digits, ending with USDT."""
    if not symbol or not symbol.endswith("USDT"):
        return False
    base = symbol[:-4]
    if not base:
        return False
    return all(c.isdigit() or (c.isalpha() and c.isupper()) for c in base)


def _validate_interval(interval: str) -> bool:
    """Validate interval is in whitelist."""
    return interval in VALID_INTERVALS


def _parse_kline(raw: list, symbol: str = "", timeframe: str = "") -> Optional[MarketBar]:
    """Parse a single Binance kline array into MarketBar.

    Format: [open_time, open, high, low, close, volume, close_time, ...]
    """
    try:
        if len(raw) < 7:
            return None
        return MarketBar(
            timestamp=float(raw[0]) / 1000.0,  # Convert ms to seconds
            open=float(raw[1]),
            high=float(raw[2]),
            low=float(raw[3]),
            close=float(raw[4]),
            volume=float(raw[5]),
            symbol=symbol,
            timeframe=timeframe,
            close_time=utc_datetime_from_epoch_ms(raw[6]),
        )
    except (ValueError, TypeError, IndexError):
        return None


class BinancePublicKlineAdapter(DataSource):
    """Readonly adapter for Binance USDS-M public klines.

    Only accesses: GET /fapi/v1/klines
    No secret, no account, no order, no websocket.
    """

    def __init__(self, config: DataSourceConfig, base_url: str = DEFAULT_BASE_URL,
                 timeout: int = DEFAULT_TIMEOUT):
        self._config = config
        self._base_url = base_url
        self._timeout = timeout
        self._network_enabled = config.network_enabled

    def get_bars(self, symbol: str, timeframe: str = "1h", limit: int = 100) -> List[MarketBar]:
        """Fetch klines from Binance public API."""
        if not self._network_enabled:
            return []

        if not _validate_symbol(symbol):
            return []

        if not _validate_interval(timeframe):
            return []

        limit = min(limit, MAX_LIMIT)

        params = urlencode({
            "symbol": symbol,
            "interval": timeframe,
            "limit": limit,
        })
        url = f"{self._base_url}/fapi/v1/klines?{params}"

        try:
            req = Request(url, method="GET")
            with urlopen(req, timeout=self._timeout) as resp:
                data = json.loads(resp.read().decode())
        except (URLError, HTTPError, json.JSONDecodeError, OSError):
            return []

        if not isinstance(data, list):
            return []

        bars: List[MarketBar] = []
        for raw in data:
            bar = _parse_kline(raw, symbol=symbol, timeframe=timeframe)
            if bar:
                bars.append(bar)
        return bars

    def get_snapshot(self, symbol: str) -> Optional[MarketSnapshot]:
        """Get latest price from klines."""
        bars = self.get_bars(symbol, limit=1)
        if not bars:
            return None
        bar = bars[-1]
        return MarketSnapshot(
            symbol=symbol,
            price=bar.close,
            timestamp=bar.timestamp,
            source="binance_public",
        )

    def _get_public_json(self, endpoint: str, params: dict) -> object:
        """GET one allowlisted unauthenticated USD-M public endpoint."""
        if not self._network_enabled or endpoint not in {
            "/fapi/v1/ticker/bookTicker", "/fapi/v1/depth", "/fapi/v1/fundingRate",
        }:
            raise ValueError("public evidence endpoint is disabled or unsupported")
        url = f"{self._base_url}{endpoint}?{urlencode(params)}"
        try:
            with urlopen(Request(url, method="GET"), timeout=self._timeout) as resp:
                return json.loads(resp.read().decode())
        except (URLError, HTTPError, json.JSONDecodeError, OSError) as exc:
            raise ValueError("public evidence source error") from exc

    @staticmethod
    def _event_at(epoch_ms: object) -> str:
        return datetime.fromtimestamp(float(epoch_ms) / 1000, timezone.utc).isoformat(timespec="milliseconds")

    def get_top_of_book(self, symbol: str) -> dict:
        if not _validate_symbol(symbol):
            raise ValueError("invalid symbol")
        raw = self._get_public_json("/fapi/v1/ticker/bookTicker", {"symbol": symbol})
        if not isinstance(raw, dict):
            raise ValueError("malformed top-of-book response")
        return {
            "symbol": raw.get("symbol"),
            "best_bid_price": raw.get("bidPrice"),
            "best_bid_quantity": raw.get("bidQty"),
            "best_ask_price": raw.get("askPrice"),
            "best_ask_quantity": raw.get("askQty"),
            "exchange_event_at": self._event_at(raw.get("time")),
            "source": "binance_usdm_public",
        }

    def get_depth(self, symbol: str, limit: int = 20) -> dict:
        if not _validate_symbol(symbol) or limit <= 0 or limit > 1000:
            raise ValueError("invalid depth request")
        raw = self._get_public_json("/fapi/v1/depth", {"symbol": symbol, "limit": limit})
        if not isinstance(raw, dict):
            raise ValueError("malformed depth response")
        return {
            "symbol": symbol,
            "bids": raw.get("bids"),
            "asks": raw.get("asks"),
            "exchange_event_at": self._event_at(raw.get("E") or raw.get("T")),
            "source": "binance_usdm_public",
        }

    def get_funding_events(self, symbol: str, lookback_seconds: int) -> list[dict]:
        if not _validate_symbol(symbol) or lookback_seconds <= 0:
            raise ValueError("invalid funding request")
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        raw = self._get_public_json("/fapi/v1/fundingRate", {
            "symbol": symbol,
            "startTime": now_ms - lookback_seconds * 1000,
            "endTime": now_ms,
            "limit": 1000,
        })
        if not isinstance(raw, list):
            raise ValueError("malformed funding response")
        ordered = sorted((item for item in raw if isinstance(item, dict)), key=lambda item: int(item.get("fundingTime", 0)))
        times = [int(item.get("fundingTime", 0)) for item in ordered]
        intervals = [later - earlier for earlier, later in zip(times, times[1:]) if later > earlier]
        interval_seconds = min(intervals) // 1000 if intervals else 0
        return [{
            "symbol": item.get("symbol"),
            "funding_event_at": self._event_at(item.get("fundingTime")),
            "signed_funding_rate": item.get("fundingRate"),
            "mark_price": item.get("markPrice"),
            "funding_interval_seconds": interval_seconds,
            "source": "binance_usdm_public",
            "source_event_identity": f"{item.get('symbol')}:{item.get('fundingTime')}",
        } for item in ordered]

    def is_available(self) -> bool:
        """Check if adapter is configured."""
        return True

    @property
    def source_name(self) -> str:
        return "binance_public"

    @property
    def network_enabled(self) -> bool:
        return self._network_enabled
