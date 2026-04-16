import math
import re
import threading
import time
from datetime import datetime, timezone
from typing import Optional

import ccxt


class TickerScanner:
    def __init__(self, config: dict, logger):
        self.config = config
        self.logger = logger
        radar_cfg = config.get("radar", {})
        self.max_hot_symbols = int(radar_cfg.get("max_hot_symbols", 10))
        self.min_24h_volume = float(radar_cfg.get("min_24h_volume", 10_000_000))
        self.update_interval = int(radar_cfg.get("update_interval", 60))
        self.price_weight = float(radar_cfg.get("price_weight", 0.6))
        self.funding_weight = float(radar_cfg.get("funding_weight", 0.4))
        self.min_score = float(radar_cfg.get("min_score", 30.0))
        self.quote_asset = str(radar_cfg.get("quote_asset", "USDT")).upper()
        self.exclude_symbols = {
            str(symbol).strip().upper()
            for symbol in radar_cfg.get("exclude_symbols", [])
            if str(symbol).strip()
        }
        self.always_include_symbols = [
            str(symbol).strip().upper()
            for symbol in radar_cfg.get("always_include_symbols", [])
            if str(symbol).strip()
        ]
        self.fallback_symbols = [
            str(symbol).strip().upper()
            for symbol in radar_cfg.get("fallback_symbols", self.always_include_symbols)
            if str(symbol).strip()
        ]

        self.exchange = self._create_exchange()
        self.hot_symbols = []
        self.snapshot = {}
        self.last_scan_at = None
        self._lock = threading.Lock()

    def _create_exchange(self):
        return ccxt.binanceusdm(
            {
                "enableRateLimit": True,
                "timeout": 15000,
                "options": {"defaultType": "future"},
            }
        )

    def should_scan(self) -> bool:
        if self.last_scan_at is None:
            return True
        return (time.time() - self.last_scan_at) >= self.update_interval

    def scan(self, force: bool = False) -> list:
        if not force and not self.should_scan():
            return list(self.hot_symbols)

        started_at = time.time()
        try:
            tickers = self.exchange.fetch_tickers()
            funding_rates = self.exchange.fetch_funding_rates()
        except Exception as exc:
            self.last_scan_at = time.time()
            self.logger.error("RADAR scan failed | error=%s", exc)
            fallback = list(self.hot_symbols) or list(self.fallback_symbols)
            if fallback:
                self.logger.warning(
                    "RADAR fallback activated | symbols=%s",
                    ",".join(fallback),
                )
            return fallback
        ranked = []

        for symbol, ticker in tickers.items():
            if not self._is_target_symbol(symbol):
                continue

            plain_symbol = self._to_plain_symbol(symbol)
            if not self._is_supported_plain_symbol(plain_symbol):
                continue
            if plain_symbol in self.exclude_symbols:
                continue

            volume_usdt = self._extract_quote_volume(ticker)
            if volume_usdt < self.min_24h_volume:
                continue

            funding_info = funding_rates.get(symbol, {})
            funding_rate = funding_info.get("fundingRate")
            if funding_rate is None:
                funding_rate = 0.0

            price_change_pct = self._extract_price_change_pct(ticker)
            score = self.calculate_sniper_score(
                price_change_pct=price_change_pct,
                funding_rate=float(funding_rate),
                volume_usdt=volume_usdt,
            )

            if score < self.min_score:
                continue

            ranked.append(
                {
                    "symbol": plain_symbol,
                    "ccxt_symbol": symbol,
                    "score": score,
                    "price_change_pct": price_change_pct,
                    "funding_rate": float(funding_rate),
                    "volume_usdt": volume_usdt,
                    "last_price": self._safe_float(ticker.get("last") or ticker.get("close")),
                }
            )

        ranked.sort(key=lambda item: item["score"], reverse=True)
        hot_entries = ranked[: self.max_hot_symbols]
        selected_symbols = {item["symbol"] for item in hot_entries}

        for priority_symbol in self.always_include_symbols:
            if priority_symbol in selected_symbols:
                continue
            fallback_entry = self._build_priority_entry(priority_symbol, tickers, funding_rates)
            if not fallback_entry:
                continue
            hot_entries.append(fallback_entry)
            selected_symbols.add(priority_symbol)

        if not hot_entries:
            hot_entries = [
                entry
                for symbol in self.fallback_symbols
                for entry in [self._build_priority_entry(symbol, tickers, funding_rates)]
                if entry
            ]

        with self._lock:
            self.hot_symbols = [item["symbol"] for item in hot_entries]
            self.snapshot = {
                item["symbol"]: {
                    "score": item["score"],
                    "price_change_pct": item["price_change_pct"],
                    "funding_rate": item["funding_rate"],
                    "volume_usdt": item["volume_usdt"],
                    "last_price": item["last_price"],
                    "ccxt_symbol": item["ccxt_symbol"],
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
                for item in hot_entries
            }
            self.last_scan_at = time.time()

        duration = time.time() - started_at
        self.logger.info(
            "RADAR scan complete | candidates=%s | hot_symbols=%s | duration=%.3fs",
            len(ranked),
            ",".join(self.hot_symbols) if self.hot_symbols else "NONE",
            duration,
        )
        return list(self.hot_symbols)

    def get_hot_symbols(self) -> list:
        with self._lock:
            return list(self.hot_symbols)

    def get_snapshot(self) -> dict:
        with self._lock:
            return dict(self.snapshot)

    def calculate_sniper_score(self, price_change_pct: float, funding_rate: float, volume_usdt: float) -> float:
        if volume_usdt < self.min_24h_volume:
            return 0.0

        momentum_factor = abs(price_change_pct) * 100.0
        funding_factor = abs(funding_rate) / 0.0001
        volume_multiplier = math.log10(max(volume_usdt, 1.0))
        score = ((self.price_weight * momentum_factor) + (self.funding_weight * funding_factor)) * volume_multiplier
        return round(score, 2)

    def _build_priority_entry(self, plain_symbol: str, tickers: dict, funding_rates: dict) -> Optional[dict]:
        if not self._is_supported_plain_symbol(plain_symbol):
            return None
        ccxt_symbol = f"{plain_symbol[:-len(self.quote_asset)]}/{self.quote_asset}:{self.quote_asset}"
        ticker = tickers.get(ccxt_symbol)
        if not ticker:
            return None
        funding_info = funding_rates.get(ccxt_symbol, {})
        funding_rate = self._safe_float(funding_info.get("fundingRate"))
        volume_usdt = self._extract_quote_volume(ticker)
        price_change_pct = self._extract_price_change_pct(ticker)
        return {
            "symbol": plain_symbol,
            "ccxt_symbol": ccxt_symbol,
            "score": self.calculate_sniper_score(
                price_change_pct=price_change_pct,
                funding_rate=funding_rate,
                volume_usdt=volume_usdt,
            ),
            "price_change_pct": price_change_pct,
            "funding_rate": funding_rate,
            "volume_usdt": volume_usdt,
            "last_price": self._safe_float(ticker.get("last") or ticker.get("close")),
        }

    def _is_target_symbol(self, symbol: str) -> bool:
        normalized = str(symbol).upper()
        return normalized.endswith(f"/{self.quote_asset}:{self.quote_asset}")

    def _extract_quote_volume(self, ticker: dict) -> float:
        direct = self._safe_float(ticker.get("quoteVolume"))
        if direct > 0:
            return direct
        base_volume = self._safe_float(ticker.get("baseVolume"))
        last_price = self._safe_float(ticker.get("last") or ticker.get("close"))
        return base_volume * last_price

    def _extract_price_change_pct(self, ticker: dict) -> float:
        percent = ticker.get("percentage")
        if percent is None:
            info_percent = ticker.get("info", {}).get("priceChangePercent")
            percent = info_percent if info_percent is not None else 0.0
        percent_value = self._safe_float(percent)
        return percent_value / 100.0

    def _to_plain_symbol(self, ccxt_symbol: str) -> str:
        return str(ccxt_symbol).split(":")[0].replace("/", "").upper()

    def _is_supported_plain_symbol(self, plain_symbol: str) -> bool:
        if not plain_symbol.endswith(self.quote_asset):
            return False
        return bool(re.fullmatch(r"[A-Z0-9]+", plain_symbol))

    def _safe_float(self, value) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0
