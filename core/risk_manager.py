from datetime import datetime, timedelta, timezone


class RiskManager:
    def __init__(self, config: dict, logger):
        self.config = config
        self.logger = logger
        risk_cfg = config.get("risk", {})
        self.starting_balance = float(risk_cfg.get("starting_balance_usdt", config.get("balance", 1000.0)))
        self.balance = self.starting_balance
        self.risk_per_trade = float(risk_cfg.get("risk_per_trade", 0.02))
        self.max_daily_loss_pct = float(risk_cfg.get("max_daily_loss_pct", 0.06))
        self.max_consecutive_losses = int(risk_cfg.get("max_consecutive_losses", 3))
        self.cooldown_minutes = int(risk_cfg.get("cooldown_minutes", 20))
        self.min_notional = float(risk_cfg.get("min_notional_usdt", 25.0))
        self.max_notional = float(risk_cfg.get("max_notional_usdt", 250.0))
        self.leverage = int(risk_cfg.get("leverage", 1))

        self.daily_pnl = 0.0
        self._current_day = datetime.now(timezone.utc).date()
        self._symbol_state = {}

    def can_open_new_trade(self, symbol: str, timestamp: datetime) -> tuple:
        self._roll_day(timestamp)
        symbol_state = self._get_symbol_state(symbol)
        if symbol_state["cooldown_until"] and timestamp < symbol_state["cooldown_until"]:
            return False, "cooldown_active"
        if self.daily_pnl <= -(self.starting_balance * self.max_daily_loss_pct):
            return False, "daily_loss_limit"
        if symbol_state["consecutive_losses"] >= self.max_consecutive_losses:
            return False, "consecutive_loss_limit"
        if self.balance <= 0:
            return False, "balance_depleted"
        return True, "ok"

    def calculate_position(self, signal: dict, symbol: str = "", open_positions: int = 0) -> dict:
        entry = float(signal["entry"])
        stop = float(signal["stop"])
        take_profit = float(signal["tp"])
        risk_distance = abs(stop - entry)
        reward_distance = abs(entry - take_profit)
        if risk_distance <= 0:
            return {
                "quantity": 0.0,
                "entry_price": entry,
                "stop_price": stop,
                "take_profit_price": take_profit,
                "risk_amount": 0.0,
                "estimated_loss_at_stop": 0.0,
                "estimated_gain_at_target": 0.0,
                "reward_risk_ratio": 0.0,
                "notional": 0.0,
                "symbol": symbol,
            }

        slot_divisor = max(1, open_positions + 1)
        risk_amount = (self.balance * self.risk_per_trade) / slot_divisor
        raw_quantity = risk_amount / risk_distance
        notional = raw_quantity * entry

        if notional < self.min_notional:
            raw_quantity = self.min_notional / entry
            notional = raw_quantity * entry
        if notional > self.max_notional:
            raw_quantity = self.max_notional / entry
            notional = raw_quantity * entry

        quantity = max(raw_quantity, 0.0)
        estimated_loss_at_stop = quantity * risk_distance
        estimated_gain_at_target = quantity * reward_distance
        reward_risk_ratio = (reward_distance / risk_distance) if risk_distance > 0 else 0.0

        return {
            "quantity": quantity,
            "entry_price": entry,
            "stop_price": stop,
            "take_profit_price": take_profit,
            "risk_amount": risk_amount,
            "estimated_loss_at_stop": estimated_loss_at_stop,
            "estimated_gain_at_target": estimated_gain_at_target,
            "reward_risk_ratio": reward_risk_ratio,
            "notional": notional,
            "leverage": self.leverage,
            "symbol": symbol or signal.get("symbol"),
        }

    def on_trade_closed(self, trade: dict) -> None:
        exit_time = trade.get("exit_time")
        if not isinstance(exit_time, datetime):
            exit_time = datetime.now(timezone.utc)
        self._roll_day(exit_time)

        symbol = trade.get("symbol", "UNKNOWN")
        symbol_state = self._get_symbol_state(symbol)
        pnl = float(trade.get("pnl", 0.0))
        self.balance += pnl
        self.daily_pnl += pnl

        if pnl <= 0:
            symbol_state["consecutive_losses"] += 1
        else:
            symbol_state["consecutive_losses"] = 0

        if self.cooldown_minutes > 0:
            symbol_state["cooldown_until"] = exit_time + timedelta(minutes=self.cooldown_minutes)

        self.logger.info(
            "risk updated | symbol=%s | balance=%.4f | daily_pnl=%.4f | symbol_consecutive_losses=%s",
            symbol,
            self.balance,
            self.daily_pnl,
            symbol_state["consecutive_losses"],
        )

    def get_symbol_snapshot(self, symbol: str) -> dict:
        state = self._get_symbol_state(symbol)
        return {
            "consecutive_losses": state["consecutive_losses"],
            "cooldown_until": state["cooldown_until"],
        }

    def _get_symbol_state(self, symbol: str) -> dict:
        if symbol not in self._symbol_state:
            self._symbol_state[symbol] = {
                "consecutive_losses": 0,
                "cooldown_until": None,
            }
        return self._symbol_state[symbol]

    def _roll_day(self, timestamp: datetime) -> None:
        current_day = timestamp.astimezone(timezone.utc).date()
        if current_day != self._current_day:
            self._current_day = current_day
            self.daily_pnl = 0.0
            for state in self._symbol_state.values():
                state["consecutive_losses"] = 0
                state["cooldown_until"] = None
