from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def normalize_account_snapshot(raw: Any) -> dict[str, Any]:
    row = dict(raw) if isinstance(raw, dict) else {}
    equity = _to_float(
        row.get(
            "equity",
            row.get(
                "wallet_balance",
                row.get("walletBalance", row.get("totalWalletBalance", 0.0)),
            ),
        )
    )
    wallet_balance = _to_float(
        row.get("wallet_balance", row.get("walletBalance", row.get("totalWalletBalance", equity)))
    )
    available_balance = _to_float(
        row.get("available_balance", row.get("availableBalance", row.get("free", 0.0)))
    )
    used_margin = _to_float(row.get("used_margin", max(wallet_balance - available_balance, 0.0)))
    return {
        "equity": equity,
        "wallet_balance": wallet_balance,
        "available_balance": available_balance,
        "used_margin": used_margin,
        "timestamp": _normalize_timestamp(row.get("timestamp", row.get("updateTime"))),
    }


def normalize_positions(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    rows: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        symbol = str(item.get("symbol", "")).strip().upper()
        if symbol == "":
            continue
        position_amt = _to_float(
            item.get("position_amt", item.get("positionAmt", item.get("qty", item.get("amount", 0.0))))
        )
        side = str(item.get("side", "")).strip().upper()
        if side == "":
            if position_amt > 0:
                side = "LONG"
            elif position_amt < 0:
                side = "SHORT"
            else:
                side = "FLAT"
        rows.append(
            {
                "symbol": symbol,
                "side": side,
                "position_amt": position_amt,
                "qty": abs(position_amt),
                "entry_price": _to_float(item.get("entry_price", item.get("entryPrice", 0.0))),
                "unrealized_pnl": _to_float(
                    item.get("unrealized_pnl", item.get("unRealizedProfit", item.get("upl", 0.0)))
                ),
                "timestamp": _normalize_timestamp(item.get("timestamp", item.get("updateTime"))),
            }
        )
    return rows


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_position_mode(raw: Any) -> str:
    row = dict(raw) if isinstance(raw, dict) else {}
    explicit_mode = str(row.get("position_mode", row.get("positionMode", ""))).strip().upper()
    if explicit_mode:
        return explicit_mode
    dual_flag = row.get("dualSidePosition", row.get("hedgeMode", None))
    if isinstance(dual_flag, str):
        dual_flag = dual_flag.strip().lower() in {"true", "1", "yes"}
    if dual_flag is True:
        return "HEDGE"
    if dual_flag is False:
        return "ONE_WAY"
    return ""


def normalize_account_details(raw: Any) -> dict[str, Any]:
    row = dict(raw) if isinstance(raw, dict) else {}
    maker_fee = _normalize_fee_rate(
        row.get("maker_fee", row.get("makerFee", row.get("makerCommission", row.get("maker_commission", ""))))
    )
    taker_fee = _normalize_fee_rate(
        row.get("taker_fee", row.get("takerFee", row.get("takerCommission", row.get("taker_commission", ""))))
    )
    fee_rate = _normalize_fee_rate(row.get("fee_rate", row.get("feeRate", taker_fee)))
    funding_fee = _to_float(
        row.get(
            "funding_fee",
            row.get("fundingFee", row.get("funding_accrual", row.get("totalFundingFee", 0.0))),
        )
    )
    position_mode = normalize_position_mode(row)
    margin_mode = str(row.get("margin_mode", row.get("marginMode", row.get("marginType", "")))).strip().upper()
    if margin_mode in {"CROSSED"}:
        margin_mode = "CROSS"
    leverage = _to_float(row.get("leverage", row.get("maxLeverage", row.get("initialLeverage", 0.0))))

    warnings: list[str] = []
    if position_mode in {"HEDGE", "DUAL_SIDE", "DUAL", "BOTH"}:
        warnings.append("unsupported_position_mode")
    if margin_mode not in {"", "ISOLATED", "CROSS"}:
        warnings.append("unsupported_margin_mode")

    return {
        "fee_rate": fee_rate,
        "maker_fee": maker_fee,
        "taker_fee": taker_fee,
        "funding_fee": funding_fee,
        "position_mode": position_mode,
        "margin_mode": margin_mode,
        "leverage": leverage,
        "warnings": warnings,
        "timestamp": _normalize_timestamp(row.get("timestamp", row.get("updateTime"))),
    }


def build_account_detail_snapshot(*, account_snapshot: Any, account_details: Any) -> dict[str, Any]:
    snapshot = normalize_account_snapshot(account_snapshot)
    details = normalize_account_details(account_details)
    merged = dict(snapshot)
    merged.update(
        {
            "fee_rate": details.get("fee_rate", 0.0),
            "maker_fee": details.get("maker_fee", 0.0),
            "taker_fee": details.get("taker_fee", 0.0),
            "funding_fee": details.get("funding_fee", 0.0),
            "position_mode": details.get("position_mode", ""),
            "margin_mode": details.get("margin_mode", ""),
            "leverage": details.get("leverage", 0.0),
            "warnings": list(details.get("warnings", [])),
        }
    )
    return merged


def _to_float(value: Any, default: float = 0.0) -> float:
    if value in ("", None):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_fee_rate(value: Any) -> float:
    rate = _to_float(value, default=0.0)
    if rate > 1:
        # Binance often uses bps or commission integer scales in payloads.
        return rate / 10000.0
    return rate


def _normalize_timestamp(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, (int, float)):
        if value > 1e12:
            value = value / 1000.0
        return datetime.fromtimestamp(float(value), tz=timezone.utc).isoformat()
    if value not in ("", None):
        return str(value)
    return now_iso()
