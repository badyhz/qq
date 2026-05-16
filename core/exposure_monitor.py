from __future__ import annotations

from typing import Any


def build_account_risk_snapshot(
    *,
    account_snapshot: dict[str, Any],
    positions: list[dict[str, Any]],
    account_details: dict[str, Any] | None = None,
    realized_pnl: float = 0.0,
    unrealized_pnl: float | None = None,
) -> dict[str, Any]:
    equity = _to_float(account_snapshot.get("equity", account_snapshot.get("wallet_balance", 0.0)))
    wallet_balance = _to_float(account_snapshot.get("wallet_balance", equity))
    available_balance = _to_float(account_snapshot.get("available_balance", 0.0))
    used_margin = _to_float(account_snapshot.get("used_margin", max(wallet_balance - available_balance, 0.0)))

    symbol_exposures: dict[str, dict[str, float]] = {}
    long_exposure = 0.0
    short_exposure = 0.0
    computed_unrealized = 0.0

    for position in positions:
        if not isinstance(position, dict):
            continue
        symbol = str(position.get("symbol", "")).strip().upper()
        if not symbol:
            continue
        side = str(position.get("side", "")).strip().upper()
        qty = _resolve_qty(position)
        entry_price = _to_float(position.get("entry_price", position.get("entryPrice", 0.0)))
        notional = abs(qty * entry_price)
        pos_unrealized = _to_float(position.get("unrealized_pnl", position.get("unRealizedProfit", 0.0)))
        computed_unrealized += pos_unrealized
        row = symbol_exposures.setdefault(symbol, {"notional": 0.0, "long": 0.0, "short": 0.0, "net": 0.0})
        row["notional"] += notional
        if side == "SHORT" or qty < 0:
            row["short"] += notional
            row["net"] -= notional
            short_exposure += notional
        else:
            row["long"] += notional
            row["net"] += notional
            long_exposure += notional

    total_notional_exposure = long_exposure + short_exposure
    resolved_unrealized = computed_unrealized if unrealized_pnl is None else float(unrealized_pnl)
    resolved_realized = float(realized_pnl)
    exposure_ratio = (total_notional_exposure / equity) if equity > 0 else 0.0
    details = dict(account_details or {})

    return {
        "equity": equity,
        "wallet_balance": wallet_balance,
        "available_balance": available_balance,
        "used_margin": used_margin,
        "unrealized_pnl": resolved_unrealized,
        "realized_pnl": resolved_realized,
        "total_notional_exposure": total_notional_exposure,
        "long_exposure": long_exposure,
        "short_exposure": short_exposure,
        "exposure_ratio": exposure_ratio,
        "symbol_exposures": symbol_exposures,
        "fee_rate": _to_float(details.get("fee_rate", account_snapshot.get("fee_rate", 0.0))),
        "maker_fee": _to_float(details.get("maker_fee", account_snapshot.get("maker_fee", 0.0))),
        "taker_fee": _to_float(details.get("taker_fee", account_snapshot.get("taker_fee", 0.0))),
        "funding_fee": _to_float(details.get("funding_fee", account_snapshot.get("funding_fee", 0.0))),
        "position_mode": str(details.get("position_mode", account_snapshot.get("position_mode", ""))),
        "margin_mode": str(details.get("margin_mode", account_snapshot.get("margin_mode", ""))),
        "leverage": _to_float(details.get("leverage", account_snapshot.get("leverage", 0.0))),
        "detail_warnings": list(details.get("warnings", [])) if isinstance(details.get("warnings", []), list) else [],
    }


def _resolve_qty(position: dict[str, Any]) -> float:
    if position.get("position_amt") not in ("", None):
        return _to_float(position.get("position_amt", 0.0))
    if position.get("positionAmt") not in ("", None):
        return _to_float(position.get("positionAmt", 0.0))
    qty = _to_float(position.get("qty", position.get("quantity", 0.0)))
    side = str(position.get("side", "")).strip().upper()
    if side == "SHORT" and qty > 0:
        return -qty
    return qty


def _to_float(value: Any, default: float = 0.0) -> float:
    if value in ("", None):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
