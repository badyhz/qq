import time


class ExecutionEngine:
    def __init__(self, config: dict, order_manager, exchange, logger):
        self.config = config
        self.order_manager = order_manager
        self.exchange = exchange
        self.logger = logger
        self.mode = config.get("mode", "dry-run")
        self.fee_rate = float(config.get("execution", {}).get("dry_run_fee_rate", 0.0004))
        self.allow_live_without_protection = bool(
            config.get("execution", {}).get("allow_live_without_protection", False)
        )
        self.slippage_threshold = float(config.get("execution", {}).get("slippage_threshold", 0.003))
        self.logger.info(
            "Execution engine initialized | mode=%s | fee_rate=%s%% | slippage_threshold=%s%%",
            self.mode, self.fee_rate * 100, self.slippage_threshold * 100
        )

    def open_short(self, position_plan: dict, signal: dict, market: dict) -> dict:
        execution_start = time.time()
        signal_meta = signal.get("meta", {})
        self.logger.debug(
            "Attempting to open short position | signal_score=%s | signal_zscore=%.4f",
            signal.get("score"), signal_meta.get("zscore", 0.0)
        )
        
        if position_plan["quantity"] <= 0:
            self.logger.warning(
                "Execution rejected | reason=invalid_quantity | quantity=%s",
                position_plan["quantity"]
            )
            return {"accepted": False, "reason": "invalid_quantity"}

        if self.mode == "dry-run":
            entry_price = float(market["close"])
            quantity = float(position_plan["quantity"])
            entry_fee = entry_price * quantity * self.fee_rate
            notional = quantity * entry_price
            duration = time.time() - execution_start
            
            result = {
                "accepted": True,
                "mode": "dry-run",
                "symbol": signal["symbol"],
                "entry_price": entry_price,
                "stop_price": float(position_plan["stop_price"]),
                "take_profit_price": float(position_plan["take_profit_price"]),
                "quantity": quantity,
                "notional": notional,
                "fees_paid": entry_fee,
                "fee_rate": self.fee_rate,
                "meta": {
                    "signal_reasons": signal.get("reasons", []),
                    "reward_risk_ratio": position_plan.get("reward_risk_ratio", 0.0),
                    "estimated_loss_at_stop": position_plan.get("estimated_loss_at_stop", 0.0),
                    "estimated_gain_at_target": position_plan.get("estimated_gain_at_target", 0.0),
                    "strategy_profile": signal_meta.get(
                        "strategy_profile",
                        self.config.get("strategy_profile", "default"),
                    ),
                },
                "notes": "dry_run_open",
                "execution_duration": duration,
            }
            
            self.logger.info(
                "DRY-RUN EXECUTION SUCCESS | entry=%.4f | qty=%.6f | notional=%.2f USDT | "
                "stop=%.4f | take_profit=%.4f | fee=%.4f USDT | duration=%.3fs",
                entry_price, quantity, notional,
                float(position_plan["stop_price"]), float(position_plan["take_profit_price"]),
                entry_fee, duration
            )
            return result

        if not self.exchange.is_enabled():
            self.logger.warning("Execution rejected | reason=live_exchange_not_available")
            return {"accepted": False, "reason": "live_exchange_not_available"}

        self.logger.info("Placing live short order | notional=%s", position_plan.get("notional"))
        result = self.exchange.place_short_bracket(position_plan, signal)
        
        if result.get("accepted"):
            duration = time.time() - execution_start
            self.logger.info(
                "LIVE EXECUTION SUCCESS | entry=%s | qty=%s | duration=%.3fs",
                result.get("entry_price"), result.get("quantity"), duration
            )
            if not self.allow_live_without_protection:
                if not result.get("stop_price") or not result.get("take_profit_price"):
                    self.logger.error(
                        "LIVE EXECUTION FAILED | reason=protection_orders_missing | "
                        "stop_price=%s | take_profit_price=%s",
                        result.get("stop_price"), result.get("take_profit_price")
                    )
                    return {"accepted": False, "reason": "protection_orders_missing"}
        else:
            self.logger.warning(
                "LIVE EXECUTION REJECTED | reason=%s",
                result.get("reason", "unknown")
            )
        
        return result

    def ensure_live_protection(self) -> None:
        if self.mode != "live":
            return
        position = self.order_manager.current_position()
        if not position:
            self.logger.debug("No active position, skipping protection check")
            return
        
        check_start = time.time()
        self.logger.debug("Checking live protection orders for position")
        actions = self.exchange.ensure_protection_orders(position)
        check_duration = time.time() - check_start
        
        if actions:
            self.logger.warning(
                "LIVE PROTECTION REPAIRED | actions=%s | check_duration=%.3fs",
                ",".join(actions), check_duration
            )
        else:
            self.logger.debug("Protection orders verified | duration=%.3fs", check_duration)
