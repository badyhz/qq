from decimal import Decimal, ROUND_DOWN
from typing import Optional


class ExchangeClient:
    def __init__(self, config: dict, logger):
        self.config = config
        self.logger = logger
        self.mode = config.get("mode", "dry-run")
        self.symbol = str(config.get("symbol", "BTCUSDT")).upper()
        self.leverage = int(config.get("risk", {}).get("leverage", 1))
        self.working_type = config.get("execution", {}).get("working_type", "MARK_PRICE")
        self.api_key = config.get("binance", {}).get("api_key", "")
        self.api_secret = config.get("binance", {}).get("api_secret", "")
        self.client = None
        self.filters = {}

        if self.mode == "live":
            self._connect()

    def is_enabled(self) -> bool:
        return self.mode == "live" and self.client is not None

    def _connect(self) -> None:
        if not self.api_key or not self.api_secret:
            raise ValueError("live mode requires Binance API key and secret")
        from binance.client import Client

        self.client = Client(self.api_key, self.api_secret)
        self.client.futures_change_leverage(symbol=self.symbol, leverage=self.leverage)
        self._load_filters()
        self.logger.info("exchange client ready | symbol=%s | leverage=%s", self.symbol, self.leverage)

    def ping(self) -> None:
        if self.client:
            self.client.futures_ping()

    def _load_filters(self) -> None:
        info = self.client.futures_exchange_info()
        for symbol_info in info["symbols"]:
            if symbol_info["symbol"] != self.symbol:
                continue
            for filt in symbol_info["filters"]:
                self.filters[filt["filterType"]] = filt
            return
        raise ValueError(f"symbol not found in exchange info: {self.symbol}")

    def _round_to_step(self, value: float, step: float) -> float:
        step_decimal = Decimal(str(step))
        value_decimal = Decimal(str(value))
        rounded = (value_decimal / step_decimal).quantize(Decimal("1"), rounding=ROUND_DOWN) * step_decimal
        return float(rounded)

    def round_quantity(self, quantity: float) -> float:
        lot = self.filters.get("LOT_SIZE", {})
        step = float(lot.get("stepSize", 0.001))
        minimum = float(lot.get("minQty", 0.001))
        rounded = self._round_to_step(quantity, step)
        if rounded < minimum:
            rounded = minimum
        return rounded

    def round_price(self, price: float) -> float:
        price_filter = self.filters.get("PRICE_FILTER", {})
        tick = float(price_filter.get("tickSize", 0.01))
        return self._round_to_step(price, tick)

    def fetch_position_snapshot(self) -> Optional[dict]:
        if not self.client:
            return None
        positions = self.client.futures_position_information(symbol=self.symbol)
        for position in positions:
            amount = float(position["positionAmt"])
            if amount == 0:
                continue
            side = "LONG" if amount > 0 else "SHORT"
            entry_price = float(position["entryPrice"])
            return {
                "symbol": self.symbol,
                "side": side,
                "quantity": abs(amount),
                "entry_price": entry_price,
                "notional": abs(amount) * entry_price,
            }
        return None

    def fetch_open_orders(self) -> list[dict]:
        if not self.client:
            return []
        return self.client.futures_get_open_orders(symbol=self.symbol)

    def fetch_protection_snapshot(self) -> dict:
        stop_price = None
        take_profit_price = None
        for order in self.fetch_open_orders():
            order_type = order.get("type")
            if order_type == "STOP_MARKET":
                stop_price = float(order.get("stopPrice", 0.0))
            elif order_type == "TAKE_PROFIT_MARKET":
                take_profit_price = float(order.get("stopPrice", 0.0))
        return {
            "stop_price": stop_price,
            "take_profit_price": take_profit_price,
        }

    def place_short_bracket(self, position_plan: dict, signal: dict) -> dict:
        if not self.client:
            return {"accepted": False, "reason": "exchange_not_ready"}

        quantity = self.round_quantity(position_plan["quantity"])
        stop_price = self.round_price(position_plan["stop_price"])
        take_profit_price = self.round_price(position_plan["take_profit_price"])

        market_order = self.client.futures_create_order(
            symbol=self.symbol,
            side="SELL",
            type="MARKET",
            quantity=quantity,
            newOrderRespType="RESULT",
        )
        entry_price = float(market_order.get("avgPrice") or position_plan["entry_price"])

        stop_order = self.client.futures_create_order(
            symbol=self.symbol,
            side="BUY",
            type="STOP_MARKET",
            stopPrice=stop_price,
            closePosition=True,
            workingType=self.working_type,
        )
        tp_order = self.client.futures_create_order(
            symbol=self.symbol,
            side="BUY",
            type="TAKE_PROFIT_MARKET",
            stopPrice=take_profit_price,
            closePosition=True,
            workingType=self.working_type,
        )

        return {
            "accepted": True,
            "mode": "live",
            "symbol": self.symbol,
            "entry_price": entry_price,
            "stop_price": stop_price,
            "take_profit_price": take_profit_price,
            "quantity": quantity,
            "notional": quantity * entry_price,
            "fees_paid": 0.0,
            "fee_rate": 0.0,
            "meta": {
                "market_order_id": market_order.get("orderId"),
                "stop_order_id": stop_order.get("orderId"),
                "tp_order_id": tp_order.get("orderId"),
                "signal_score": signal.get("score", 0),
            },
        }

    def ensure_protection_orders(self, position: dict) -> list[str]:
        if not self.client:
            return []

        existing_orders = self.fetch_open_orders()
        has_stop = any(order.get("type") == "STOP_MARKET" for order in existing_orders)
        has_tp = any(order.get("type") == "TAKE_PROFIT_MARKET" for order in existing_orders)
        actions = []

        if not has_stop:
            self.client.futures_create_order(
                symbol=self.symbol,
                side="BUY",
                type="STOP_MARKET",
                stopPrice=self.round_price(position["stop_price"]),
                closePosition=True,
                workingType=self.working_type,
            )
            actions.append("restored_stop")

        if not has_tp:
            self.client.futures_create_order(
                symbol=self.symbol,
                side="BUY",
                type="TAKE_PROFIT_MARKET",
                stopPrice=self.round_price(position["take_profit_price"]),
                closePosition=True,
                workingType=self.working_type,
            )
            actions.append("restored_take_profit")

        return actions
