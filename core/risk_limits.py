from __future__ import annotations

from typing import Any


def _to_float(value: Any, default: float = 0.0) -> float:
    if value in ("", None):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_positive_limit(value: Any) -> float | None:
    resolved = _to_float(value, default=0.0)
    if resolved <= 0:
        return None
    return resolved


class RiskLimits:
    def __init__(
        self,
        *,
        max_symbol_position_qty: float | None = None,
        max_symbol_notional: float | None = None,
        max_strategy_positions: int | None = None,
        max_account_positions: int | None = None,
        max_per_trade_risk: float | None = None,
        max_account_total_risk: float | None = None,
    ):
        self.max_symbol_position_qty = _to_positive_limit(max_symbol_position_qty)
        self.max_symbol_notional = _to_positive_limit(max_symbol_notional)
        self.max_strategy_positions = (
            int(max_strategy_positions) if max_strategy_positions and int(max_strategy_positions) > 0 else None
        )
        self.max_account_positions = (
            int(max_account_positions) if max_account_positions and int(max_account_positions) > 0 else None
        )
        self.max_per_trade_risk = _to_positive_limit(max_per_trade_risk)
        self.max_account_total_risk = _to_positive_limit(max_account_total_risk)

    @classmethod
    def from_config(cls, config: dict | None) -> "RiskLimits":
        source = {}
        if isinstance(config, dict):
            source = dict(config.get("risk_limits", {}))
        return cls(
            max_symbol_position_qty=source.get("max_symbol_position_qty"),
            max_symbol_notional=source.get("max_symbol_notional"),
            max_strategy_positions=source.get("max_strategy_positions"),
            max_account_positions=source.get("max_account_positions"),
            max_per_trade_risk=source.get("max_per_trade_risk"),
            max_account_total_risk=source.get("max_account_total_risk"),
        )

    def can_open_new_position(
        self,
        *,
        symbol: str,
        strategy_profile: str,
        side: str,
        quantity: float,
        entry_price: float,
        stop_price: float,
        open_positions: list[dict],
    ) -> dict[str, Any]:
        resolved_symbol = str(symbol or "").strip().upper()
        resolved_strategy = str(strategy_profile or "").strip() or "default"
        resolved_side = str(side or "").strip().upper() or "SHORT"
        request_qty = max(_to_float(quantity, default=0.0), 0.0)
        request_entry_price = max(_to_float(entry_price, default=0.0), 0.0)
        request_notional = request_qty * request_entry_price
        request_risk = self._compute_trade_risk(
            side=resolved_side,
            quantity=request_qty,
            entry_price=request_entry_price,
            stop_price=_to_float(stop_price, default=0.0),
        )

        normalized_positions = [dict(pos) for pos in open_positions if isinstance(pos, dict)]
        symbol_qty = 0.0
        symbol_notional = 0.0
        strategy_count = 0
        account_count = 0
        total_risk = request_risk

        for position in normalized_positions:
            qty = abs(_to_float(position.get("quantity", 0.0), default=0.0))
            if qty <= 0:
                continue
            account_count += 1
            position_symbol = str(position.get("symbol", "")).strip().upper()
            if position_symbol == resolved_symbol:
                symbol_qty += qty
                position_notional = abs(
                    _to_float(position.get("notional", qty * _to_float(position.get("entry_price", 0.0))), default=0.0)
                )
                symbol_notional += position_notional
            position_strategy = str(position.get("strategy_profile", "default")).strip() or "default"
            if position_strategy == resolved_strategy:
                strategy_count += 1
            total_risk += self._position_risk(position)

        if self.max_symbol_position_qty is not None and symbol_qty + request_qty > self.max_symbol_position_qty:
            return {"allowed": False, "reason": "symbol_limit_exceeded", "error_code": "symbol_limit_exceeded"}
        if self.max_symbol_notional is not None and symbol_notional + request_notional > self.max_symbol_notional:
            return {"allowed": False, "reason": "symbol_limit_exceeded", "error_code": "symbol_limit_exceeded"}
        if self.max_strategy_positions is not None and strategy_count + 1 > self.max_strategy_positions:
            return {
                "allowed": False,
                "reason": "strategy_limit_exceeded",
                "error_code": "strategy_limit_exceeded",
            }
        if self.max_account_positions is not None and account_count + 1 > self.max_account_positions:
            return {"allowed": False, "reason": "account_limit_exceeded", "error_code": "account_limit_exceeded"}
        if self.max_per_trade_risk is not None and request_risk > self.max_per_trade_risk:
            return {"allowed": False, "reason": "per_trade_risk_exceeded", "error_code": "per_trade_risk_exceeded"}
        if self.max_account_total_risk is not None and total_risk > self.max_account_total_risk:
            return {
                "allowed": False,
                "reason": "account_total_risk_exceeded",
                "error_code": "account_total_risk_exceeded",
            }
        return {"allowed": True, "reason": "", "error_code": ""}

    def can_close_position(self) -> dict[str, Any]:
        return {"allowed": True, "reason": "", "error_code": ""}

    def _position_risk(self, position: dict) -> float:
        estimated_loss = _to_float(position.get("estimated_loss_at_stop", 0.0), default=0.0)
        if estimated_loss > 0:
            return estimated_loss
        return self._compute_trade_risk(
            side=str(position.get("side", "SHORT")).strip().upper() or "SHORT",
            quantity=abs(_to_float(position.get("quantity", 0.0), default=0.0)),
            entry_price=_to_float(position.get("entry_price", 0.0), default=0.0),
            stop_price=_to_float(position.get("stop_price", 0.0), default=0.0),
        )

    @staticmethod
    def _compute_trade_risk(*, side: str, quantity: float, entry_price: float, stop_price: float) -> float:
        if quantity <= 0 or entry_price <= 0 or stop_price <= 0:
            return 0.0
        if side == "LONG":
            per_unit = max(entry_price - stop_price, 0.0)
        else:
            per_unit = max(stop_price - entry_price, 0.0)
        return per_unit * quantity
