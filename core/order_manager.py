from datetime import datetime, timezone
from typing import Optional


class OrderManager:
    def __init__(self, config: dict):
        self.config = config
        self.mode = config.get("mode", "dry-run")
        self.dry_run_slippage_rate = max(
            0.0, float(config.get("execution", {}).get("dry_run_slippage_rate", 0.0))
        )
        self.position = None
        self._trade_sequence = 0

    def has_position(self) -> bool:
        return self.position is not None

    def can_open(self) -> bool:
        return self.position is None

    def open_position(self, execution_result: dict, signal: dict, market: dict) -> None:
        self._trade_sequence += 1
        opened_at = market.get("timestamp") or datetime.now(timezone.utc)
        entry_price = float(execution_result["entry_price"])
        reference_entry_price = float(execution_result.get("reference_entry_price", entry_price))
        entry_fill_price = float(execution_result.get("entry_fill_price", entry_price))
        entry_fee = float(execution_result.get("entry_fee", execution_result.get("fees_paid", 0.0)))
        total_fees = float(execution_result.get("total_fees", execution_result.get("fees_paid", 0.0)))
        notional = float(execution_result.get("notional", 0.0))
        leverage = float(execution_result.get("leverage", self.config.get("risk", {}).get("leverage", 1)))
        leverage = leverage if leverage > 0 else 1.0
        margin_required = float(execution_result.get("margin_required", notional / leverage))
        execution_meta = dict(execution_result.get("meta", {}))
        signal_meta = dict(signal.get("meta", {}))
        self.position = {
            "trade_id": self._trade_sequence,
            "mode": execution_result["mode"],
            "symbol": execution_result["symbol"],
            "side": "SHORT",
            "entry_price": entry_price,
            "reference_entry_price": reference_entry_price,
            "entry_fill_price": entry_fill_price,
            "stop_price": float(execution_result["stop_price"]),
            "take_profit_price": float(execution_result["take_profit_price"]),
            "quantity": float(execution_result["quantity"]),
            "notional": notional,
            "entry_fee": entry_fee,
            "total_fees": total_fees,
            "fees_paid": total_fees,
            "fee_rate": float(execution_result.get("fee_rate", 0.0)),
            "leverage": leverage,
            "margin_required": margin_required,
            "opened_at": opened_at,
            "score": int(signal.get("score", 0)),
            "strategy_profile": signal_meta.get(
                "strategy_profile",
                execution_meta.get("strategy_profile", self.config.get("strategy_profile", "default")),
            ),
            "signal_meta": signal_meta,
            "execution_meta": execution_meta,
            "reward_risk_ratio": float(signal_meta.get("reward_risk_ratio", execution_meta.get("reward_risk_ratio", 0.0))),
            "estimated_loss_at_stop": float(execution_meta.get("estimated_loss_at_stop", 0.0)),
            "estimated_gain_at_target": float(execution_meta.get("estimated_gain_at_target", 0.0)),
            "mae_price_distance": 0.0,
            "mfe_price_distance": 0.0,
            "mae_pct": 0.0,
            "mfe_pct": 0.0,
            "highest_price_seen": entry_price,
            "lowest_price_seen": entry_price,
            "notes": execution_result.get("notes", ""),
        }

    def restore_live_position(self, snapshot: dict) -> None:
        self._trade_sequence += 1
        self.position = {
            "trade_id": self._trade_sequence,
            "mode": "live",
            "symbol": snapshot["symbol"],
            "side": snapshot["side"],
            "entry_price": float(snapshot["entry_price"]),
            "stop_price": float(snapshot.get("stop_price", snapshot["entry_price"] * 1.01)),
            "take_profit_price": float(snapshot.get("take_profit_price", snapshot["entry_price"] * 0.99)),
            "quantity": float(snapshot["quantity"]),
            "notional": float(snapshot.get("notional", abs(snapshot["quantity"]) * snapshot["entry_price"])),
            "fees_paid": 0.0,
            "fee_rate": 0.0,
            "opened_at": datetime.now(timezone.utc),
            "score": int(snapshot.get("score", 0)),
            "signal_meta": dict(snapshot.get("signal_meta", {})),
            "execution_meta": dict(snapshot.get("execution_meta", {})),
            "notes": "restored_from_exchange",
        }

    def update_market(self, market: dict) -> Optional[dict]:
        if not self.position:
            return None
        if self.position["mode"] != "dry-run":
            return None

        high = float(market.get("high", market.get("close", market.get("price", 0.0))))
        low = float(market.get("low", market.get("close", market.get("price", 0.0))))
        self._update_excursions(high=high, low=low)
        stop_price = self.position["stop_price"]
        take_profit_price = self.position["take_profit_price"]

        stop_hit = high >= stop_price
        take_profit_hit = low <= take_profit_price

        if stop_hit:
            return self._close_position(exit_price=stop_price, exit_reason="STOP_LOSS", closed_at=market["timestamp"])
        if take_profit_hit:
            return self._close_position(
                exit_price=take_profit_price,
                exit_reason="TAKE_PROFIT",
                closed_at=market["timestamp"],
            )
        return None

    def current_position(self) -> Optional[dict]:
        return self.position

    def _close_position(self, exit_price: float, exit_reason: str, closed_at: datetime) -> dict:
        trade = self.position
        reference_entry_price = float(trade.get("reference_entry_price", trade["entry_price"]))
        entry_fill_price = float(trade.get("entry_fill_price", trade["entry_price"]))
        reference_exit_price = float(exit_price)
        exit_fill_price = reference_exit_price * (1.0 + self.dry_run_slippage_rate)
        reference_gross_pnl = (reference_entry_price - reference_exit_price) * trade["quantity"]
        gross_pnl = (entry_fill_price - exit_fill_price) * trade["quantity"]
        exit_fee = exit_fill_price * trade["quantity"] * trade["fee_rate"]
        total_fees = float(trade.get("entry_fee", trade.get("fees_paid", 0.0))) + exit_fee
        slippage_cost = reference_gross_pnl - gross_pnl
        net_pnl = gross_pnl - total_fees
        duration = (closed_at - trade["opened_at"]).total_seconds()
        return_pct = (net_pnl / trade["notional"] * 100.0) if trade["notional"] else 0.0

        closed_trade = {
            "trade_id": trade["trade_id"],
            "symbol": trade["symbol"],
            "mode": trade["mode"],
            "side": trade["side"],
            "entry_price": trade["entry_price"],
            "reference_entry_price": reference_entry_price,
            "entry_fill_price": entry_fill_price,
            "exit_price": exit_fill_price,
            "reference_exit_price": reference_exit_price,
            "exit_fill_price": exit_fill_price,
            "stop_price": trade["stop_price"],
            "take_profit_price": trade["take_profit_price"],
            "quantity": trade["quantity"],
            "notional": trade["notional"],
            "margin_required": float(trade.get("margin_required", 0.0)),
            "exit_fee": exit_fee,
            "total_fees": total_fees,
            "reference_gross_pnl": reference_gross_pnl,
            "gross_pnl": gross_pnl,
            "slippage_cost": slippage_cost,
            "net_pnl": net_pnl,
            "fees_paid": total_fees,
            "pnl": net_pnl,
            "return_pct": return_pct,
            "score": trade["score"],
            "strategy_profile": trade.get("strategy_profile", self.config.get("strategy_profile", "default")),
            "zscore": trade["signal_meta"].get("zscore"),
            "vwap": trade["signal_meta"].get("vwap"),
            "vwap_dev": trade["signal_meta"].get("vwap_dev"),
            "atr": trade["signal_meta"].get("atr"),
            "volume_ratio": trade["signal_meta"].get("volume_ratio"),
            "reward_risk_ratio": trade.get("reward_risk_ratio", 0.0),
            "estimated_loss_at_stop": trade.get("estimated_loss_at_stop", 0.0),
            "estimated_gain_at_target": trade.get("estimated_gain_at_target", 0.0),
            "mae_price_distance": trade.get("mae_price_distance", 0.0),
            "mfe_price_distance": trade.get("mfe_price_distance", 0.0),
            "mae_pct": trade.get("mae_pct", 0.0),
            "mfe_pct": trade.get("mfe_pct", 0.0),
            "entry_time": trade["opened_at"],
            "exit_time": closed_at,
            "duration_sec": duration,
            "exit_reason": exit_reason,
            "notes": trade.get("notes", ""),
        }
        self.position = None
        return closed_trade

    def _update_excursions(self, high: float, low: float) -> None:
        if not self.position:
            return
        entry_price = self.position["entry_price"]
        self.position["highest_price_seen"] = max(self.position.get("highest_price_seen", entry_price), high)
        self.position["lowest_price_seen"] = min(self.position.get("lowest_price_seen", entry_price), low)

        adverse_distance = max(0.0, self.position["highest_price_seen"] - entry_price)
        favorable_distance = max(0.0, entry_price - self.position["lowest_price_seen"])

        self.position["mae_price_distance"] = max(self.position.get("mae_price_distance", 0.0), adverse_distance)
        self.position["mfe_price_distance"] = max(self.position.get("mfe_price_distance", 0.0), favorable_distance)
        if entry_price > 0:
            self.position["mae_pct"] = self.position["mae_price_distance"] / entry_price
            self.position["mfe_pct"] = self.position["mfe_price_distance"] / entry_price
