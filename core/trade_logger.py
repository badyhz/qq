import csv
import math
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


TRADE_CSV_COLUMNS = [
    "trade_id",
    "symbol",
    "mode",
    "side",
    "timeframe",
    "strategy_tag",
    "strategy_profile",
    "status",
    "open_time",
    "close_time",
    "entry_time",
    "exit_time",
    "entry_price",
    "exit_price",
    "stop_price",
    "take_profit_price",
    "qty",
    "quantity",
    "leverage",
    "notional",
    "margin_required",
    "gross_pnl",
    "net_pnl",
    "pnl",
    "fee_open",
    "fee_close",
    "fees_total",
    "total_cost",
    "slippage_open",
    "slippage_close",
    "slippage_total",
    "funding_fee",
    "borrow_cost",
    "other_cost",
    "risk_amount",
    "r_multiple",
    "pnl_pct",
    "equity_before",
    "equity_after",
    "return_on_equity",
    "holding_seconds",
    "holding_bars",
    "duration_sec",
    "score",
    "zscore",
    "vwap",
    "vwap_dev",
    "atr",
    "volume_ratio",
    "reward_risk_ratio",
    "estimated_loss_at_stop",
    "estimated_gain_at_target",
    "mae_price_distance",
    "mfe_price_distance",
    "mae_pct",
    "mfe_pct",
    "exit_reason",
    "notes",
]


def _to_float(value: Any, default: float = 0.0) -> float:
    if value in (None, ""):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_scalar(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _compact_number(value: Any) -> Any:
    if isinstance(value, float) and math.isfinite(value) and value.is_integer():
        return int(value)
    return value


def _parse_timeframe_seconds(timeframe: str) -> int:
    raw = str(timeframe or "").strip().lower()
    if not raw:
        return 0
    unit = raw[-1]
    number = raw[:-1]
    if not number.isdigit():
        return 0
    count = int(number)
    if unit == "m":
        return count * 60
    if unit == "h":
        return count * 3600
    if unit == "d":
        return count * 86400
    return 0


def _compute_holding_bars(holding_seconds: float, timeframe: str) -> int:
    bar_seconds = _parse_timeframe_seconds(timeframe)
    if holding_seconds <= 0 or bar_seconds <= 0:
        return 0
    return max(1, int(round(holding_seconds / bar_seconds)))


def _legacy_aliases(source: dict) -> dict:
    data = dict(source)

    if data.get("qty") in (None, "") and data.get("quantity") not in (None, ""):
        data["qty"] = data.get("quantity")
    if data.get("quantity") in (None, "") and data.get("qty") not in (None, ""):
        data["quantity"] = data.get("qty")

    if data.get("open_time") in (None, "") and data.get("entry_time") not in (None, ""):
        data["open_time"] = data.get("entry_time")
    if data.get("entry_time") in (None, "") and data.get("open_time") not in (None, ""):
        data["entry_time"] = data.get("open_time")

    if data.get("close_time") in (None, "") and data.get("exit_time") not in (None, ""):
        data["close_time"] = data.get("exit_time")
    if data.get("exit_time") in (None, "") and data.get("close_time") not in (None, ""):
        data["exit_time"] = data.get("close_time")

    if data.get("net_pnl") in (None, "") and data.get("pnl") not in (None, ""):
        data["net_pnl"] = data.get("pnl")
    if data.get("pnl") in (None, "") and data.get("net_pnl") not in (None, ""):
        data["pnl"] = data.get("net_pnl")

    if data.get("fee_open") in (None, "") and data.get("entry_fee") not in (None, ""):
        data["fee_open"] = data.get("entry_fee")
    if data.get("fee_close") in (None, "") and data.get("exit_fee") not in (None, ""):
        data["fee_close"] = data.get("exit_fee")

    if data.get("fees_total") in (None, ""):
        if data.get("total_fees") not in (None, ""):
            data["fees_total"] = data.get("total_fees")
        else:
            data["fees_total"] = _to_float(data.get("fee_open")) + _to_float(data.get("fee_close"))

    if data.get("strategy_tag") in (None, "") and data.get("strategy_profile") not in (None, ""):
        data["strategy_tag"] = data.get("strategy_profile")

    if data.get("risk_amount") in (None, "") and data.get("estimated_loss_at_stop") not in (None, ""):
        data["risk_amount"] = data.get("estimated_loss_at_stop")

    if data.get("holding_seconds") in (None, "") and data.get("duration_sec") not in (None, ""):
        data["holding_seconds"] = data.get("duration_sec")
    if data.get("duration_sec") in (None, "") and data.get("holding_seconds") not in (None, ""):
        data["duration_sec"] = data.get("holding_seconds")

    if data.get("status") in (None, ""):
        data["status"] = "CLOSED" if data.get("close_time") not in (None, "") else "OPEN"

    return data


def _canonical_trade_row(source: dict, default_timeframe: str = "", default_strategy_tag: str = "") -> dict:
    data = _legacy_aliases(source)

    timeframe = str(data.get("timeframe") or default_timeframe or "")
    strategy_tag = str(data.get("strategy_tag") or default_strategy_tag or "")

    risk_amount = _to_float(data.get("risk_amount"), 0.0)
    net_pnl = _to_float(data.get("net_pnl"), 0.0)

    raw_qty = data.get("qty", data.get("quantity", ""))
    raw_quantity = data.get("quantity", data.get("qty", ""))

    row = {key: "" for key in TRADE_CSV_COLUMNS}
    row.update(
        {
            "trade_id": str(data.get("trade_id", "")),
            "symbol": _normalize_scalar(data.get("symbol", "")),
            "mode": _normalize_scalar(data.get("mode", "")),
            "side": str(data.get("side", "")),
            "timeframe": timeframe,
            "strategy_tag": strategy_tag,
            "strategy_profile": str(data.get("strategy_profile", strategy_tag)),
            "status": str(data.get("status", "OPEN")),
            "open_time": _normalize_scalar(data.get("open_time", "")),
            "close_time": _normalize_scalar(data.get("close_time", "")),
            "entry_time": _normalize_scalar(data.get("entry_time", data.get("open_time", ""))),
            "exit_time": _normalize_scalar(data.get("exit_time", data.get("close_time", ""))),
            "entry_price": _to_float(data.get("entry_price"), 0.0),
            "exit_price": _to_float(data.get("exit_price"), 0.0),
            "stop_price": _to_float(data.get("stop_price"), 0.0),
            "take_profit_price": _to_float(data.get("take_profit_price"), 0.0),
            "qty": _normalize_scalar(raw_qty) if raw_qty not in (None, "") else 0.0,
            "quantity": _normalize_scalar(raw_quantity) if raw_quantity not in (None, "") else _to_float(raw_qty, 0.0),
            "leverage": _to_float(data.get("leverage"), 0.0),
            "notional": _to_float(data.get("notional"), 0.0),
            "margin_required": _to_float(data.get("margin_required"), 0.0),
            "gross_pnl": _to_float(data.get("gross_pnl"), 0.0),
            "net_pnl": net_pnl,
            "pnl": _to_float(data.get("pnl"), net_pnl),
            "fee_open": _to_float(data.get("fee_open"), 0.0),
            "fee_close": _to_float(data.get("fee_close"), 0.0),
            "fees_total": _to_float(data.get("fees_total"), 0.0),
            "total_cost": _to_float(data.get("total_cost"), 0.0),
            "slippage_open": _to_float(data.get("slippage_open"), 0.0),
            "slippage_close": _to_float(data.get("slippage_close"), 0.0),
            "slippage_total": _to_float(data.get("slippage_total"), 0.0),
            "funding_fee": _to_float(data.get("funding_fee"), 0.0),
            "borrow_cost": _to_float(data.get("borrow_cost"), 0.0),
            "other_cost": _to_float(data.get("other_cost"), 0.0),
            "risk_amount": risk_amount,
            "r_multiple": _to_float(data.get("r_multiple"), 0.0),
            "pnl_pct": _to_float(data.get("pnl_pct"), _to_float(data.get("return_pct"), 0.0)),
            "equity_before": _to_float(data.get("equity_before"), 0.0),
            "equity_after": _to_float(data.get("equity_after"), 0.0),
            "return_on_equity": _to_float(data.get("return_on_equity"), 0.0),
            "holding_seconds": _to_float(data.get("holding_seconds"), 0.0),
            "holding_bars": int(_to_float(data.get("holding_bars"), 0.0)),
            "duration_sec": _to_float(data.get("duration_sec"), 0.0),
            "score": _to_float(data.get("score"), 0.0),
            "zscore": _to_float(data.get("zscore"), 0.0),
            "vwap": _to_float(data.get("vwap"), 0.0),
            "vwap_dev": _to_float(data.get("vwap_dev"), 0.0),
            "atr": _to_float(data.get("atr"), 0.0),
            "volume_ratio": _to_float(data.get("volume_ratio"), 0.0),
            "reward_risk_ratio": _to_float(data.get("reward_risk_ratio"), 0.0),
            "estimated_loss_at_stop": _to_float(data.get("estimated_loss_at_stop"), 0.0),
            "estimated_gain_at_target": _to_float(data.get("estimated_gain_at_target"), 0.0),
            "mae_price_distance": _to_float(data.get("mae_price_distance"), 0.0),
            "mfe_price_distance": _to_float(data.get("mfe_price_distance"), 0.0),
            "mae_pct": _to_float(data.get("mae_pct"), 0.0),
            "mfe_pct": _to_float(data.get("mfe_pct"), 0.0),
            "exit_reason": str(data.get("exit_reason", "")),
            "notes": str(data.get("notes", "")),
        }
    )

    if row["holding_seconds"] <= 0 and row["duration_sec"] > 0:
        row["holding_seconds"] = row["duration_sec"]
    if row["duration_sec"] <= 0 and row["holding_seconds"] > 0:
        row["duration_sec"] = row["holding_seconds"]

    if row["holding_bars"] <= 0:
        row["holding_bars"] = _compute_holding_bars(row["holding_seconds"], timeframe)

    if row["fees_total"] == 0.0:
        row["fees_total"] = row["fee_open"] + row["fee_close"]

    if row["risk_amount"] > 0 and row["r_multiple"] == 0.0:
        row["r_multiple"] = row["net_pnl"] / row["risk_amount"]

    if row["status"] == "" or row["status"] == "None":
        row["status"] = "CLOSED" if row["close_time"] else "OPEN"

    row["qty"] = _compact_number(_to_float(row["qty"], 0.0))
    row["quantity"] = _compact_number(_to_float(row["quantity"], 0.0))
    row["holding_seconds"] = _compact_number(_to_float(row["holding_seconds"], 0.0))
    row["duration_sec"] = _compact_number(_to_float(row["duration_sec"], 0.0))

    return row


def ensure_csv_schema(csv_path: Path) -> None:
    path = Path(csv_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if not path.exists():
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=TRADE_CSV_COLUMNS)
            writer.writeheader()
        return

    with path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames == TRADE_CSV_COLUMNS:
            return
        rows = list(reader)

    migrated_rows = [_canonical_trade_row(row) for row in rows]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=TRADE_CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(migrated_rows)


def append_trade(csv_path: Path, trade: "TradeRecord | dict") -> dict:
    path = Path(csv_path)
    ensure_csv_schema(path)

    if isinstance(trade, TradeRecord):
        source = asdict(trade)
    else:
        source = dict(trade)

    row = _canonical_trade_row(source)
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=TRADE_CSV_COLUMNS)
        writer.writerow(row)
    return row


def update_trade(csv_path: Path, trade_id: str, updates: dict) -> bool:
    path = Path(csv_path)
    ensure_csv_schema(path)

    with path.open("r", newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    updated = False
    next_rows = []
    for row in rows:
        if str(row.get("trade_id", "")) == str(trade_id):
            merged = dict(row)
            merged.update(updates)
            row = _canonical_trade_row(merged)
            updated = True
        next_rows.append(row)

    if updated:
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=TRADE_CSV_COLUMNS)
            writer.writeheader()
            writer.writerows(next_rows)

    return updated


def compute_trade_economics(
    *,
    side: str,
    entry_price: float,
    exit_price: float,
    qty: float,
    risk_amount: float,
    fee_open: float = 0.0,
    fee_close: float = 0.0,
    slippage_open: float = 0.0,
    slippage_close: float = 0.0,
    funding_fee: float = 0.0,
    borrow_cost: float = 0.0,
    other_cost: float = 0.0,
    equity_before: float = 0.0,
) -> dict:
    direction = str(side).strip().upper()
    signed_qty = abs(float(qty))
    notional = abs(float(entry_price)) * signed_qty

    if direction == "SHORT":
        gross_pnl = (float(entry_price) - float(exit_price)) * signed_qty
    else:
        gross_pnl = (float(exit_price) - float(entry_price)) * signed_qty

    fees_total = float(fee_open) + float(fee_close)
    slippage_total = float(slippage_open) + float(slippage_close)
    total_cost = fees_total + float(funding_fee) + float(borrow_cost) + float(other_cost)
    net_pnl = gross_pnl - total_cost

    pnl_pct = (net_pnl / notional * 100.0) if notional else 0.0
    r_multiple = (net_pnl / float(risk_amount)) if float(risk_amount) else 0.0
    equity_after = float(equity_before) + net_pnl
    return_on_equity = (net_pnl / float(equity_before) * 100.0) if float(equity_before) else 0.0

    return {
        "notional": notional,
        "gross_pnl": gross_pnl,
        "fees_total": fees_total,
        "slippage_total": slippage_total,
        "total_cost": total_cost,
        "net_pnl": net_pnl,
        "pnl_pct": pnl_pct,
        "r_multiple": r_multiple,
        "equity_after": equity_after,
        "return_on_equity": return_on_equity,
    }


@dataclass
class TradeRecord:
    trade_id: str
    symbol: str
    side: str
    timeframe: str = ""
    strategy_tag: str = ""
    status: str = "OPEN"
    open_time: str = ""
    close_time: str = ""
    entry_price: float = 0.0
    exit_price: float = 0.0
    qty: float = 0.0
    leverage: float = 0.0
    notional: float = 0.0
    gross_pnl: float = 0.0
    net_pnl: float = 0.0
    fee_open: float = 0.0
    fee_close: float = 0.0
    fees_total: float = 0.0
    total_cost: float = 0.0
    risk_amount: float = 0.0
    r_multiple: float = 0.0
    pnl_pct: float = 0.0
    equity_before: float = 0.0
    equity_after: float = 0.0
    return_on_equity: float = 0.0
    holding_seconds: float = 0.0
    holding_bars: int = 0
    exit_reason: str = ""
    notes: str = ""


class TradeLogger:
    def __init__(self, config: dict):
        self.config = config
        self.file_path = Path(config.get("paths", {}).get("trades_csv", "trades.csv"))
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        ensure_csv_schema(self.file_path)

    def log_trade(self, trade: dict) -> None:
        default_timeframe = str(self.config.get("timeframe", ""))
        default_strategy = str(self.config.get("strategy_profile", ""))

        row = _canonical_trade_row(
            trade,
            default_timeframe=default_timeframe,
            default_strategy_tag=default_strategy,
        )

        append_trade(self.file_path, row)
