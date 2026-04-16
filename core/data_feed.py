import json
import math
import random
import threading
import time
import traceback
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.request import urlopen


class DataFeed:
    def __init__(self, config: dict, logger):
        self.config = config
        self.logger = logger
        self.symbols = self._extract_symbols(config)
        self.primary_symbol = self.symbols[0] if self.symbols else None
        self.timeframe = str(config.get("timeframe", "5m"))
        self.data_mode = str(config.get("data_mode", "mock")).lower()
        self.warmup_candles = int(config.get("data", {}).get("warmup_candles", 160))
        self.websocket_reconnect_seconds = int(config.get("data", {}).get("websocket_reconnect_seconds", 5))
        self.websocket_stale_seconds = int(config.get("data", {}).get("websocket_stale_seconds", 75))

        self._lock = threading.Lock()
        self._event_queue = deque()
        self._latest_by_symbol = {}
        self._ws_started = False
        self._ws_watchdog_started = False
        self._ws_connected = False
        self._ws_app = None
        self._ws_message_id = 0
        self._ws_last_message_at = 0.0
        self._mock_symbol_index = 0
        self._mock_state = {}
        self._initialize_mock_state(self.symbols)

        if self.data_mode == "websocket" and self.symbols:
            self._start_websocket()
        elif self.data_mode == "websocket":
            self.logger.info("data feed websocket deferred until symbols are activated")
        else:
            self.logger.info("data feed running in mock mode | symbols=%s", ",".join(self.symbols))

    def bootstrap_candles(self) -> dict:
        return self._bootstrap_symbol_set(self.symbols)

    def bootstrap_symbols(self, target_symbols) -> dict:
        return self._bootstrap_symbol_set(target_symbols)

    def update_subscriptions(self, target_symbols: set) -> dict:
        normalized_targets = self._normalize_symbols(target_symbols)
        current_symbols = set(self.symbols)
        added_symbols = sorted(set(normalized_targets) - current_symbols)
        removed_symbols = sorted(current_symbols - set(normalized_targets))

        self._initialize_mock_state(added_symbols)
        bootstrap_candles = self._bootstrap_symbol_set(added_symbols)

        with self._lock:
            self.symbols = list(normalized_targets)
            self.primary_symbol = self.symbols[0] if self.symbols else None
            if removed_symbols:
                self._event_queue = deque(
                    candle for candle in self._event_queue if candle.get("symbol") not in removed_symbols
                )
                for symbol in removed_symbols:
                    self._latest_by_symbol.pop(symbol, None)

        if self.data_mode == "websocket":
            if added_symbols and not self._ws_started:
                self._start_websocket()
            if added_symbols:
                self._send_ws_command("SUBSCRIBE", self._build_stream_params(added_symbols))
            if removed_symbols:
                self._send_ws_command("UNSUBSCRIBE", self._build_stream_params(removed_symbols))

        self.logger.info(
            "Data feed subscriptions updated | active=%s | added=%s | removed=%s",
            ",".join(self.symbols) if self.symbols else "NONE",
            ",".join(added_symbols) if added_symbols else "NONE",
            ",".join(removed_symbols) if removed_symbols else "NONE",
        )
        return bootstrap_candles

    def get_active_symbols(self) -> list:
        with self._lock:
            return list(self.symbols)

    def _bootstrap_symbol_set(self, target_symbols) -> dict:
        symbols = self._normalize_symbols(target_symbols)
        start_time = time.time()
        if not symbols:
            return {}

        if self.data_mode == "mock":
            candles_by_symbol = {}
            for symbol in symbols:
                candles_by_symbol[symbol] = [
                    self._generate_mock_candle(symbol, enqueue=False) for _ in range(self.warmup_candles)
                ]
            duration = time.time() - start_time
            self.logger.info(
                "mock warmup generated | symbols=%s | candles_per_symbol=%s | duration=%.3fs",
                len(symbols),
                self.warmup_candles,
                duration,
            )
            return candles_by_symbol

        max_workers = max(1, min(len(symbols), 8))
        candles_by_symbol = {symbol: [] for symbol in symbols}
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_map = {
                executor.submit(self._fetch_rest_klines, symbol, self.warmup_candles): symbol
                for symbol in symbols
            }
            for future in as_completed(future_map):
                symbol = future_map[future]
                try:
                    candles_by_symbol[symbol] = future.result()
                except Exception as exc:
                    self.logger.error("warmup failed | symbol=%s | error=%s", symbol, exc)
                    candles_by_symbol[symbol] = []

        duration = time.time() - start_time
        self.logger.info(
            "rest warmup loaded | symbols=%s | duration=%.3fs | counts=%s",
            len(symbols),
            duration,
            {symbol: len(candles_by_symbol.get(symbol, [])) for symbol in symbols},
        )
        return candles_by_symbol

    def get_latest(self) -> Optional[dict]:
        if self.data_mode == "mock":
            with self._lock:
                active_symbols = list(self.symbols)
            if active_symbols and not self._event_queue:
                symbol = active_symbols[self._mock_symbol_index % len(active_symbols)]
                self._mock_symbol_index = (self._mock_symbol_index + 1) % len(active_symbols)
                self._generate_mock_candle(symbol, enqueue=True)

        with self._lock:
            while self._event_queue:
                candle = self._event_queue.popleft()
                if candle.get("symbol") in self.symbols:
                    return candle
        return None

    def _extract_symbols(self, config: dict) -> list:
        raw_symbols = config.get("symbols")
        if not raw_symbols:
            if config.get("radar", {}).get("enabled", False):
                raw_symbols = []
            else:
                raw_symbols = [config.get("symbol", "BTCUSDT")]
        return self._normalize_symbols(raw_symbols)

    def _normalize_symbols(self, raw_symbols) -> list:
        symbols = []
        seen = set()
        for symbol in raw_symbols or []:
            cleaned = str(symbol).strip().upper()
            if not cleaned or cleaned in seen:
                continue
            symbols.append(cleaned)
            seen.add(cleaned)
        return symbols

    def _initialize_mock_state(self, symbols) -> None:
        base_prices = {
            "BTCUSDT": 30000.0,
            "ETHUSDT": 1800.0,
            "SOLUSDT": 140.0,
            "DOGEUSDT": 0.18,
        }
        existing_count = len(self._mock_state)
        for index, symbol in enumerate(symbols):
            if symbol in self._mock_state:
                continue
            base_price = base_prices.get(symbol, max(1.0, 100.0 + (existing_count + index) * 25.0))
            self._mock_state[symbol] = {
                "price": base_price,
                "volume": 100.0,
                "step": existing_count + index,
                "shock": 0.0,
                "timestamp": datetime.now(timezone.utc) - timedelta(minutes=self._timeframe_minutes()),
            }

    def _timeframe_minutes(self) -> int:
        mapping = {"1m": 1, "3m": 3, "5m": 5, "15m": 15, "30m": 30, "1h": 60}
        return mapping.get(self.timeframe, 5)

    def _generate_mock_candle(self, symbol: str, enqueue: bool) -> dict:
        state = self._mock_state[symbol]
        state["step"] += 1
        if abs(state["shock"]) < 5 and random.random() < 0.10:
            state["shock"] += random.choice([1.0, -1.0]) * random.uniform(120.0, 240.0)

        scale = max(state["price"] * 0.001, 0.02)
        drift = math.sin(state["step"] / 6.0) * scale * 0.3
        noise = random.gauss(0.0, scale * 0.6)
        impulse = state["shock"] * 0.22
        state["shock"] *= 0.80

        open_price = state["price"]
        close_price = max(0.0001, open_price + drift + noise + impulse)
        candle_range = max(abs(close_price - open_price), scale)
        high = max(open_price, close_price) + random.uniform(scale * 0.1, candle_range * 0.8)
        low = max(0.0001, min(open_price, close_price) - random.uniform(scale * 0.1, candle_range * 0.8))
        volume = abs(close_price - open_price) * random.uniform(10.0, 30.0) + random.uniform(50.0, 180.0)

        state["price"] = close_price
        state["volume"] = volume
        state["timestamp"] += timedelta(minutes=self._timeframe_minutes())

        candle = self._build_candle(
            symbol=symbol,
            timestamp=state["timestamp"],
            open_price=open_price,
            high=high,
            low=low,
            close=close_price,
            volume=volume,
            closed=True,
        )
        self._latest_by_symbol[symbol] = candle
        if enqueue:
            with self._lock:
                self._event_queue.append(candle)
        return candle

    def _fetch_rest_klines(self, symbol: str, limit: int) -> list:
        base_url = self.config.get("binance", {}).get("futures_base_url", "https://fapi.binance.com")
        url = f"{base_url}/fapi/v1/klines?symbol={symbol}&interval={self.timeframe}&limit={limit}"
        fetch_start = time.time()
        try:
            with urlopen(url, timeout=10) as response:
                payload = json.loads(response.read().decode("utf-8"))

            candles = []
            for item in payload:
                open_time = datetime.fromtimestamp(item[0] / 1000, tz=timezone.utc)
                candles.append(
                    self._build_candle(
                        symbol=symbol,
                        timestamp=open_time,
                        open_price=float(item[1]),
                        high=float(item[2]),
                        low=float(item[3]),
                        close=float(item[4]),
                        volume=float(item[5]),
                        closed=True,
                    )
                )
            if candles:
                self._latest_by_symbol[symbol] = candles[-1]
            self.logger.info(
                "REST klines fetched successfully | symbol=%s | count=%s | fetch_time=%.3fs",
                symbol,
                len(candles),
                time.time() - fetch_start,
            )
            return candles
        except Exception as exc:
            self.logger.error(
                "Failed to fetch REST klines | symbol=%s | error=%s | duration=%.3fs | falling back to mock warmup",
                symbol,
                str(exc),
                time.time() - fetch_start,
            )
            return [self._generate_mock_candle(symbol, enqueue=False) for _ in range(limit)]

    def _start_websocket(self) -> None:
        if self._ws_started:
            return
        self._ws_started = True
        self._start_websocket_watchdog()

        url = "wss://fstream.binance.com/ws"
        self.logger.info(
            "Starting websocket connection | symbols=%s | timeframe=%s",
            ",".join(self.symbols) if self.symbols else "NONE",
            self.timeframe,
        )

        def runner() -> None:
            import websocket

            reconnect_attempts = 0
            while True:
                ws_start_time = time.time()
                try:
                    self.logger.debug(
                        "Creating websocket connection | url=%s | attempt=%s",
                        url,
                        reconnect_attempts + 1,
                    )
                    ws = websocket.WebSocketApp(
                        url,
                        on_message=self._on_message,
                        on_error=self._on_error,
                        on_close=self._on_close,
                        on_open=self._on_open,
                    )
                    self._ws_app = ws
                    ws.run_forever()
                except Exception as exc:
                    reconnect_attempts += 1
                    self.logger.error(
                        "WEBSOCKET ERROR | attempt=%s | error=%s | duration=%.3fs | reconnecting in %ds",
                        reconnect_attempts,
                        str(exc),
                        time.time() - ws_start_time,
                        self.websocket_reconnect_seconds,
                    )
                    self.logger.debug("Websocket stack trace:\n%s", traceback.format_exc())
                else:
                    reconnect_attempts += 1
                    self.logger.warning(
                        "WEBSOCKET DISCONNECTED | attempt=%s | reconnecting in %ds",
                        reconnect_attempts,
                        self.websocket_reconnect_seconds,
                    )
                time.sleep(self.websocket_reconnect_seconds)

        thread = threading.Thread(target=runner, name="qq-websocket", daemon=True)
        thread.start()

    def _start_websocket_watchdog(self) -> None:
        if self._ws_watchdog_started:
            return
        self._ws_watchdog_started = True

        def watchdog() -> None:
            while True:
                time.sleep(5)
                if not self._ws_connected or not self._ws_app:
                    continue
                if self._ws_last_message_at <= 0:
                    continue
                age = time.time() - self._ws_last_message_at
                if age < self.websocket_stale_seconds:
                    continue
                self.logger.warning(
                    "WEBSOCKET STALE | last_message_age=%.1fs | threshold=%ss | forcing reconnect",
                    age,
                    self.websocket_stale_seconds,
                )
                try:
                    self._ws_app.close()
                except Exception as exc:
                    self.logger.error("Failed to close stale websocket cleanly | error=%s", exc)

        thread = threading.Thread(target=watchdog, name="qq-websocket-watchdog", daemon=True)
        thread.start()

    def _build_stream_params(self, symbols) -> list:
        return [f"{symbol.lower()}@kline_{self.timeframe}" for symbol in symbols]

    def _send_ws_command(self, method: str, params: list) -> bool:
        if not params:
            return False
        if not self._ws_connected or not self._ws_app:
            self.logger.debug("Websocket not ready for %s | params=%s", method, params)
            return False
        try:
            self._ws_message_id += 1
            payload = {"method": method, "params": params, "id": self._ws_message_id}
            self._ws_app.send(json.dumps(payload))
            self.logger.info("WEBSOCKET %s | params=%s", method, ",".join(params))
            return True
        except Exception as exc:
            self.logger.error("Failed to send websocket command | method=%s | error=%s", method, exc)
            return False

    def _on_message(self, _ws, message: str) -> None:
        try:
            self._ws_last_message_at = time.time()
            payload = json.loads(message)
            if "result" in payload and "id" in payload:
                self.logger.debug("Websocket command ack | id=%s | result=%s", payload["id"], payload["result"])
                return

            event = payload.get("data", payload)
            if "k" not in event:
                return
            kline = event["k"]
            symbol = event.get("s") or payload.get("stream", "").split("@")[0].upper()
            with self._lock:
                if symbol not in self.symbols:
                    return
            candle = self._build_candle(
                symbol=symbol,
                timestamp=datetime.fromtimestamp(int(kline["t"]) / 1000, tz=timezone.utc),
                open_price=float(kline["o"]),
                high=float(kline["h"]),
                low=float(kline["l"]),
                close=float(kline["c"]),
                volume=float(kline["v"]),
                closed=bool(kline["x"]),
            )
            with self._lock:
                self._latest_by_symbol[symbol] = candle
                self._event_queue.append(candle)
            if candle["closed"]:
                self.logger.info(
                    "WEBSOCKET CANDLE CLOSED | symbol=%s | close=%.4f | volume=%.2f | time=%s",
                    symbol,
                    candle["close"],
                    candle["volume"],
                    candle["timestamp"],
                )
        except Exception as exc:
            self.logger.error("Failed to parse websocket message | error=%s: %s", type(exc).__name__, str(exc))
            self.logger.debug("Parse error stack trace:\n%s", traceback.format_exc())

    def _on_error(self, _ws, error) -> None:
        self.logger.error("WEBSOCKET ERROR EVENT | error=%s", str(error))

    def _on_close(self, _ws, status_code, message) -> None:
        self._ws_connected = False
        self._ws_app = None
        self._ws_last_message_at = 0.0
        self.logger.warning(
            "WEBSOCKET CLOSED | symbols=%s | timeframe=%s | status_code=%s | message=%s",
            ",".join(self.symbols) if self.symbols else "NONE",
            self.timeframe,
            status_code,
            message,
        )

    def _on_open(self, _ws) -> None:
        self._ws_connected = True
        self._ws_last_message_at = time.time()
        self.logger.info(
            "WEBSOCKET CONNECTED | symbols=%s | timeframe=%s | timestamp=%s",
            ",".join(self.symbols) if self.symbols else "NONE",
            self.timeframe,
            datetime.now(timezone.utc).isoformat(),
        )
        self._send_ws_command("SUBSCRIBE", self._build_stream_params(self.symbols))

    def _build_candle(
        self,
        symbol: str,
        timestamp: datetime,
        open_price: float,
        high: float,
        low: float,
        close: float,
        volume: float,
        closed: bool,
    ) -> dict:
        return {
            "symbol": symbol,
            "timestamp": timestamp,
            "open": float(open_price),
            "high": float(high),
            "low": float(low),
            "close": float(close),
            "price": float(close),
            "volume": float(volume),
            "closed": bool(closed),
        }
