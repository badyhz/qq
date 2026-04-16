from utils.indicators import atr, ema, rolling_mean, rolling_std, vwap


class SignalEngine:
    def __init__(self, config: dict, logger):
        self.config = config
        self.logger = logger
        strategy = config.get("strategy", {})
        self.strategy_profile = str(
            config.get("strategy_profile", strategy.get("profile_name", "default"))
        )
        self.lookback = int(strategy.get("lookback", 50))
        self.ema_period = int(strategy.get("ema_period", 21))
        self.vwap_window = int(strategy.get("vwap_window", 20))
        self.std_window = int(strategy.get("std_window", self.lookback))
        self.atr_period = int(strategy.get("atr_period", 14))
        self.armed_zscore = float(strategy.get("armed_zscore", 1.8))
        self.entry_zscore = float(strategy.get("entry_zscore", 2.2))
        self.min_score = int(strategy.get("min_score", 6))
        self.low_volatility_filter_pct = float(strategy.get("low_volatility_filter_pct", 0.0025))
        self.stop_atr_multiplier = float(strategy.get("stop_atr_multiplier", 1.2))
        self.take_profit_rr = float(strategy.get("take_profit_rr", 1.6))
        self.min_stop_pct = float(strategy.get("min_stop_pct", 0.01))
        self.max_stop_pct = float(strategy.get("max_stop_pct", 0.035))
        self.min_take_profit_rr = float(strategy.get("min_take_profit_rr", self.take_profit_rr))
        self.max_take_profit_rr = float(strategy.get("max_take_profit_rr", max(self.take_profit_rr, 2.2)))
        self.zscore_retrace_delta = float(strategy.get("zscore_retrace_delta", 0.35))
        self.cooldown_bars = int(strategy.get("cooldown_bars", 4))

        self.closes: list[float] = []
        self.highs: list[float] = []
        self.lows: list[float] = []
        self.volumes: list[float] = []
        self.timestamps: list = []

        self.state = "IDLE"
        self.cooldown_remaining = 0
        self.last_signal_ts = None
        self.armed_snapshot = None

    @property
    def candle_count(self) -> int:
        return len(self.closes)

    def seed_history(self, candles: list[dict]) -> None:
        for candle in candles:
            self._append_candle(candle)

    def on_position_opened(self) -> None:
        self.state = "IN_POSITION"
        self.armed_snapshot = None

    def on_trade_closed(self, _trade: dict) -> None:
        self.cooldown_remaining = self.cooldown_bars
        self.state = "COOLDOWN" if self.cooldown_bars > 0 else "IDLE"
        self.armed_snapshot = None

    def on_candle(self, candle: dict, has_position: bool) -> dict:
        self._append_candle(candle)
        if len(self.closes) < max(self.lookback, self.ema_period, self.vwap_window, self.atr_period + 1):
            return {"action": "NONE"}

        metrics = self._metrics()
        close = candle["close"]
        previous_close = self.closes[-2]

        if has_position:
            self.state = "IN_POSITION"
            self.armed_snapshot = None
            return {"action": "NONE", "state": self.state}

        if self.state == "IN_POSITION":
            self.state = "COOLDOWN" if self.cooldown_remaining > 0 else "IDLE"

        if self.cooldown_remaining > 0:
            self.cooldown_remaining -= 1
            if self.cooldown_remaining == 0:
                self.state = "IDLE"
            return {"action": "NONE", "state": self.state}

        # 修复：TRIGGERED 状态需要重置为 IDLE，否则无法再次触发信号
        if self.state == "TRIGGERED":
            self.state = "IDLE"

        if metrics["zscore"] >= self.armed_zscore and close > metrics["upper_band"]:
            if self.state != "ARMED":
                self.armed_snapshot = {
                    "zscore": metrics["zscore"],
                    "close": close,
                    "vwap": metrics["vwap"],
                    "std": metrics["std"],
                }
            self.state = "ARMED"
        elif self.state == "ARMED" and metrics["zscore"] < 0.5:
            self.state = "IDLE"
            self.armed_snapshot = None
            return {"action": "NONE", "state": self.state}

        if self.state != "ARMED":
            return {"action": "NONE", "state": self.state}

        score, reasons = self._score(metrics, close, previous_close)
        if score < self.min_score:
            return {"action": "NONE", "state": self.state, "score": score}

        armed_zscore = metrics["zscore"]
        if self.armed_snapshot:
            armed_zscore = max(armed_zscore, self.armed_snapshot["zscore"])

        zscore_retrace = max(0.0, armed_zscore - metrics["zscore"])
        retrace_confirmation = close < metrics["upper_band"] and zscore_retrace >= self.zscore_retrace_delta
        trend_confirmation = close < metrics["ema"]
        rollover_confirmation = close < previous_close

        if not (trend_confirmation or (retrace_confirmation and rollover_confirmation)):
            return {"action": "NONE", "state": self.state, "score": score}

        raw_risk_distance = max(
            metrics["atr"] * self.stop_atr_multiplier,
            abs(candle["high"] - close),
        )
        min_risk_distance = close * self.min_stop_pct
        risk_distance = max(raw_risk_distance, min_risk_distance)
        if self.max_stop_pct > 0:
            max_risk_distance = close * self.max_stop_pct
            risk_distance = min(risk_distance, max_risk_distance)

        stop_price = close + risk_distance
        structural_candidates = [
            metrics["vwap"],
            metrics["mean"] + (metrics["std"] * 0.25),
            metrics["mean"],
        ]
        structural_target = max([target for target in structural_candidates if target < close], default=close)
        min_rr_target = close - (risk_distance * self.min_take_profit_rr)
        max_rr_target = close - (risk_distance * self.max_take_profit_rr)
        take_profit = min(structural_target, min_rr_target) if structural_target < close else min_rr_target
        take_profit = max(take_profit, max_rr_target)
        reward_distance = close - take_profit
        reward_risk_ratio = reward_distance / risk_distance if risk_distance > 0 else 0.0

        signal = {
            "action": "SHORT",
            "symbol": candle["symbol"],
            "entry": close,
            "stop": stop_price,
            "tp": take_profit,
            "score": score,
            "reasons": reasons,
            "meta": {
                "state": self.state,
                "zscore": metrics["zscore"],
                "mean": metrics["mean"],
                "std": metrics["std"],
                "ema": metrics["ema"],
                "vwap": metrics["vwap"],
                "vwap_dev": close - metrics["vwap"],
                "atr": metrics["atr"],
                "volume_ratio": metrics["volume_ratio"],
                "armed_zscore": armed_zscore,
                "zscore_retrace": zscore_retrace,
                "risk_distance": risk_distance,
                "stop_pct": (risk_distance / close) if close else 0.0,
                "reward_risk_ratio": reward_risk_ratio,
                "retrace_confirmation": retrace_confirmation,
                "trend_confirmation": trend_confirmation,
                "strategy_profile": self.strategy_profile,
            },
            "timestamp": candle["timestamp"],
        }
        self.state = "TRIGGERED"
        self.armed_snapshot = None
        self.last_signal_ts = candle["timestamp"]
        return signal

    def _append_candle(self, candle: dict) -> None:
        self.timestamps.append(candle["timestamp"])
        self.highs.append(float(candle["high"]))
        self.lows.append(float(candle["low"]))
        self.closes.append(float(candle["close"]))
        self.volumes.append(float(candle["volume"]))

        max_length = max(self.lookback, self.std_window, self.vwap_window, self.atr_period + 5, 300)
        if len(self.closes) > max_length:
            self.timestamps = self.timestamps[-max_length:]
            self.highs = self.highs[-max_length:]
            self.lows = self.lows[-max_length:]
            self.closes = self.closes[-max_length:]
            self.volumes = self.volumes[-max_length:]

    def _metrics(self) -> dict:
        close = self.closes[-1]
        mean = rolling_mean(self.closes, self.lookback)
        std = max(rolling_std(self.closes, self.std_window), 1e-8)
        ema_value = ema(self.closes[-self.ema_period * 3 :], self.ema_period)
        vwap_value = vwap(self.closes, self.volumes, self.vwap_window)
        atr_value = atr(self.highs, self.lows, self.closes, self.atr_period)
        volume_avg = rolling_mean(self.volumes, self.vwap_window)
        volume_ratio = (self.volumes[-1] / volume_avg) if volume_avg else 1.0
        std_pct = std / close if close else 0.0
        upper_band = vwap_value + std
        return {
            "close": close,
            "mean": mean,
            "std": std,
            "zscore": (close - mean) / std,
            "ema": ema_value,
            "vwap": vwap_value,
            "atr": atr_value,
            "volume_ratio": volume_ratio,
            "std_pct": std_pct,
            "upper_band": upper_band,
        }

    def _score(self, metrics: dict, close: float, previous_close: float) -> tuple[int, list[str]]:
        score = 0
        reasons = []
        armed_zscore = metrics["zscore"]
        armed_close = close
        armed_vwap = metrics["vwap"]
        armed_std = metrics["std"]

        if self.armed_snapshot:
            armed_zscore = max(armed_zscore, self.armed_snapshot["zscore"])
            armed_close = max(armed_close, self.armed_snapshot["close"])
            armed_vwap = self.armed_snapshot["vwap"]
            armed_std = self.armed_snapshot["std"]

        if armed_zscore >= self.entry_zscore + 0.5:
            score += 3
            reasons.append("extreme_zscore")
        elif armed_zscore >= self.entry_zscore:
            score += 2
            reasons.append("entry_zscore")

        if armed_close > armed_vwap + armed_std:
            score += 2
            reasons.append("vwap_extension")
        elif armed_close > armed_vwap:
            score += 1
            reasons.append("above_vwap")

        if close < metrics["ema"]:
            score += 2
            reasons.append("below_ema")

        if close < previous_close:
            score += 1
            reasons.append("momentum_rollover")

        if metrics["volume_ratio"] >= 1.8:
            score += 2
            reasons.append("high_volume")
        elif metrics["volume_ratio"] >= 1.2:
            score += 1
            reasons.append("volume_confirm")

        if metrics["atr"] > metrics["std"] * 0.8:
            score += 1
            reasons.append("atr_support")

        if metrics["std_pct"] < self.low_volatility_filter_pct:
            score -= 2
            reasons.append("low_volatility_penalty")

        return score, reasons
