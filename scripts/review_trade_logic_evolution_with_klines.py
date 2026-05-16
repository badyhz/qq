#!/usr/bin/env python3
"""Review trade logic evolution with Binance USD-M Futures klines.

This script is intentionally read-only with respect to trading systems. It reads a
trade CSV, fetches public Binance USD-M klines, computes heuristic trade-logic
features, and writes reports/charts. It does not read API keys and does not touch
order/execution code.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
import requests
from scripts.trade_logic_klines_fetch_common import (
    BINANCE_KLINES_URL,
    build_kline_request_params,
    normalize_interval,
    normalize_kline_rows,
    normalize_symbol,
)

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    HAS_MATPLOTLIB = True
except Exception as exc:  # pragma: no cover - environment dependent
    plt = None
    HAS_MATPLOTLIB = False
    MATPLOTLIB_ERROR = str(exc)
else:
    MATPLOTLIB_ERROR = ""

CSV_LOCAL_TZ = timezone(timedelta(hours=8))
KLINE_COLUMNS = [
    "open_time_ms",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "close_time_ms",
    "quote_asset_volume",
    "number_of_trades",
    "taker_buy_base_asset_volume",
    "taker_buy_quote_asset_volume",
    "ignore",
]
INTERVAL_WINDOWS = {
    "1m": (timedelta(minutes=60), timedelta(minutes=30)),
    "5m": (timedelta(hours=4), timedelta(hours=1)),
    "15m": (timedelta(hours=12), timedelta(hours=2)),
    "1h": (timedelta(days=3), timedelta(hours=6)),
}
INTERVAL_MS = {
    "1m": 60_000,
    "5m": 5 * 60_000,
    "15m": 15 * 60_000,
    "1h": 60 * 60_000,
}
PLAN_TAGS = {
    "planned_trend_follow",
    "planned_pullback_entry",
    "planned_breakout_entry",
    "planned_reversal_after_confirm",
    "good_exit",
    "controlled_loss",
}
IMPULSE_TAGS = {
    "impulse_chase_long",
    "impulse_chase_short",
    "countertrend_guess_top",
    "countertrend_guess_bottom",
    "revenge_trade",
    "overtrade_same_symbol",
    "range_noise_trade",
    "no_stop_loss",
    "late_exit",
    "profit_giveback",
}


@dataclass
class FieldMap:
    symbol: Optional[str] = None
    side: Optional[str] = None
    open_time: Optional[str] = None
    close_time: Optional[str] = None
    entry_price: Optional[str] = None
    exit_price: Optional[str] = None
    realized_pnl: Optional[str] = None
    quantity: Optional[str] = None
    fee: Optional[str] = None
    note: Optional[str] = None
    strategy: Optional[str] = None

    def missing_core(self) -> List[str]:
        missing = []
        for name in ["symbol", "open_time", "close_time", "entry_price", "exit_price"]:
            if getattr(self, name) is None:
                missing.append(name)
        return missing

    def as_dict(self) -> Dict[str, Optional[str]]:
        return self.__dict__.copy()


class ErrorLog:
    def __init__(self) -> None:
        self.messages: List[str] = []

    def add(self, msg: str) -> None:
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.messages.append(f"[{stamp}] {msg}")

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(self.messages) + ("\n" if self.messages else ""), encoding="utf-8")


ERRORS = ErrorLog()


def norm_col(name: Any) -> str:
    text = str(name).strip().lower()
    text = text.replace("（", "(").replace("）", ")")
    text = re.sub(r"[\s_\-./:()\[\]%]+", "", text)
    return text


def find_column(columns: Sequence[str], candidates: Sequence[str]) -> Optional[str]:
    normalized = {col: norm_col(col) for col in columns}
    candidate_norms = [norm_col(c) for c in candidates]
    for cand in candidate_norms:
        for col, ncol in normalized.items():
            if ncol == cand:
                return col
    for cand in candidate_norms:
        for col, ncol in normalized.items():
            if cand and cand in ncol:
                return col
    return None


def detect_fields(df: pd.DataFrame) -> FieldMap:
    cols = list(df.columns)
    return FieldMap(
        symbol=find_column(cols, ["symbol", "pair", "代币名称/币种名称/币对", "币种名称", "代币名称", "交易对", "币对", "币种", "标的", "品种", "contract", "合约"]),
        side=find_column(cols, ["side", "direction", "position_side", "position", "方向", "多空", "买卖", "开仓方向", "仓位方向"]),
        open_time=find_column(cols, ["open_time", "entry_time", "opened_at", "entry_at", "start_time", "开仓时间", "入场时间", "建仓时间", "开始时间", "已打开", "打开时间", "time", "时间"]),
        close_time=find_column(cols, ["close_time", "exit_time", "closed_at", "exit_at", "end_time", "平仓时间", "出场时间", "结束时间", "已关闭", "关闭时间", "close date", "平仓日期"]),
        entry_price=find_column(cols, ["entry_price", "open_price", "avg_entry_price", "开仓价", "入场价", "入场价格", "成交均价", "开仓均价", "entry"]),
        exit_price=find_column(cols, ["exit_price", "close_price", "avg_exit_price", "平仓价", "出场价", "平仓价格", "平均收盘价", "收盘价", "平仓均价", "exit"]),
        realized_pnl=find_column(cols, ["realized_pnl", "realizedpnl", "pnl", "profit", "盈亏", "结算盈亏", "已实现盈亏", "已实现损益", "收益", "PNL"]),
        quantity=find_column(cols, ["quantity", "qty", "amount", "size", "数量", "成交数量", "仓位数量", "持仓量", "已平仓量", "最大未平仓合约"]),
        fee=find_column(cols, ["fee", "commission", "手续费", "佣金"]),
        note=find_column(cols, ["note", "comment", "memo", "remark", "备注", "注释", "说明"]),
        strategy=find_column(cols, ["strategy", "source", "tag", "tags", "策略", "来源", "标签", "信号来源"]),
    )


def read_csv_auto(path: Path) -> pd.DataFrame:
    encodings = ["utf-8-sig", "utf-8", "gb18030", "gbk", "big5"]
    last_exc: Optional[Exception] = None
    for enc in encodings:
        try:
            return pd.read_csv(path, encoding=enc)
        except UnicodeDecodeError as exc:
            last_exc = exc
            continue
    if last_exc:
        raise last_exc
    return pd.read_csv(path)


def clean_number(value: Any) -> float:
    if pd.isna(value):
        return np.nan
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null", "--", "-"}:
        return np.nan
    text = text.replace(",", "")
    text = text.replace("USDT", "").replace("usd", "").replace("USD", "")
    text = text.replace("+", "")
    m = re.search(r"-?\d+(?:\.\d+)?", text)
    if not m:
        return np.nan
    try:
        return float(m.group(0))
    except ValueError:
        return np.nan


def parse_text_time_value(value: Any) -> pd.Timestamp:
    if pd.isna(value):
        return pd.NaT
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null", "--", "-"}:
        return pd.NaT
    has_tz = bool(re.search(r"(z|[+-]\d{2}:?\d{2})$", text, flags=re.IGNORECASE))
    formats = [
        "%y-%m-%d %H:%M:%S",
        "%y/%m/%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
    ]
    parsed = pd.NaT
    for fmt in formats:
        parsed = pd.to_datetime(text, format=fmt, errors="coerce", utc=has_tz)
        if pd.notna(parsed):
            break
    if pd.isna(parsed):
        parsed = pd.to_datetime(text, errors="coerce", utc=has_tz)
    if pd.isna(parsed):
        return pd.NaT
    if has_tz:
        return pd.Timestamp(parsed).tz_convert("UTC")
    return pd.Timestamp(parsed).tz_localize(CSV_LOCAL_TZ).tz_convert("UTC")


def parse_time_series(series: pd.Series) -> pd.Series:
    raw = series.copy()
    numeric = pd.to_numeric(raw, errors="coerce")
    parsed = pd.Series(pd.NaT, index=series.index, dtype="datetime64[ns, UTC]")
    if numeric.notna().any():
        ms_mask = numeric > 10_000_000_000
        sec_mask = numeric.between(1_000_000_000, 10_000_000_000)
        if ms_mask.any():
            parsed.loc[ms_mask] = pd.to_datetime(numeric.loc[ms_mask], unit="ms", utc=True, errors="coerce")
        if sec_mask.any():
            parsed.loc[sec_mask] = pd.to_datetime(numeric.loc[sec_mask], unit="s", utc=True, errors="coerce")
    text_parsed = raw.map(parse_text_time_value)
    parsed = parsed.fillna(text_parsed)
    return parsed


def normalize_symbol(value: Any) -> str:
    if pd.isna(value):
        return ""
    text = str(value).upper().strip()
    text = re.sub(r"\s+", "", text)
    text = text.replace("/", "").replace("-", "").replace("_", "")
    text = text.replace("PERPETUAL", "").replace("PERP", "")
    text = text.replace("USDⓈM", "").replace("USDM", "")
    quote_suffixes = ("USDT", "USDC", "BUSD", "FDUSD", "USD")
    if text and not text.endswith(quote_suffixes) and len(text) <= 8:
        text = f"{text}USDT"
    return text


def infer_direction(row: pd.Series, field_map: FieldMap) -> str:
    side_text = ""
    if field_map.side:
        side_text = str(row.get(field_map.side, "")).strip().lower()
    entry = clean_number(row.get(field_map.entry_price)) if field_map.entry_price else np.nan
    exitp = clean_number(row.get(field_map.exit_price)) if field_map.exit_price else np.nan
    pnl = clean_number(row.get(field_map.realized_pnl)) if field_map.realized_pnl else np.nan
    if any(x in side_text for x in ["long", "buy", "多", "做多", "开多"]):
        return "long"
    if any(x in side_text for x in ["short", "sell", "空", "做空", "开空"]):
        return "short"
    if not np.isnan(entry) and not np.isnan(exitp) and not np.isnan(pnl):
        price_move = exitp - entry
        if pnl * price_move >= 0:
            return "long"
        return "short"
    return "unknown"


def prepare_trades(df: pd.DataFrame, field_map: FieldMap, max_trades: Optional[int]) -> pd.DataFrame:
    out = pd.DataFrame(index=df.index)
    out["source_row"] = df.index + 2
    out["symbol"] = df[field_map.symbol].map(normalize_symbol) if field_map.symbol else ""
    out["open_time"] = parse_time_series(df[field_map.open_time]) if field_map.open_time else pd.NaT
    out["close_time"] = parse_time_series(df[field_map.close_time]) if field_map.close_time else pd.NaT
    out["entry_price"] = df[field_map.entry_price].map(clean_number) if field_map.entry_price else np.nan
    out["exit_price"] = df[field_map.exit_price].map(clean_number) if field_map.exit_price else np.nan
    out["realized_pnl"] = df[field_map.realized_pnl].map(clean_number) if field_map.realized_pnl else np.nan
    out["quantity"] = df[field_map.quantity].map(clean_number) if field_map.quantity else np.nan
    out["fee"] = df[field_map.fee].map(clean_number) if field_map.fee else np.nan
    out["note_text"] = ""
    if field_map.note:
        out["note_text"] = out["note_text"].astype(str) + " " + df[field_map.note].fillna("").astype(str)
    if field_map.strategy:
        out["note_text"] = out["note_text"].astype(str) + " " + df[field_map.strategy].fillna("").astype(str)
    out["direction"] = df.apply(lambda r: infer_direction(r, field_map), axis=1)
    out = out.sort_values("open_time", na_position="last").reset_index(drop=True)
    if max_trades and max_trades > 0 and len(out) > max_trades:
        out = out.tail(max_trades).reset_index(drop=True)
    return out


def evenly_sample(df: pd.DataFrame, count: int) -> pd.DataFrame:
    if count <= 0 or df.empty:
        return df.head(0)
    if len(df) <= count:
        return df
    positions = np.linspace(0, len(df) - 1, count).round().astype(int)
    positions = np.unique(positions)
    sampled = df.iloc[positions]
    if len(sampled) < count:
        missing = count - len(sampled)
        extra = df.drop(sampled.index).tail(missing)
        sampled = pd.concat([sampled, extra])
    return sampled.sort_values("open_time")


def select_trades_for_analysis(trades: pd.DataFrame, max_trades: Optional[int], recent_months: int) -> pd.DataFrame:
    if not max_trades or max_trades <= 0 or len(trades) <= max_trades:
        return trades.reset_index(drop=True)
    valid_times = trades["open_time"].dropna()
    if valid_times.empty:
        return evenly_sample(trades, max_trades).reset_index(drop=True)
    cutoff = valid_times.max() - pd.DateOffset(months=recent_months)
    recent = trades[trades["open_time"] >= cutoff]
    earlier = trades[trades["open_time"] < cutoff]
    if recent.empty or earlier.empty:
        return evenly_sample(trades, max_trades).reset_index(drop=True)

    recent_quota = min(len(recent), int(round(max_trades * 0.60)))
    earlier_quota = min(len(earlier), max_trades - recent_quota)
    spare = max_trades - recent_quota - earlier_quota
    if spare > 0:
        if len(recent) > recent_quota:
            add = min(spare, len(recent) - recent_quota)
            recent_quota += add
            spare -= add
        if spare > 0 and len(earlier) > earlier_quota:
            earlier_quota += min(spare, len(earlier) - earlier_quota)
    selected = pd.concat([evenly_sample(earlier, earlier_quota), evenly_sample(recent, recent_quota)], ignore_index=True)
    return selected.sort_values("open_time").reset_index(drop=True)


def to_ms(ts: pd.Timestamp) -> int:
    return int(ts.timestamp() * 1000)


def from_ms(ms: int) -> pd.Timestamp:
    return pd.to_datetime(ms, unit="ms", utc=True)


def day_bounds(day: pd.Timestamp) -> Tuple[pd.Timestamp, pd.Timestamp]:
    start = pd.Timestamp(day.date(), tz="UTC")
    return start, start + pd.Timedelta(days=1) - pd.Timedelta(milliseconds=1)


def date_range_days(start: pd.Timestamp, end: pd.Timestamp) -> Iterable[pd.Timestamp]:
    cur = pd.Timestamp(start.date(), tz="UTC")
    final = pd.Timestamp(end.date(), tz="UTC")
    while cur <= final:
        yield cur
        cur += pd.Timedelta(days=1)


def kline_cache_path(cache_root: Path, symbol: str, interval: str, day: pd.Timestamp) -> Path:
    return cache_root / symbol / interval / f"{day.strftime('%Y-%m-%d')}.csv"


def klines_to_df(rows: List[List[Any]]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(columns=KLINE_COLUMNS + ["open_time", "close_time"])
    df = pd.DataFrame(rows, columns=KLINE_COLUMNS)
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["open_time_ms"] = pd.to_numeric(df["open_time_ms"], errors="coerce").astype("Int64")
    df["close_time_ms"] = pd.to_numeric(df["close_time_ms"], errors="coerce").astype("Int64")
    df["open_time"] = pd.to_datetime(df["open_time_ms"], unit="ms", utc=True, errors="coerce")
    df["close_time"] = pd.to_datetime(df["close_time_ms"], unit="ms", utc=True, errors="coerce")
    df = df.dropna(subset=["open_time", "open", "high", "low", "close"])
    return df.sort_values("open_time").drop_duplicates("open_time").reset_index(drop=True)


def fetch_klines(symbol: str, interval: str, start: pd.Timestamp, end: pd.Timestamp, timeout: int = 15) -> pd.DataFrame:
    rows: List[List[Any]] = []
    symbol = normalize_symbol(symbol)
    interval = normalize_interval(interval, INTERVAL_MS.keys())
    start_ms = to_ms(start)
    end_ms = to_ms(end)
    step_ms = INTERVAL_MS[interval]
    cursor = start_ms
    while cursor <= end_ms:
        params = build_kline_request_params(
            symbol=symbol,
            interval=interval,
            start_ms=cursor,
            end_ms=end_ms,
            limit=1500,
        )
        try:
            resp = requests.get(BINANCE_KLINES_URL, params=params, timeout=timeout)
        except Exception as exc:
            raise RuntimeError(f"network error fetching {symbol} {interval}: {exc}") from exc
        if resp.status_code != 200:
            raise RuntimeError(f"Binance status {resp.status_code} for {symbol} {interval}: {resp.text[:300]}")
        batch = normalize_kline_rows(resp.json())
        if not batch:
            break
        rows.extend(batch)
        last_open = int(batch[-1][0])
        next_cursor = last_open + step_ms
        if next_cursor <= cursor:
            break
        cursor = next_cursor
        if len(batch) < 1500:
            break
        time.sleep(0.12)
    return klines_to_df(rows)


def load_day_klines(cache_root: Path, symbol: str, interval: str, day: pd.Timestamp) -> pd.DataFrame:
    path = kline_cache_path(cache_root, symbol, interval, day)
    if path.exists():
        try:
            df = pd.read_csv(path)
            if "open_time" in df.columns:
                df["open_time"] = pd.to_datetime(df["open_time"], utc=True, errors="coerce")
            if "close_time" in df.columns:
                df["close_time"] = pd.to_datetime(df["close_time"], utc=True, errors="coerce")
            return df.dropna(subset=["open_time"]).sort_values("open_time").reset_index(drop=True)
        except Exception as exc:
            ERRORS.add(f"cache read failed {path}: {exc}; refetching")
    start, end = day_bounds(day)
    try:
        df = fetch_klines(symbol, interval, start, end)
    except Exception as exc:
        ERRORS.add(str(exc))
        return pd.DataFrame(columns=KLINE_COLUMNS + ["open_time", "close_time"])
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        df.to_csv(path, index=False)
    except Exception as exc:
        ERRORS.add(f"cache write failed {path}: {exc}")
    time.sleep(0.08)
    return df


def get_klines(cache_root: Path, symbol: str, interval: str, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    parts = []
    for day in date_range_days(start, end):
        parts.append(load_day_klines(cache_root, symbol, interval, day))
    parts = [part for part in parts if not part.empty]
    if not parts:
        return pd.DataFrame(columns=KLINE_COLUMNS + ["open_time", "close_time"])
    df = pd.concat(parts, ignore_index=True)
    if df.empty:
        return df
    df["open_time"] = pd.to_datetime(df["open_time"], utc=True, errors="coerce")
    df = df.dropna(subset=["open_time"])
    mask = (df["open_time"] >= start) & (df["open_time"] <= end)
    return df.loc[mask].sort_values("open_time").drop_duplicates("open_time").reset_index(drop=True)


def pct(a: float, b: float) -> float:
    if b is None or np.isnan(b) or b == 0 or a is None or np.isnan(a):
        return np.nan
    return (a / b - 1.0) * 100.0


def close_before(df: pd.DataFrame, ts: pd.Timestamp) -> float:
    if df.empty:
        return np.nan
    sub = df[df["open_time"] <= ts]
    if sub.empty:
        return np.nan
    return float(sub.iloc[-1]["close"])


def close_after(df: pd.DataFrame, ts: pd.Timestamp) -> float:
    if df.empty:
        return np.nan
    sub = df[df["open_time"] >= ts]
    if sub.empty:
        return np.nan
    return float(sub.iloc[0]["close"])


def pre_return(df: pd.DataFrame, entry_time: pd.Timestamp, minutes: int) -> float:
    now = close_before(df, entry_time)
    before = close_before(df, entry_time - pd.Timedelta(minutes=minutes))
    return pct(now, before)


def pre_volatility(df: pd.DataFrame, entry_time: pd.Timestamp, minutes: int) -> float:
    sub = df[(df["open_time"] >= entry_time - pd.Timedelta(minutes=minutes)) & (df["open_time"] < entry_time)]
    if len(sub) < 3:
        return np.nan
    returns = sub["close"].pct_change().dropna()
    if returns.empty:
        return np.nan
    return float(returns.std() * math.sqrt(len(returns)) * 100.0)


def range_position(df: pd.DataFrame, entry_time: pd.Timestamp, entry_price: float, bars: int) -> float:
    sub = df[df["open_time"] < entry_time].tail(bars)
    if sub.empty or np.isnan(entry_price):
        return np.nan
    low = float(sub["low"].min())
    high = float(sub["high"].max())
    if high <= low:
        return np.nan
    return max(0.0, min(1.0, (entry_price - low) / (high - low)))


def trend_direction(df: pd.DataFrame, entry_time: pd.Timestamp, bars: int = 12, threshold_pct: float = 0.12) -> str:
    sub = df[df["open_time"] < entry_time].tail(bars)
    if len(sub) < max(4, bars // 3):
        return "unknown"
    change = pct(float(sub.iloc[-1]["close"]), float(sub.iloc[0]["close"]))
    if np.isnan(change):
        return "unknown"
    if change > threshold_pct:
        return "up"
    if change < -threshold_pct:
        return "down"
    return "range"


def direction_aligned(direction: str, trend: str) -> bool:
    return (direction == "long" and trend == "up") or (direction == "short" and trend == "down")


def favorable_pct(direction: str, entry_price: float, price: float) -> float:
    if np.isnan(entry_price) or entry_price == 0 or np.isnan(price):
        return np.nan
    if direction == "long":
        return (price / entry_price - 1.0) * 100.0
    if direction == "short":
        return (entry_price / price - 1.0) * 100.0
    return np.nan


def compute_mfe_mae(df_1m: pd.DataFrame, direction: str, entry_time: pd.Timestamp, close_time: pd.Timestamp, entry_price: float, qty: float) -> Dict[str, float]:
    result = {
        "mfe_pct": np.nan,
        "mae_pct": np.nan,
        "mfe_usdt": np.nan,
        "mae_usdt": np.nan,
        "mfe_mae_ratio": np.nan,
        "first_30m_mfe_pct": np.nan,
    }
    if df_1m.empty or direction not in {"long", "short"} or np.isnan(entry_price):
        return result
    if pd.isna(close_time) or close_time <= entry_time:
        close_time = entry_time + pd.Timedelta(minutes=30)
    hold = df_1m[(df_1m["open_time"] >= entry_time) & (df_1m["open_time"] <= close_time)]
    if hold.empty:
        return result
    if direction == "long":
        mfe_pct = (float(hold["high"].max()) / entry_price - 1.0) * 100.0
        mae_pct = (float(hold["low"].min()) / entry_price - 1.0) * 100.0
    else:
        mfe_pct = (entry_price / float(hold["low"].min()) - 1.0) * 100.0
        mae_pct = (entry_price / float(hold["high"].max()) - 1.0) * 100.0
    result["mfe_pct"] = max(0.0, mfe_pct)
    result["mae_pct"] = min(0.0, mae_pct)
    if not np.isnan(qty) and qty > 0:
        notional_per_pct = entry_price * qty / 100.0
        result["mfe_usdt"] = result["mfe_pct"] * notional_per_pct
        result["mae_usdt"] = result["mae_pct"] * notional_per_pct
    if abs(result["mae_pct"]) > 1e-9:
        result["mfe_mae_ratio"] = result["mfe_pct"] / abs(result["mae_pct"])
    first30 = hold[hold["open_time"] <= entry_time + pd.Timedelta(minutes=30)]
    if not first30.empty:
        if direction == "long":
            result["first_30m_mfe_pct"] = max(0.0, (float(first30["high"].max()) / entry_price - 1.0) * 100.0)
        else:
            result["first_30m_mfe_pct"] = max(0.0, (entry_price / float(first30["low"].min()) - 1.0) * 100.0)
    return result


def post_move(df_1m: pd.DataFrame, direction: str, close_time: pd.Timestamp, exit_price: float, minutes: int) -> float:
    if df_1m.empty or direction not in {"long", "short"} or pd.isna(close_time) or np.isnan(exit_price):
        return np.nan
    target = close_after(df_1m, close_time + pd.Timedelta(minutes=minutes))
    return favorable_pct(direction, exit_price, target)


def source_category(text: str) -> str:
    lowered = str(text).lower()
    if any(x in lowered for x in ["ai", "gpt", "chatgpt", "claude", "llm", "机器人", "ai辅助", "ai 分析"]):
        return "AI辅助交易"
    if any(x in lowered for x in ["感觉", "凭感觉", "冲动", "复仇", "随手", "乱", "手痒"]):
        return "凭感觉交易"
    if any(x in lowered for x in ["manual", "手动", "自主"]):
        return "手动交易"
    if str(text).strip():
        return "有标注但未归类"
    return "未标注交易"


def add_behavior_features(features: pd.DataFrame) -> pd.DataFrame:
    features = features.sort_values("open_time").reset_index(drop=True)
    features["is_same_day_consecutive"] = False
    features["prev_trade_pnl"] = np.nan
    features["prev_trade_result"] = "none"
    features["minutes_after_prev_loss"] = np.nan
    features["day_trade_number"] = 0
    features["day_pnl_before_entry"] = 0.0
    features["same_symbol_trades_prev_2h"] = 0
    day_counts: Dict[str, int] = {}
    day_pnl: Dict[str, float] = {}
    for i, row in features.iterrows():
        ot = row["open_time"]
        day = ot.strftime("%Y-%m-%d") if pd.notna(ot) else "unknown"
        features.at[i, "day_trade_number"] = day_counts.get(day, 0) + 1
        features.at[i, "day_pnl_before_entry"] = day_pnl.get(day, 0.0)
        day_counts[day] = day_counts.get(day, 0) + 1
        pnl = row.get("realized_pnl", np.nan)
        if not np.isnan(pnl):
            day_pnl[day] = day_pnl.get(day, 0.0) + float(pnl)
        if i > 0:
            prev = features.iloc[i - 1]
            features.at[i, "prev_trade_pnl"] = prev.get("realized_pnl", np.nan)
            features.at[i, "prev_trade_result"] = "win" if prev.get("realized_pnl", np.nan) > 0 else "loss" if prev.get("realized_pnl", np.nan) < 0 else "flat"
            if pd.notna(prev.get("open_time")) and pd.notna(ot):
                features.at[i, "is_same_day_consecutive"] = prev["open_time"].strftime("%Y-%m-%d") == ot.strftime("%Y-%m-%d")
            if prev.get("realized_pnl", np.nan) < 0 and pd.notna(prev.get("close_time")) and pd.notna(ot):
                features.at[i, "minutes_after_prev_loss"] = (ot - prev["close_time"]).total_seconds() / 60.0
        if pd.notna(ot):
            recent_same_symbol = features.iloc[:i]
            recent_same_symbol = recent_same_symbol[
                (recent_same_symbol["symbol"] == row["symbol"])
                & (recent_same_symbol["open_time"] >= ot - pd.Timedelta(hours=2))
                & (recent_same_symbol["open_time"] < ot)
            ]
            features.at[i, "same_symbol_trades_prev_2h"] = len(recent_same_symbol)
    return features


def score_and_tag(row: pd.Series) -> Tuple[List[str], Dict[str, float], str]:
    tags: List[str] = []
    direction = row.get("direction", "unknown")
    pnl = row.get("realized_pnl", np.nan)
    mae = row.get("mae_pct", np.nan)
    mfe = row.get("mfe_pct", np.nan)
    ratio = row.get("mfe_mae_ratio", np.nan)
    pos_1m = row.get("entry_pos_20x1m", np.nan)
    pos_5m = row.get("entry_pos_20x5m", np.nan)
    trend_5m = row.get("trend_5m", "unknown")
    trend_15m = row.get("trend_15m", "unknown")
    trend_1h = row.get("trend_1h", "unknown")
    aligned_15m = bool(row.get("aligned_15m", False))
    aligned_1h = bool(row.get("aligned_1h", False))
    sudden_up = bool(row.get("sudden_up_before_entry", False))
    sudden_down = bool(row.get("sudden_down_before_entry", False))
    duration_min = row.get("holding_minutes", np.nan)
    post30 = row.get("post_30m_move_pct", np.nan)
    exit_score = row.get("exit_quality_score", np.nan)

    near_high = (not np.isnan(pos_1m) and pos_1m >= 0.85) or (not np.isnan(pos_5m) and pos_5m >= 0.85)
    near_low = (not np.isnan(pos_1m) and pos_1m <= 0.15) or (not np.isnan(pos_5m) and pos_5m <= 0.15)

    if direction == "long" and sudden_up and near_high:
        tags.append("impulse_chase_long")
    if direction == "short" and sudden_down and near_low:
        tags.append("impulse_chase_short")
    if direction == "short" and trend_15m == "up" and near_high:
        tags.append("countertrend_guess_top")
    if direction == "long" and trend_15m == "down" and near_low:
        tags.append("countertrend_guess_bottom")
    if row.get("minutes_after_prev_loss", np.nan) >= 0 and row.get("minutes_after_prev_loss", np.nan) <= 45:
        tags.append("revenge_trade")
    if row.get("same_symbol_trades_prev_2h", 0) >= 2:
        tags.append("overtrade_same_symbol")
    if trend_5m == "range" and trend_15m == "range" and abs(row.get("pre_15m_return_pct", 0) or 0) < 0.25:
        tags.append("range_noise_trade")

    final_move_pct = favorable_pct(direction, row.get("entry_price", np.nan), row.get("exit_price", np.nan))
    if not np.isnan(pnl) and pnl < 0:
        if (not np.isnan(mae) and abs(mae) >= max(0.6, abs(final_move_pct) * 1.8 if not np.isnan(final_move_pct) else 0.6)) or (not np.isnan(duration_min) and duration_min > 120 and abs(mae) > 0.35):
            tags.append("no_stop_loss")
        if not np.isnan(duration_min) and duration_min > 45 and not np.isnan(row.get("first_30m_mfe_pct", np.nan)) and row.get("first_30m_mfe_pct", 0) < 0.12:
            tags.append("late_exit")
    if not np.isnan(mfe) and mfe > 0.35:
        if (not np.isnan(final_move_pct) and final_move_pct < mfe * 0.35) or (not np.isnan(pnl) and pnl <= 0):
            tags.append("profit_giveback")

    has_impulse = any(t in IMPULSE_TAGS for t in tags)
    if aligned_15m and aligned_1h and not has_impulse:
        tags.append("planned_trend_follow")
    if direction == "long" and trend_15m == "up" and not np.isnan(pos_5m) and 0.15 <= pos_5m <= 0.55 and not has_impulse:
        tags.append("planned_pullback_entry")
    if direction == "short" and trend_15m == "down" and not np.isnan(pos_5m) and 0.45 <= pos_5m <= 0.85 and not has_impulse:
        tags.append("planned_pullback_entry")
    if direction == "long" and trend_15m == "up" and near_high and not sudden_up:
        tags.append("planned_breakout_entry")
    if direction == "short" and trend_15m == "down" and near_low and not sudden_down:
        tags.append("planned_breakout_entry")
    if aligned_15m and trend_1h in {"range", "unknown"} and not has_impulse:
        tags.append("planned_reversal_after_confirm")
    if not np.isnan(exit_score) and exit_score >= 10:
        tags.append("good_exit")
    if not np.isnan(pnl) and pnl < 0 and not np.isnan(mae) and abs(mae) <= 0.45 and "late_exit" not in tags and "no_stop_loss" not in tags:
        tags.append("controlled_loss")
    if not tags:
        tags.append("unclear")

    trend_score = 0
    if aligned_15m:
        trend_score += 10
    elif trend_15m == "range":
        trend_score += 5
    if aligned_1h:
        trend_score += 10
    elif trend_1h == "range":
        trend_score += 5

    entry_score = 10
    if direction == "long":
        if sudden_up and near_high:
            entry_score -= 7
        if trend_15m == "up" and not np.isnan(pos_5m) and 0.15 <= pos_5m <= 0.65:
            entry_score += 7
        if near_low and trend_15m != "down":
            entry_score += 3
        if near_high and trend_15m == "down":
            entry_score -= 4
    elif direction == "short":
        if sudden_down and near_low:
            entry_score -= 7
        if trend_15m == "down" and not np.isnan(pos_5m) and 0.35 <= pos_5m <= 0.85:
            entry_score += 7
        if near_high and trend_15m != "up":
            entry_score += 3
        if near_low and trend_15m == "up":
            entry_score -= 4
    entry_score = max(0, min(20, entry_score))

    risk_score = 18
    if "no_stop_loss" in tags:
        risk_score -= 12
    if "late_exit" in tags:
        risk_score -= 6
    if "controlled_loss" in tags:
        risk_score += 5
    if not np.isnan(mae):
        if abs(mae) <= 0.25:
            risk_score += 3
        elif abs(mae) > 1.2:
            risk_score -= 6
    risk_score = max(0, min(25, risk_score))

    hold_score = 9
    if not np.isnan(ratio):
        if ratio >= 1.5:
            hold_score += 4
        elif ratio < 0.5:
            hold_score -= 3
    if "profit_giveback" in tags:
        hold_score -= 5
    if not np.isnan(duration_min) and duration_min > 30 and row.get("first_30m_mfe_pct", 0) < 0.12 and pnl < 0:
        hold_score -= 3
    hold_score = max(0, min(15, hold_score))

    if np.isnan(exit_score):
        exit_component = 7
    else:
        exit_component = max(0, min(15, float(exit_score)))

    discipline = 5
    for bad in ["revenge_trade", "overtrade_same_symbol", "range_noise_trade"]:
        if bad in tags:
            discipline -= 2
    discipline = max(0, min(5, discipline))

    components = {
        "score_trend": float(trend_score),
        "score_entry": float(entry_score),
        "score_risk": float(risk_score),
        "score_holding": float(hold_score),
        "score_exit": float(exit_component),
        "score_discipline": float(discipline),
    }
    quality = sum(components.values())
    components["quality_score"] = max(0.0, min(100.0, quality))

    plan_count = sum(1 for t in tags if t in PLAN_TAGS)
    impulse_count = sum(1 for t in tags if t in IMPULSE_TAGS)
    if plan_count > 0 and impulse_count == 0 and components["quality_score"] >= 60:
        inferred = "更像计划交易"
    elif impulse_count > 0 or components["quality_score"] <= 45:
        inferred = "更像冲动交易"
    else:
        inferred = "无法判断"
    return tags, components, inferred


def compute_exit_score(row: Dict[str, Any]) -> float:
    direction = row.get("direction", "unknown")
    entry = row.get("entry_price", np.nan)
    exitp = row.get("exit_price", np.nan)
    mfe = row.get("mfe_pct", np.nan)
    mae = row.get("mae_pct", np.nan)
    pnl = row.get("realized_pnl", np.nan)
    final_move = favorable_pct(direction, entry, exitp)
    post30 = row.get("post_30m_move_pct", np.nan)
    score = 8.0
    if not np.isnan(mfe) and mfe > 0.05 and not np.isnan(final_move):
        capture = final_move / mfe
        if capture >= 0.65:
            score += 4
        elif capture >= 0.35:
            score += 1
        else:
            score -= 3
    if not np.isnan(post30):
        if post30 > 0.3:
            score -= 3  # Closed before substantial continuation.
        elif post30 < -0.25:
            score += 2  # Exit avoided reversal.
    if not np.isnan(pnl) and pnl < 0 and not np.isnan(mae) and abs(mae) > 0.8:
        score -= 2
    if not np.isnan(pnl) and pnl < 0 and not np.isnan(mae) and abs(mae) <= 0.35:
        score += 2
    return max(0.0, min(15.0, score))


def compute_trade_features(trades: pd.DataFrame, cache_root: Path) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    for idx, trade in trades.iterrows():
        symbol = trade.get("symbol", "")
        entry_time = trade.get("open_time")
        close_time = trade.get("close_time")
        entry_price = trade.get("entry_price", np.nan)
        exit_price = trade.get("exit_price", np.nan)
        direction = trade.get("direction", "unknown")
        base: Dict[str, Any] = trade.to_dict()
        base["trade_id"] = idx + 1
        base["holding_minutes"] = np.nan
        base["kline_status"] = "ok"
        if pd.notna(entry_time) and pd.notna(close_time):
            base["holding_minutes"] = max(0.0, (close_time - entry_time).total_seconds() / 60.0)
        if not symbol or pd.isna(entry_time) or pd.isna(close_time) or np.isnan(entry_price) or np.isnan(exit_price):
            base["kline_status"] = "missing_required_trade_fields"
            base["logic_tags"] = "insufficient_kline_data"
            base["inferred_logic_group"] = "无法判断"
            base["quality_score"] = np.nan
            rows.append(base)
            continue

        klines: Dict[str, pd.DataFrame] = {}
        for interval, (pre, post) in INTERVAL_WINDOWS.items():
            start = entry_time - pre
            end = close_time + post
            df = get_klines(cache_root, symbol, interval, start, end)
            klines[interval] = df
            if df.empty:
                ERRORS.add(f"empty kline data: trade_id={idx + 1} symbol={symbol} interval={interval}")
        if any(klines[x].empty for x in ["1m", "5m", "15m"]):
            base["kline_status"] = "partial_or_empty_kline_data"

        df_1m = klines["1m"]
        df_5m = klines["5m"]
        df_15m = klines["15m"]
        df_1h = klines["1h"]

        base["pre_5m_return_pct"] = pre_return(df_1m, entry_time, 5)
        base["pre_15m_return_pct"] = pre_return(df_1m, entry_time, 15)
        base["pre_60m_return_pct"] = pre_return(df_1m, entry_time, 60)
        base["pre_15m_volatility_pct"] = pre_volatility(df_1m, entry_time, 15)
        base["pre_60m_volatility_pct"] = pre_volatility(df_1m, entry_time, 60)
        sudden_threshold = max(0.45, (base["pre_15m_volatility_pct"] if not np.isnan(base["pre_15m_volatility_pct"]) else 0.25) * 1.5)
        base["sudden_up_before_entry"] = bool(base["pre_5m_return_pct"] > sudden_threshold or base["pre_15m_return_pct"] > sudden_threshold * 1.5)
        base["sudden_down_before_entry"] = bool(base["pre_5m_return_pct"] < -sudden_threshold or base["pre_15m_return_pct"] < -sudden_threshold * 1.5)
        base["entry_pos_20x1m"] = range_position(df_1m, entry_time, entry_price, 20)
        base["entry_pos_20x5m"] = range_position(df_5m, entry_time, entry_price, 20)
        base["near_local_high"] = bool((base["entry_pos_20x1m"] >= 0.85 if not np.isnan(base["entry_pos_20x1m"]) else False) or (base["entry_pos_20x5m"] >= 0.85 if not np.isnan(base["entry_pos_20x5m"]) else False))
        base["near_local_low"] = bool((base["entry_pos_20x1m"] <= 0.15 if not np.isnan(base["entry_pos_20x1m"]) else False) or (base["entry_pos_20x5m"] <= 0.15 if not np.isnan(base["entry_pos_20x5m"]) else False))
        base["trend_5m"] = trend_direction(df_5m, entry_time, bars=12, threshold_pct=0.16)
        base["trend_15m"] = trend_direction(df_15m, entry_time, bars=12, threshold_pct=0.22)
        base["trend_1h"] = trend_direction(df_1h, entry_time, bars=24, threshold_pct=0.5)
        base["aligned_15m"] = direction_aligned(direction, base["trend_15m"])
        base["aligned_1h"] = direction_aligned(direction, base["trend_1h"])

        base.update(compute_mfe_mae(df_1m, direction, entry_time, close_time, entry_price, trade.get("quantity", np.nan)))
        base["mae_much_larger_than_final_loss"] = False
        final_move_pct = favorable_pct(direction, entry_price, exit_price)
        if not np.isnan(base["mae_pct"]) and not np.isnan(final_move_pct):
            base["mae_much_larger_than_final_loss"] = bool(final_move_pct < 0 and abs(base["mae_pct"]) > abs(final_move_pct) * 1.8)
        base["profit_giveback_flag"] = bool(not np.isnan(base["mfe_pct"]) and not np.isnan(final_move_pct) and base["mfe_pct"] > 0.35 and final_move_pct < base["mfe_pct"] * 0.35)
        base["held_after_adverse_expansion"] = bool(not np.isnan(base["mae_pct"]) and base["mae_pct"] < -0.5 and base["holding_minutes"] > 30)
        base["held_30m_without_profit"] = bool(base["holding_minutes"] > 30 and (np.isnan(base["first_30m_mfe_pct"]) or base["first_30m_mfe_pct"] < 0.12))

        base["post_5m_move_pct"] = post_move(df_1m, direction, close_time, exit_price, 5)
        base["post_15m_move_pct"] = post_move(df_1m, direction, close_time, exit_price, 15)
        base["post_30m_move_pct"] = post_move(df_1m, direction, close_time, exit_price, 30)
        base["post_5m_continues_original_direction"] = bool(base["post_5m_move_pct"] > 0.15 if not np.isnan(base["post_5m_move_pct"]) else False)
        base["post_15m_continues_original_direction"] = bool(base["post_15m_move_pct"] > 0.2 if not np.isnan(base["post_15m_move_pct"]) else False)
        base["post_30m_continues_original_direction"] = bool(base["post_30m_move_pct"] > 0.3 if not np.isnan(base["post_30m_move_pct"]) else False)
        base["quick_reverse_after_exit"] = bool(base["post_15m_move_pct"] < -0.25 if not np.isnan(base["post_15m_move_pct"]) else False)
        base["early_take_profit"] = bool((trade.get("realized_pnl", np.nan) > 0) and base["post_30m_continues_original_direction"])
        base["late_stop_loss"] = bool((trade.get("realized_pnl", np.nan) < 0) and base["held_30m_without_profit"] and base["held_after_adverse_expansion"])
        base["exit_quality_score"] = compute_exit_score(base)
        rows.append(base)

    features = pd.DataFrame(rows)
    if not features.empty:
        features = add_behavior_features(features)
        tag_rows = []
        for _, row in features.iterrows():
            if row.get("logic_tags") == "insufficient_kline_data":
                tag_rows.append(("insufficient_kline_data", {}, "无法判断"))
                continue
            tags, components, inferred = score_and_tag(row)
            tag_rows.append((";".join(dict.fromkeys(tags)), components, inferred))
        for i, (tags, components, inferred) in enumerate(tag_rows):
            features.at[i, "logic_tags"] = tags
            features.at[i, "inferred_logic_group"] = inferred
            for key, value in components.items():
                features.at[i, key] = value
        features["source_category"] = features["note_text"].map(source_category) if "note_text" in features else "未标注交易"
    return features


def has_tag(series_value: Any, tag: str) -> bool:
    return tag in str(series_value).split(";")


def any_tag(series_value: Any, tags: set) -> bool:
    values = set(str(series_value).split(";"))
    return bool(values & tags)


def metrics_for(df: pd.DataFrame, label: str) -> Dict[str, Any]:
    if df.empty:
        return {
            "period": label,
            "trade_count": 0,
            "total_pnl": 0.0,
            "win_rate": np.nan,
            "avg_pnl": np.nan,
            "avg_quality_score": np.nan,
            "trend_aligned_ratio": np.nan,
            "planned_tag_ratio": np.nan,
            "impulse_tag_ratio": np.nan,
            "no_stop_loss_ratio": np.nan,
            "revenge_trade_ratio": np.nan,
            "overtrade_ratio": np.nan,
            "avg_mae_pct": np.nan,
            "avg_abs_mae_pct": np.nan,
            "avg_mae_usdt": np.nan,
            "avg_mfe_mae_ratio": np.nan,
            "avg_exit_quality_score": np.nan,
        }
    tags = df["logic_tags"].fillna("")
    return {
        "period": label,
        "trade_count": int(len(df)),
        "total_pnl": float(df["realized_pnl"].sum(skipna=True)) if "realized_pnl" in df else np.nan,
        "win_rate": float((df["realized_pnl"] > 0).mean()) if "realized_pnl" in df else np.nan,
        "avg_pnl": float(df["realized_pnl"].mean(skipna=True)) if "realized_pnl" in df else np.nan,
        "avg_quality_score": float(df["quality_score"].mean(skipna=True)) if "quality_score" in df else np.nan,
        "trend_aligned_ratio": float((df.get("aligned_15m", False) | df.get("aligned_1h", False)).mean()) if "aligned_15m" in df and "aligned_1h" in df else np.nan,
        "planned_tag_ratio": float(tags.map(lambda x: any_tag(x, PLAN_TAGS)).mean()),
        "impulse_tag_ratio": float(tags.map(lambda x: any_tag(x, IMPULSE_TAGS)).mean()),
        "no_stop_loss_ratio": float(tags.map(lambda x: has_tag(x, "no_stop_loss")).mean()),
        "revenge_trade_ratio": float(tags.map(lambda x: has_tag(x, "revenge_trade")).mean()),
        "overtrade_ratio": float(tags.map(lambda x: has_tag(x, "overtrade_same_symbol")).mean()),
        "avg_mae_pct": float(df["mae_pct"].mean(skipna=True)) if "mae_pct" in df else np.nan,
        "avg_abs_mae_pct": float(df["mae_pct"].abs().mean(skipna=True)) if "mae_pct" in df else np.nan,
        "avg_mae_usdt": float(df["mae_usdt"].mean(skipna=True)) if "mae_usdt" in df else np.nan,
        "avg_mfe_mae_ratio": float(df["mfe_mae_ratio"].replace([np.inf, -np.inf], np.nan).mean(skipna=True)) if "mfe_mae_ratio" in df else np.nan,
        "avg_exit_quality_score": float(df["exit_quality_score"].mean(skipna=True)) if "exit_quality_score" in df else np.nan,
    }


def build_periods(features: pd.DataFrame, recent_months: int) -> Tuple[pd.DataFrame, Dict[str, pd.DataFrame], pd.Timestamp, pd.Timestamp]:
    valid_times = features["open_time"].dropna()
    if valid_times.empty:
        cutoff_recent = pd.Timestamp.now(tz="UTC") - pd.DateOffset(months=recent_months)
        cutoff_month = pd.Timestamp.now(tz="UTC") - pd.DateOffset(months=1)
    else:
        latest = valid_times.max()
        cutoff_recent = latest - pd.DateOffset(months=recent_months)
        cutoff_month = latest - pd.DateOffset(months=1)
    recent = features[features["open_time"] >= cutoff_recent]
    earlier = features[features["open_time"] < cutoff_recent]
    periods = {
        "全部交易": features,
        "最近两个月交易": recent,
        "最近一个月交易": features[features["open_time"] >= cutoff_month],
        "更早交易": earlier,
        "最近两个月中的盈利交易": recent[recent["realized_pnl"] > 0],
        "最近两个月中的亏损交易": recent[recent["realized_pnl"] < 0],
    }
    period_df = pd.DataFrame([metrics_for(df, label) for label, df in periods.items()])
    return period_df, periods, cutoff_recent, cutoff_month


def build_logic_summary(features: pd.DataFrame, has_source_fields: bool) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    if has_source_fields:
        group_col = "source_category"
    else:
        group_col = "inferred_logic_group"
    for name, group in features.groupby(group_col, dropna=False):
        m = metrics_for(group, str(name))
        m["comparison_type"] = "AI辅助/凭感觉字段" if has_source_fields else "K线结构推断"
        rows.append(m)
    return pd.DataFrame(rows)


def pick_top_examples(features: pd.DataFrame, periods: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    examples: List[pd.DataFrame] = []

    def add(category: str, df: pd.DataFrame, sort_cols: List[str], ascending: List[bool], n: int = 5) -> None:
        if df.empty:
            return
        tmp = df.copy()
        tmp["case_category"] = category
        tmp = tmp.sort_values(sort_cols, ascending=ascending, na_position="last").head(n)
        examples.append(tmp)

    early = periods.get("更早交易", pd.DataFrame())
    recent = periods.get("最近两个月交易", pd.DataFrame())
    if not features.empty:
        features = features.copy()
        features["impulse_tag_count"] = features["logic_tags"].fillna("").map(lambda x: sum(1 for t in str(x).split(";") if t in IMPULSE_TAGS))
        features["plan_tag_count"] = features["logic_tags"].fillna("").map(lambda x: sum(1 for t in str(x).split(";") if t in PLAN_TAGS))
        early = features[features["open_time"] < recent["open_time"].min()] if not recent.empty else pd.DataFrame()
        if "case_category" in early:
            early = early.drop(columns=["case_category"])
        recent = features.loc[recent.index] if not recent.empty else recent
    add("早期最典型的冲动交易", early[early["logic_tags"].fillna("").map(lambda x: any_tag(x, IMPULSE_TAGS))] if not early.empty else early, ["impulse_tag_count", "quality_score"], [False, True])
    add("早期最典型的无止损交易", early[early["logic_tags"].fillna("").map(lambda x: has_tag(x, "no_stop_loss"))] if not early.empty else early, ["mae_pct", "quality_score"], [True, True])
    add("最近两个月最典型的计划交易", recent[recent["inferred_logic_group"].eq("更像计划交易")] if not recent.empty else recent, ["plan_tag_count", "quality_score"], [False, False])
    add("最近两个月最典型的冲动交易", recent[recent["logic_tags"].fillna("").map(lambda x: any_tag(x, IMPULSE_TAGS))] if not recent.empty else recent, ["impulse_tag_count", "quality_score"], [False, True])
    add("最近两个月最值得表扬的交易", recent, ["quality_score", "realized_pnl"], [False, False])
    add("最近两个月最需要警惕的交易", recent, ["quality_score", "realized_pnl"], [True, True])
    add("最大亏损交易", features[features["realized_pnl"].notna()] if not features.empty else features, ["realized_pnl"], [True], 5)
    add("最大MAE交易", features[features["mae_pct"].notna()] if not features.empty and "mae_pct" in features else features, ["mae_pct"], [True], 5)
    if not examples:
        return pd.DataFrame()
    out = pd.concat(examples, ignore_index=True)
    keep = [
        "case_category",
        "trade_id",
        "source_row",
        "symbol",
        "direction",
        "open_time",
        "close_time",
        "holding_minutes",
        "entry_price",
        "exit_price",
        "realized_pnl",
        "mae_pct",
        "mfe_pct",
        "mfe_mae_ratio",
        "quality_score",
        "exit_quality_score",
        "logic_tags",
        "inferred_logic_group",
        "source_category",
        "kline_status",
    ]
    keep = [c for c in keep if c in out.columns]
    return out[keep].drop_duplicates(["case_category", "trade_id"])


def safe_file_part(text: Any) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", str(text))[:120].strip("_")


def plot_trade_charts(examples: pd.DataFrame, cache_root: Path, chart_dir: Path, max_charts: int) -> List[str]:
    chart_paths: List[str] = []
    if not HAS_MATPLOTLIB:
        ERRORS.add(f"matplotlib unavailable; charts skipped: {MATPLOTLIB_ERROR}")
        return chart_paths
    chart_dir.mkdir(parents=True, exist_ok=True)
    selected = examples.drop_duplicates("trade_id").head(max_charts) if not examples.empty else examples
    for _, row in selected.iterrows():
        symbol = row.get("symbol", "")
        entry_time = row.get("open_time")
        close_time = row.get("close_time")
        if not symbol or pd.isna(entry_time) or pd.isna(close_time):
            continue
        start = entry_time - pd.Timedelta(minutes=60)
        end = close_time + pd.Timedelta(minutes=30)
        df = get_klines(cache_root, symbol, "1m", start, end)
        if df.empty:
            continue
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.plot(df["open_time"], df["close"], linewidth=1.2, label="1m close")
        ax.scatter([entry_time], [row.get("entry_price", np.nan)], color="green", s=70, marker="^", label="entry", zorder=5)
        ax.scatter([close_time], [row.get("exit_price", np.nan)], color="red", s=70, marker="v", label="exit", zorder=5)
        title = (
            f"{symbol} {row.get('direction', '')} {entry_time.strftime('%Y-%m-%d %H:%M')} "
            f"pnl={row.get('realized_pnl', np.nan):.2f} MAE={row.get('mae_pct', np.nan):.2f}% "
            f"MFE={row.get('mfe_pct', np.nan):.2f}% score={row.get('quality_score', np.nan):.1f}\n"
            f"{row.get('logic_tags', '')}"
        )
        ax.set_title(title, fontsize=10)
        ax.set_xlabel("UTC time")
        ax.set_ylabel("price")
        ax.grid(alpha=0.25)
        ax.legend(loc="best")
        fig.autofmt_xdate()
        filename = f"trade_{int(row.get('trade_id', 0)):04d}_{safe_file_part(row.get('case_category', 'case'))}_{safe_file_part(symbol)}.png"
        path = chart_dir / filename
        fig.tight_layout()
        fig.savefig(path, dpi=150)
        plt.close(fig)
        chart_paths.append(str(path))
    return chart_paths


def clear_chart_dir(chart_dir: Path) -> None:
    chart_dir.mkdir(parents=True, exist_ok=True)
    for path in chart_dir.glob("*.png"):
        try:
            path.unlink()
        except Exception as exc:
            ERRORS.add(f"failed to remove old chart {path}: {exc}")


def fmt_num(value: Any, digits: int = 2, pct_style: bool = False) -> str:
    try:
        if pd.isna(value):
            return "N/A"
        f = float(value)
    except Exception:
        return str(value)
    if pct_style:
        return f"{f * 100:.1f}%"
    return f"{f:.{digits}f}"


def md_table(df: pd.DataFrame, columns: Optional[List[str]] = None) -> str:
    if df.empty:
        return "无数据\n"
    view = df[columns].copy() if columns else df.copy()
    for col in view.columns:
        if pd.api.types.is_float_dtype(view[col]):
            view[col] = view[col].map(lambda x: "" if pd.isna(x) else f"{x:.4f}")
    return view.to_markdown(index=False)


def compare_statement(period_df: pd.DataFrame, metric: str, better_high: bool = True) -> str:
    try:
        recent = float(period_df.loc[period_df["period"] == "最近两个月交易", metric].iloc[0])
        earlier = float(period_df.loc[period_df["period"] == "更早交易", metric].iloc[0])
    except Exception:
        return "数据不足，无法比较"
    if np.isnan(recent) or np.isnan(earlier):
        return "数据不足，无法比较"
    improved = recent > earlier if better_high else recent < earlier
    if improved:
        return f"改善：最近两个月 {recent:.4f}，更早阶段 {earlier:.4f}"
    if recent == earlier:
        return f"基本持平：最近两个月 {recent:.4f}，更早阶段 {earlier:.4f}"
    return f"未改善：最近两个月 {recent:.4f}，更早阶段 {earlier:.4f}"


def generate_summary(
    path: Path,
    features: pd.DataFrame,
    period_df: pd.DataFrame,
    logic_summary: pd.DataFrame,
    top_examples: pd.DataFrame,
    chart_paths: List[str],
    field_map: FieldMap,
    original_columns: Sequence[str],
    missing_fields: List[str],
    has_source_fields: bool,
    cutoff_recent: pd.Timestamp,
    recent_months: int,
    original_trade_count: int,
) -> None:
    if features.empty:
        start = end = "N/A"
    else:
        start = str(features["open_time"].min())
        end = str(features["open_time"].max())
    recent_stmt = compare_statement(period_df, "avg_quality_score", True)
    trend_stmt = compare_statement(period_df, "trend_aligned_ratio", True)
    impulse_stmt = compare_statement(period_df, "impulse_tag_ratio", False)
    nostop_stmt = compare_statement(period_df, "no_stop_loss_ratio", False)
    revenge_stmt = compare_statement(period_df, "revenge_trade_ratio", False)
    overtrade_stmt = compare_statement(period_df, "overtrade_ratio", False)
    mae_stmt = compare_statement(period_df, "avg_abs_mae_pct", False)
    ratio_stmt = compare_statement(period_df, "avg_mfe_mae_ratio", True)
    exit_stmt = compare_statement(period_df, "avg_exit_quality_score", True)

    direct_or_inferred = (
        "CSV 中识别到备注/策略/来源字段，因此 AI 辅助 vs 凭感觉部分优先使用字段文本归类。"
        if has_source_fields
        else "由于 CSV 未标注是否 AI 辅助，因此无法直接验证 AI 辅助效果，只能用 K 线结构和行为特征做间接推断。"
    )
    source_section_title = "AI 辅助 vs 凭感觉" if has_source_fields else "计划型 vs 冲动型"

    top_lines = []
    if not top_examples.empty:
        for _, row in top_examples.head(30).iterrows():
            top_lines.append(
                f"- {row.get('case_category')}: trade_id={row.get('trade_id')} {row.get('symbol')} {row.get('direction')} "
                f"pnl={fmt_num(row.get('realized_pnl'))} score={fmt_num(row.get('quality_score'), 1)} tags={row.get('logic_tags')}"
            )
    else:
        top_lines.append("- 无足够数据生成典型案例。")

    chart_lines = [f"- {p}" for p in chart_paths[:20]] if chart_paths else ["- 未生成图表；可能原因是 matplotlib 缺失、CSV 缺失或 K 线不足。"]

    columns_info = ", ".join(map(str, original_columns))
    missing_info = "无" if not missing_fields else ", ".join(missing_fields)
    field_info = json.dumps(field_map.as_dict(), ensure_ascii=False, indent=2)

    summary = f"""# 交易逻辑演变 K 线复盘报告

## 1. 结论先行
- 最近两个月交易质量评分对比：{recent_stmt}。
- 最近两个月顺势交易比例对比：{trend_stmt}。
- 最近两个月冲动追单/冲动标签比例对比：{impulse_stmt}。
- 最近两个月 no_stop_loss 比例对比：{nostop_stmt}。
- 最近两个月 revenge_trade 比例对比：{revenge_stmt}。
- 最近两个月 overtrade_same_symbol 比例对比：{overtrade_stmt}。
- 最近两个月平均 MAE 绝对值对比：{mae_stmt}。数值越低通常代表浮亏控制越好。
- 最近两个月 MFE/MAE 对比：{ratio_stmt}。
- 最近两个月出场质量对比：{exit_stmt}。
- {direct_or_inferred}
- 本评分是启发式复盘工具，不是真实预测模型，也不能证明某笔交易的真实心理动机。

## 2. 数据范围与方法说明
- 分析交易数：{len(features)}。
- 原始 CSV 交易数：{original_trade_count}。如果 `--max-trades` 小于原始交易数，脚本会跨时间段抽样，避免只取最近记录而失去“更早交易”对照组。
- 覆盖时间：{start} 至 {end}。
- 最近两个月切分口径：以 CSV 中最新开仓时间为锚点，向前 {recent_months} 个月；切分点为 {cutoff_recent}。
- K 线周期：1m、5m、15m、1h，来自 Binance USD-M Futures 公共接口 `/fapi/v1/klines`。
- K 线缓存目录：`data/cache/klines/{{symbol}}/{{interval}}/`。
- 字段识别结果：
```json
{field_info}
```
- 未识别核心字段：{missing_info}。
- CSV 原始列名：{columns_info}。
- 直接数据：成交时间、方向、价格、盈亏、数量、手续费、备注/来源字段。
- K 线结构推断：顺势程度、追单、摸顶摸底、无止损/晚止损、计划型/冲动型标签、质量评分。
- 如果 quantity 缺失，MFE/MAE 的 USDT 口径无法精确计算，报告使用价格百分比近似。

## 3. 早期交易逻辑画像
- 早期画像根据“更早交易”阶段的标签、顺势比例、MAE、MFE/MAE、出场质量综合判断。
- 是否追涨杀跌：查看 `impulse_chase_long`、`impulse_chase_short` 以及入场前急涨急跌字段。
- 是否逆势摸顶摸底：查看 `countertrend_guess_top`、`countertrend_guess_bottom` 和 15m/1h 趋势对齐字段。
- 是否高频反复：查看 `overtrade_same_symbol`、当日第几笔交易、同币种 2 小时内重复交易次数。
- 是否没有止损：查看 `no_stop_loss`、`late_exit`、MAE、持仓超过 30 分钟仍未盈利。
- 是否短线抢波动：查看持仓时长、震荡区间标签 `range_noise_trade`、出场后是否继续朝原方向走。

## 4. 最近两个月交易逻辑画像
- 是否更顺势：{trend_stmt}。
- 是否更会等位置：参考平均质量评分、计划型标签比例、入场位置分数。
- 是否更少追单：{impulse_stmt}。
- 是否止损更及时：{nostop_stmt}；{exit_stmt}。
- 是否仍会情绪化：{revenge_stmt}；{overtrade_stmt}。
- 如果最近两个月表现更差，优先查看 `top_examples.csv` 中“最近两个月最需要警惕的交易”和对应图表。

## 5. 以前 vs 最近两个月：量化对比
{md_table(period_df, ['period','trade_count','total_pnl','win_rate','avg_pnl','avg_quality_score','trend_aligned_ratio','planned_tag_ratio','impulse_tag_ratio','no_stop_loss_ratio','revenge_trade_ratio','overtrade_ratio','avg_mae_pct','avg_abs_mae_pct','avg_mfe_mae_ratio','avg_exit_quality_score'])}

## 6. {source_section_title}
- {direct_or_inferred}
{md_table(logic_summary)}

## 7. 我的进步点
- 若最近两个月平均质量评分上升，说明交易不只是盈亏改善，而是顺势、入场、风险控制、出场和纪律的综合结构改善。
- 若顺势比例上升，说明更少在 15m/1h 主方向反着猜。
- 若冲动标签比例下降，说明追涨杀跌、噪音区间乱开仓和短时间复仇交易减少。
- 若 no_stop_loss / late_exit 下降，说明止损意识或退出纪律改善。
- 若 MFE/MAE 上升，说明同样承受浮亏时，能换来更大的浮盈空间。
- 若出场质量评分上升，说明不再只是靠入场，退出也更像计划的一部分。

## 8. 我的退步点或仍未解决的问题
- 如果最近两个月质量评分没有高于更早阶段，说明“看起来更谨慎”没有转化为 K 线结构上的优势。
- 如果冲动标签仍高，说明 AI 分析或计划没有阻断实际执行时的追单/复仇行为。
- 如果 no_stop_loss 或 late_exit 仍高，最大问题不是方向判断，而是错误后不及时承认。
- 如果 overtrade 仍高，说明同一币种短时间反复交易仍在放大噪音和手续费影响。
- 如果出场后 30m 经常继续朝原方向走，说明止盈过早或没有分批/跟踪出场计划。
- 如果盈利后回吐标签多，说明持仓管理仍弱于入场分析。

## 9. 最典型案例
{chr(10).join(top_lines)}

图表路径：
{chr(10).join(chart_lines)}

## 10. 给我的下一步训练建议
- 继续保留：质量评分高且带 `planned_trend_follow` / `planned_pullback_entry` / `controlled_loss` 的做法，把这些案例作为模板。
- 必须禁止：`revenge_trade`、`overtrade_same_symbol`、`impulse_chase_long`、`impulse_chase_short` 同时出现时禁止开仓。
- AI 应重点帮你判断：15m/1h 是否顺势、开仓价是否贴近局部高低点、入场前是否急涨急跌、如果错了 protective stop 应放在哪里。
- 不准凭感觉交易：上一笔亏损后 45 分钟内、同币种 2 小时内已交易 2 次以上、5m/15m 都是震荡且没有突破确认、入场前 5-15 分钟已经急涨急跌。
- 可以自己交易：趋势清晰、回踩位置合理、MAE 预算明确、平仓条件在开仓前写清楚的交易。
- 是否应该先做 protective_stop_guard：如果 `no_stop_loss` 或 `late_exit` 在最近两个月仍高于 10%-15%，建议优先做；这比继续优化入场信号更直接降低灾难性回撤。

"""
    path.write_text(summary, encoding="utf-8")


def write_missing_input_summary(output_dir: Path, trades_csv: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "summary.md").write_text(
        f"""# 交易逻辑演变 K 线复盘报告

## 输入文件缺失
`{trades_csv}` 不存在。

请把 Binance Futures 成交记录 CSV 放到：

`data/trades/trades.csv`

本次没有读取替代文件，也没有编造交易数据。
""",
        encoding="utf-8",
    )
    pd.DataFrame().to_csv(output_dir / "trade_features.csv", index=False)
    pd.DataFrame().to_csv(output_dir / "period_comparison.csv", index=False)
    pd.DataFrame().to_csv(output_dir / "logic_tags_summary.csv", index=False)
    pd.DataFrame().to_csv(output_dir / "top_examples.csv", index=False)
    (output_dir / "charts").mkdir(parents=True, exist_ok=True)
    ERRORS.add(f"input CSV missing: {trades_csv}")
    ERRORS.write(output_dir / "error_log.txt")


def main() -> int:
    parser = argparse.ArgumentParser(description="Review trade logic evolution with Binance USD-M Futures klines.")
    parser.add_argument("--trades-csv", default="data/trades/trades.csv")
    parser.add_argument("--output-dir", default="reports/trade_logic_evolution")
    parser.add_argument("--max-trades", type=int, default=300)
    parser.add_argument("--recent-months", type=int, default=2)
    parser.add_argument("--top-charts", type=int, default=60)
    args = parser.parse_args()

    trades_csv = Path(args.trades_csv)
    output_dir = Path(args.output_dir)
    cache_root = Path("data/cache/klines")
    chart_dir = output_dir / "charts"
    output_dir.mkdir(parents=True, exist_ok=True)
    chart_dir.mkdir(parents=True, exist_ok=True)
    clear_chart_dir(chart_dir)

    if not trades_csv.exists():
        print(f"输入文件不存在：{trades_csv}")
        print("请把 Binance Futures 成交记录 CSV 放到 data/trades/trades.csv 后重新运行。")
        write_missing_input_summary(output_dir, trades_csv)
        return 2

    try:
        raw = read_csv_auto(trades_csv)
    except Exception as exc:
        ERRORS.add(f"failed to read CSV {trades_csv}: {exc}")
        ERRORS.write(output_dir / "error_log.txt")
        raise

    field_map = detect_fields(raw)
    missing = field_map.missing_core()
    if missing:
        ERRORS.add(f"field detection missing core fields: {missing}; columns={list(raw.columns)}")
    has_source_fields = bool(field_map.note or field_map.strategy)

    all_trades = prepare_trades(raw, field_map, None)
    trades = select_trades_for_analysis(all_trades, args.max_trades, args.recent_months)
    if trades.empty:
        ERRORS.add("no trades after reading CSV")

    features = compute_trade_features(trades, cache_root) if not trades.empty else pd.DataFrame()
    period_df, periods, cutoff_recent, _ = build_periods(features, args.recent_months) if not features.empty else (
        pd.DataFrame(),
        {},
        pd.Timestamp.now(tz="UTC") - pd.DateOffset(months=args.recent_months),
        pd.Timestamp.now(tz="UTC") - pd.DateOffset(months=1),
    )
    logic_summary = build_logic_summary(features, has_source_fields) if not features.empty else pd.DataFrame()
    top_examples = pick_top_examples(features, periods) if not features.empty else pd.DataFrame()
    chart_paths = plot_trade_charts(top_examples, cache_root, chart_dir, args.top_charts) if not top_examples.empty else []

    features.to_csv(output_dir / "trade_features.csv", index=False, quoting=csv.QUOTE_MINIMAL)
    period_df.to_csv(output_dir / "period_comparison.csv", index=False)
    logic_summary.to_csv(output_dir / "logic_tags_summary.csv", index=False)
    top_examples.to_csv(output_dir / "top_examples.csv", index=False)
    generate_summary(
        output_dir / "summary.md",
        features,
        period_df,
        logic_summary,
        top_examples,
        chart_paths,
        field_map,
        list(raw.columns),
        missing,
        has_source_fields,
        cutoff_recent,
        args.recent_months,
        len(all_trades),
    )
    ERRORS.write(output_dir / "error_log.txt")
    print(f"wrote {output_dir / 'summary.md'}")
    print(f"wrote {output_dir / 'trade_features.csv'}")
    print(f"wrote {output_dir / 'period_comparison.csv'}")
    print(f"wrote {output_dir / 'logic_tags_summary.csv'}")
    print(f"wrote {output_dir / 'top_examples.csv'}")
    print(f"charts: {len(chart_paths)}")
    if missing:
        print(f"未识别核心字段：{', '.join(missing)}")
        print("CSV 列名：" + ", ".join(map(str, raw.columns)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
