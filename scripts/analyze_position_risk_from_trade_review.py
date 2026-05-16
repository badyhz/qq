#!/usr/bin/env python3
"""Append position sizing risk analysis to the existing trade review outputs.

Reads the original Binance futures position-history CSV plus the already computed
trade_features.csv. It does not call trading APIs and does not re-fetch klines.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

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


def norm_col(name: Any) -> str:
    text = str(name).strip().lower()
    text = text.replace("（", "(").replace("）", ")")
    return re.sub(r"[\s_\-./:()\[\]%]+", "", text)


def find_column(columns: Sequence[str], candidates: Sequence[str]) -> Optional[str]:
    normalized = {col: norm_col(col) for col in columns}
    cands = [norm_col(c) for c in candidates]
    for cand in cands:
        for col, ncol in normalized.items():
            if ncol == cand:
                return col
    for cand in cands:
        for col, ncol in normalized.items():
            if cand and cand in ncol:
                return col
    return None


def read_csv_auto(path: Path) -> pd.DataFrame:
    for enc in ["utf-8-sig", "utf-8", "gb18030", "gbk", "big5"]:
        try:
            return pd.read_csv(path, encoding=enc)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(path)


def clean_number(value: Any) -> float:
    if pd.isna(value):
        return np.nan
    text = str(value).strip().replace(",", "")
    if not text or text.lower() in {"nan", "none", "null", "--", "-"}:
        return np.nan
    text = text.replace("USDT", "").replace("USD", "").replace("usd", "").replace("+", "")
    m = re.search(r"-?\d+(?:\.\d+)?", text)
    return float(m.group(0)) if m else np.nan


def has_tag(tags: Any, tag: str) -> bool:
    return tag in str(tags).split(";")


def any_tag(tags: Any, tag_set: set) -> bool:
    return bool(set(str(tags).split(";")) & tag_set)


def detect_position_fields(raw: pd.DataFrame) -> Dict[str, Optional[str]]:
    cols = list(raw.columns)
    fields = {
        "notional": find_column(cols, ["notional", "value", "trade_amount", "position_value", "amount_usdt", "成交金额", "交易金额", "持仓金额", "名义价值", "仓位价值", "合约价值"]),
        "margin": find_column(cols, ["margin", "isolated_margin", "initial_margin", "保证金", "起始保证金", "初始保证金", "逐仓保证金"]),
        "quantity": find_column(cols, ["quantity", "qty", "size", "volume", "amount", "数量", "张数", "已平仓量", "最大未平仓合约", "成交数量"]),
        "entry_price": find_column(cols, ["entry_price", "open_price", "avg_entry_price", "入场价格", "入场价", "开仓价", "开仓均价"]),
        "fee": find_column(cols, ["fee", "commission", "手续费", "佣金"]),
    }
    for key, col in list(fields.items()):
        if not col:
            continue
        numeric = raw[col].map(clean_number)
        if numeric.notna().sum() == 0:
            fields[key] = None
    return fields


def add_position_fields(features: pd.DataFrame, raw: pd.DataFrame, fields: Dict[str, Optional[str]]) -> pd.DataFrame:
    df = features.copy()
    df["open_time"] = pd.to_datetime(df["open_time"], utc=True, errors="coerce")
    df["close_time"] = pd.to_datetime(df["close_time"], utc=True, errors="coerce")
    df["realized_pnl"] = pd.to_numeric(df["realized_pnl"], errors="coerce")
    df["entry_price"] = pd.to_numeric(df["entry_price"], errors="coerce")
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")

    raw_aug = raw.copy()
    raw_aug["source_row"] = raw_aug.index + 2
    merge_cols = ["source_row"]
    for key, col in fields.items():
        if col:
            out_col = f"raw_{key}"
            raw_aug[out_col] = raw_aug[col].map(clean_number)
            merge_cols.append(out_col)
    df = df.merge(raw_aug[merge_cols], on="source_row", how="left")

    direct_notional_col = "raw_notional" if "raw_notional" in df.columns else None
    if direct_notional_col and df[direct_notional_col].notna().any():
        df["position_size"] = df[direct_notional_col].abs()
        df["position_size_source"] = "raw_notional"
    else:
        quantity = df["raw_quantity"] if "raw_quantity" in df.columns and df["raw_quantity"].notna().any() else df["quantity"]
        entry = df["raw_entry_price"] if "raw_entry_price" in df.columns and df["raw_entry_price"].notna().any() else df["entry_price"]
        df["notional_est"] = (pd.to_numeric(quantity, errors="coerce").abs() * pd.to_numeric(entry, errors="coerce").abs())
        df["position_size"] = df["notional_est"]
        df["position_size_source"] = "quantity_x_entry_price"
    if "notional_est" not in df.columns:
        df["notional_est"] = df["position_size"]

    if "raw_margin" in df.columns and df["raw_margin"].notna().any():
        df["loss_pct_on_margin"] = np.where(df["raw_margin"].abs() > 0, df["realized_pnl"].abs() / df["raw_margin"].abs(), np.nan)
    else:
        df["loss_pct_on_margin"] = np.nan
    df["pnl_pct_on_notional"] = np.where(df["position_size"] > 0, df["realized_pnl"] / df["position_size"], np.nan)
    df["abs_pnl_pct_on_notional"] = df["pnl_pct_on_notional"].abs()
    df["is_impulse"] = df["logic_tags"].fillna("").map(lambda x: any_tag(x, IMPULSE_TAGS))
    df["is_plan"] = df["inferred_logic_group"].eq("更像计划交易")
    return df


def assign_size_buckets(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, float]]:
    out = df.copy()
    valid = out["position_size"].dropna()
    quantiles = {q: float(valid.quantile(q)) if len(valid) else np.nan for q in [0.2, 0.4, 0.6, 0.8, 0.95]}
    if len(valid) < 10 or valid.nunique() < 5:
        qs = valid.quantile([0.2, 0.4, 0.6, 0.8]) if len(valid) else pd.Series(dtype=float)
        edges = [-np.inf] + [float(x) for x in qs.tolist()] + [np.inf]
    else:
        edges = [-np.inf, quantiles[0.2], quantiles[0.4], quantiles[0.6], quantiles[0.8], np.inf]
    labels = ["very_small", "small", "medium", "large", "very_large"]
    out["size_bucket"] = pd.cut(out["position_size"], bins=edges, labels=labels, include_lowest=True, duplicates="drop")
    out["size_bucket"] = out["size_bucket"].astype(str).replace("nan", "unknown")
    top5_cut = quantiles[0.95]
    out["top_5pct_size"] = out["position_size"] >= top5_cut if not np.isnan(top5_cut) else False
    quantiles["large_upper_q80"] = quantiles[0.8]
    return out, quantiles


def add_sequential_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.sort_values("open_time").reset_index(drop=True).copy()
    out["prev_position_size"] = out["position_size"].shift(1)
    out["prev_realized_pnl"] = out["realized_pnl"].shift(1)
    out["size_change_vs_prev"] = out["position_size"] / out["prev_position_size"] - 1
    out["after_loss_size_increased"] = (out["prev_realized_pnl"] < 0) & (out["position_size"] > out["prev_position_size"])
    out["after_win_size_increased"] = (out["prev_realized_pnl"] > 0) & (out["position_size"] > out["prev_position_size"])
    out["after_prev_loss_45m"] = (out["prev_realized_pnl"] < 0) & (pd.to_numeric(out.get("minutes_after_prev_loss"), errors="coerce") <= 45)

    out["day"] = out["open_time"].dt.strftime("%Y-%m-%d")
    out["day_pnl_before_entry_calc"] = out.groupby("day")["realized_pnl"].cumsum() - out["realized_pnl"]
    out["after_daily_profit_size_increased"] = (out["day_pnl_before_entry_calc"] > 0) & (out["position_size"] > out["prev_position_size"])
    out["after_daily_loss_size_increased"] = (out["day_pnl_before_entry_calc"] < 0) & (out["position_size"] > out["prev_position_size"])

    loss_streak = []
    win_streak = []
    cur_loss = 0
    cur_win = 0
    for pnl in out["realized_pnl"].fillna(0):
        loss_streak.append(cur_loss)
        win_streak.append(cur_win)
        if pnl < 0:
            cur_loss += 1
            cur_win = 0
        elif pnl > 0:
            cur_win += 1
            cur_loss = 0
        else:
            cur_loss = 0
            cur_win = 0
    out["loss_streak_before"] = loss_streak
    out["win_streak_before"] = win_streak
    out["during_loss_streak_size_increased"] = (out["loss_streak_before"] >= 1) & (out["position_size"] > out["prev_position_size"])
    out["during_win_streak_size_increased"] = (out["win_streak_before"] >= 1) & (out["position_size"] > out["prev_position_size"])

    prev_same_sizes = []
    prev_same_times = []
    prev_same_pnls = []
    grows_same_2h = []
    for i, row in out.iterrows():
        hist = out.iloc[:i]
        hist = hist[(hist["symbol"] == row["symbol"]) & (hist["open_time"] < row["open_time"])]
        if hist.empty:
            prev_same_sizes.append(np.nan)
            prev_same_times.append(pd.NaT)
            prev_same_pnls.append(np.nan)
            grows_same_2h.append(False)
            continue
        prev = hist.iloc[-1]
        prev_same_sizes.append(prev["position_size"])
        prev_same_times.append(prev["open_time"])
        prev_same_pnls.append(prev["realized_pnl"])
        within_2h = (row["open_time"] - prev["open_time"]).total_seconds() <= 7200
        grows_same_2h.append(bool(within_2h and row["position_size"] > prev["position_size"]))
    out["prev_same_symbol_position_size"] = prev_same_sizes
    out["prev_same_symbol_open_time"] = prev_same_times
    out["prev_same_symbol_pnl"] = prev_same_pnls
    out["same_symbol_2h_size_increased"] = grows_same_2h
    return out


def ratio_true(series: pd.Series, mask: Optional[pd.Series] = None) -> float:
    if mask is not None:
        series = series[mask]
    if len(series) == 0:
        return np.nan
    return float(series.fillna(False).mean())


def bucket_metrics(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    order = ["very_small", "small", "medium", "large", "very_large", "unknown"]
    for bucket in order:
        g = df[df["size_bucket"] == bucket]
        if g.empty and bucket != "unknown":
            continue
        tags = g["logic_tags"].fillna("") if not g.empty else pd.Series(dtype=str)
        rows.append({
            "size_bucket": bucket,
            "trade_count": int(len(g)),
            "avg_position_size": float(g["position_size"].mean()) if len(g) else np.nan,
            "median_position_size": float(g["position_size"].median()) if len(g) else np.nan,
            "total_pnl": float(g["realized_pnl"].sum()) if len(g) else 0.0,
            "win_rate": float((g["realized_pnl"] > 0).mean()) if len(g) else np.nan,
            "avg_pnl": float(g["realized_pnl"].mean()) if len(g) else np.nan,
            "avg_loss": float(g.loc[g["realized_pnl"] < 0, "realized_pnl"].mean()) if (g["realized_pnl"] < 0).any() else np.nan,
            "max_loss": float(g["realized_pnl"].min()) if len(g) else np.nan,
            "avg_quality_score": float(g["quality_score"].mean()) if len(g) else np.nan,
            "impulse_tag_ratio": float(tags.map(lambda x: any_tag(x, IMPULSE_TAGS)).mean()) if len(g) else np.nan,
            "no_stop_loss_ratio": float(tags.map(lambda x: has_tag(x, "no_stop_loss")).mean()) if len(g) else np.nan,
            "late_exit_ratio": float(tags.map(lambda x: has_tag(x, "late_exit")).mean()) if len(g) else np.nan,
            "revenge_trade_ratio": float(tags.map(lambda x: has_tag(x, "revenge_trade")).mean()) if len(g) else np.nan,
            "overtrade_same_symbol_ratio": float(tags.map(lambda x: has_tag(x, "overtrade_same_symbol")).mean()) if len(g) else np.nan,
            "avg_mae_pct": float(g["mae_pct"].mean()) if len(g) else np.nan,
            "avg_abs_mae_pct": float(g["mae_pct"].abs().mean()) if len(g) else np.nan,
            "avg_mfe_mae_ratio": float(g["mfe_mae_ratio"].replace([np.inf, -np.inf], np.nan).mean()) if len(g) else np.nan,
            "top_5pct_size_count": int(g["top_5pct_size"].sum()) if len(g) else 0,
        })
    return pd.DataFrame(rows)


def summarize_position_relations(df: pd.DataFrame, cutoff_recent: pd.Timestamp) -> Dict[str, Any]:
    top_loss20 = df.nsmallest(20, "realized_pnl")
    largeish = {"large", "very_large"}
    recent = df[df["open_time"] >= cutoff_recent]
    earlier = df[df["open_time"] < cutoff_recent]
    very_large = df[df["size_bucket"] == "very_large"]
    impulse = df[df["is_impulse"]]
    plan = df[df["is_plan"]]
    wins = df[df["realized_pnl"] > 0]
    losses = df[df["realized_pnl"] < 0]
    after_loss_mask = df["prev_realized_pnl"] < 0
    after_win_mask = df["prev_realized_pnl"] > 0
    after_daily_profit_mask = df["day_pnl_before_entry_calc"] > 0
    after_daily_loss_mask = df["day_pnl_before_entry_calc"] < 0
    return {
        "top_loss20_large_or_very_large_count": int(top_loss20["size_bucket"].isin(largeish).sum()),
        "top_loss20_count": int(len(top_loss20)),
        "very_large_trade_count": int(len(very_large)),
        "very_large_total_pnl": float(very_large["realized_pnl"].sum()) if len(very_large) else 0.0,
        "very_large_win_rate": float((very_large["realized_pnl"] > 0).mean()) if len(very_large) else np.nan,
        "very_large_no_stop_loss_ratio": ratio_true(very_large["logic_tags"].map(lambda x: has_tag(x, "no_stop_loss"))) if len(very_large) else np.nan,
        "very_large_late_exit_ratio": ratio_true(very_large["logic_tags"].map(lambda x: has_tag(x, "late_exit"))) if len(very_large) else np.nan,
        "very_large_revenge_ratio": ratio_true(very_large["logic_tags"].map(lambda x: has_tag(x, "revenge_trade"))) if len(very_large) else np.nan,
        "very_large_overtrade_ratio": ratio_true(very_large["logic_tags"].map(lambda x: has_tag(x, "overtrade_same_symbol"))) if len(very_large) else np.nan,
        "impulse_avg_position_size": float(impulse["position_size"].mean()) if len(impulse) else np.nan,
        "plan_avg_position_size": float(plan["position_size"].mean()) if len(plan) else np.nan,
        "win_avg_position_size": float(wins["position_size"].mean()) if len(wins) else np.nan,
        "loss_avg_position_size": float(losses["position_size"].mean()) if len(losses) else np.nan,
        "recent_avg_position_size": float(recent["position_size"].mean()) if len(recent) else np.nan,
        "earlier_avg_position_size": float(earlier["position_size"].mean()) if len(earlier) else np.nan,
        "recent_very_large_ratio": float((recent["size_bucket"] == "very_large").mean()) if len(recent) else np.nan,
        "earlier_very_large_ratio": float((earlier["size_bucket"] == "very_large").mean()) if len(earlier) else np.nan,
        "same_symbol_2h_size_increase_ratio": ratio_true(df["same_symbol_2h_size_increased"], df["prev_same_symbol_open_time"].notna()),
        "after_loss_45m_avg_position_size": float(df.loc[df["after_prev_loss_45m"], "position_size"].mean()) if df["after_prev_loss_45m"].any() else np.nan,
        "after_loss_size_increase_ratio": ratio_true(df["after_loss_size_increased"], after_loss_mask),
        "after_win_size_increase_ratio": ratio_true(df["after_win_size_increased"], after_win_mask),
        "after_daily_profit_size_increase_ratio": ratio_true(df["after_daily_profit_size_increased"], after_daily_profit_mask),
        "after_daily_loss_size_increase_ratio": ratio_true(df["after_daily_loss_size_increased"], after_daily_loss_mask),
        "loss_streak_size_increase_ratio": ratio_true(df["during_loss_streak_size_increased"], df["loss_streak_before"] >= 1),
        "win_streak_size_increase_ratio": ratio_true(df["during_win_streak_size_increased"], df["win_streak_before"] >= 1),
    }


def simulate_rules(df: pd.DataFrame, q: Dict[str, float]) -> pd.DataFrame:
    rows = []
    original_total = float(df["realized_pnl"].sum())
    original_max_loss = float(df["realized_pnl"].min())

    def add_rule(name: str, desc: str, scale: pd.Series) -> None:
        scale = scale.fillna(1.0).clip(lower=0.0, upper=1.0)
        sim_pnl = df["realized_pnl"] * scale
        affected = scale < 0.999999
        sim_total = float(sim_pnl.sum())
        sim_max_loss = float(sim_pnl.min())
        rows.append({
            "rule": name,
            "description": desc,
            "original_total_pnl": original_total,
            "simulated_total_pnl": sim_total,
            "improvement_amount": sim_total - original_total,
            "affected_trade_count": int(affected.sum()),
            "original_max_loss": original_max_loss,
            "simulated_max_loss": sim_max_loss,
            "max_loss_compression": abs(original_max_loss) - abs(sim_max_loss),
        })

    large_cap = q.get("large_upper_q80", np.nan)
    scale_a = pd.Series(1.0, index=df.index)
    if not np.isnan(large_cap) and large_cap > 0:
        mask = df["size_bucket"].eq("very_large") & (df["position_size"] > large_cap)
        scale_a.loc[mask] = large_cap / df.loc[mask, "position_size"]
    add_rule("A", "禁止 very_large 仓位，将 very_large 盈亏按 large 桶上限等比例缩小。", scale_a)

    cap_b = df["prev_position_size"] * 0.5
    mask_b = (df["prev_realized_pnl"] < 0) & (df["position_size"] > cap_b) & (cap_b > 0)
    scale_b = pd.Series(1.0, index=df.index)
    scale_b.loc[mask_b] = cap_b.loc[mask_b] / df.loc[mask_b, "position_size"]
    add_rule("B", "亏损后一笔交易，仓位不得大于上一笔仓位的 50%。", scale_b)

    cap_c = df["prev_same_symbol_position_size"] * 0.5
    within_2h = (df["open_time"] - pd.to_datetime(df["prev_same_symbol_open_time"], utc=True, errors="coerce")).dt.total_seconds() <= 7200
    mask_c = within_2h & (df["position_size"] > cap_c) & (cap_c > 0)
    scale_c = pd.Series(1.0, index=df.index)
    scale_c.loc[mask_c] = cap_c.loc[mask_c] / df.loc[mask_c, "position_size"]
    add_rule("C", "同一 symbol 2 小时内再次交易，仓位不得大于上一笔同 symbol 仓位的 50%。", scale_c)

    scale_d = pd.Series(np.where(df["is_impulse"], 0.3, 1.0), index=df.index)
    add_rule("D", "冲动标签交易的仓位统一缩小到当前的 30%。", scale_d)

    scale_e = pd.Series(np.where(df["inferred_logic_group"].eq("更像冲动交易"), 0.3, 1.0), index=df.index)
    add_rule("E", "计划型交易保持原仓位，冲动型交易仓位缩小到 30%。", scale_e)
    return pd.DataFrame(rows)


def chart_path_for(trade_id: Any, chart_dir: Path) -> str:
    try:
        tid = int(trade_id)
    except Exception:
        return ""
    matches = sorted(chart_dir.glob(f"trade_{tid:04d}_*.png"))
    return str(matches[0]) if matches else ""


def build_examples(df: pd.DataFrame, chart_dir: Path) -> pd.DataFrame:
    examples: List[pd.DataFrame] = []

    def add(category: str, data: pd.DataFrame, reason: str, sort_cols: List[str], ascending: List[bool], n: int = 10) -> None:
        if data.empty:
            return
        tmp = data.sort_values(sort_cols, ascending=ascending, na_position="last").head(n).copy()
        tmp["case_category"] = category
        tmp["review_reason"] = reason
        examples.append(tmp)

    largeish = df[df["size_bucket"].isin(["large", "very_large"])]
    add("大仓位 + 大亏损", largeish[largeish["realized_pnl"] < 0], "大仓位下出现大额亏损，优先检查是否应被仓位上限拦截。", ["realized_pnl"], [True])
    add("大仓位 + 冲动标签", largeish[largeish["is_impulse"]], "仓位较大且带冲动/纪律问题标签，说明行为风险被仓位放大。", ["position_size"], [False])
    add("大仓位 + no_stop_loss", largeish[largeish["logic_tags"].map(lambda x: has_tag(x, "no_stop_loss"))], "大仓位且无止损/扛单，是最大回撤源头之一。", ["position_size"], [False])
    add("连亏后仓位放大", df[df["after_loss_size_increased"]], "上一笔亏损后下一笔仓位变大，可能是复仇交易或急于追回。", ["size_change_vs_prev"], [False])
    add("盈利后仓位放大", df[df["after_win_size_increased"]], "上一笔盈利后下一笔仓位变大，可能是上头或过度自信。", ["size_change_vs_prev"], [False])
    add("计划型交易但仓位合理的优秀样板", df[df["is_plan"] & df["size_bucket"].isin(["small", "medium", "large"])], "计划型结构清晰，仓位不在极端区间，可作为正向模板。", ["quality_score", "realized_pnl"], [False, False])
    add("位置不差但仓位过大", df[(df["quality_score"] >= 60) & df["size_bucket"].eq("very_large")], "K线结构或质量不差，但仓位进入 very_large，应复盘是否有必要承担这么大敞口。", ["position_size"], [False])

    if not examples:
        return pd.DataFrame()
    out = pd.concat(examples, ignore_index=True)
    out["chart_path"] = out["trade_id"].map(lambda x: chart_path_for(x, chart_dir))
    out = out.rename(columns={"direction": "side", "logic_tags": "tags"})
    keep = [
        "case_category", "trade_id", "source_row", "symbol", "open_time", "side", "realized_pnl",
        "position_size", "notional_est", "size_bucket", "top_5pct_size", "quality_score", "tags",
        "review_reason", "chart_path", "prev_realized_pnl", "prev_position_size", "size_change_vs_prev",
        "day_pnl_before_entry_calc", "pnl_pct_on_notional", "mae_pct", "mfe_mae_ratio",
    ]
    return out[[c for c in keep if c in out.columns]].drop_duplicates(["case_category", "trade_id"])


def md_table(df: pd.DataFrame, columns: Optional[List[str]] = None) -> str:
    if df.empty:
        return "无数据"
    view = df[columns].copy() if columns else df.copy()
    for col in view.columns:
        if pd.api.types.is_float_dtype(view[col]):
            view[col] = view[col].map(lambda x: "" if pd.isna(x) else f"{x:.4f}")
    return view.to_markdown(index=False)


def fmt(v: Any, digits: int = 2, pct: bool = False) -> str:
    try:
        if pd.isna(v):
            return "N/A"
        f = float(v)
    except Exception:
        return str(v)
    if pct:
        return f"{f * 100:.1f}%"
    return f"{f:.{digits}f}"


def generate_report(
    out_path: Path,
    df: pd.DataFrame,
    raw: pd.DataFrame,
    fields: Dict[str, Optional[str]],
    buckets: pd.DataFrame,
    relations: Dict[str, Any],
    simulations: pd.DataFrame,
    examples: pd.DataFrame,
    quantiles: Dict[str, float],
    cutoff_recent: pd.Timestamp,
) -> None:
    best = simulations.sort_values("improvement_amount", ascending=False).iloc[0] if not simulations.empty else None
    suitable = simulations.sort_values(["max_loss_compression", "affected_trade_count"], ascending=[False, True]).iloc[0] if not simulations.empty else None
    very_large = buckets[buckets["size_bucket"] == "very_large"]
    very_large_pnl = very_large["total_pnl"].iloc[0] if not very_large.empty else np.nan
    very_large_wr = very_large["win_rate"].iloc[0] if not very_large.empty else np.nan
    position_core = "是核心问题之一" if relations["top_loss20_large_or_very_large_count"] >= 10 or relations["loss_avg_position_size"] > relations["win_avg_position_size"] else "不是唯一核心问题，但会放大错误交易后果"
    recent_more_aggressive = relations["recent_avg_position_size"] > relations["earlier_avg_position_size"] or relations["recent_very_large_ratio"] > relations["earlier_very_large_ratio"]
    direct_notional = fields.get("notional")
    margin_field = fields.get("margin")
    size_method = "直接使用原始 CSV 的交易金额/名义价值字段" if direct_notional else "未识别到直接名义价值字段，使用 abs(quantity * entry_price) 估算 notional_est"
    margin_note = "可计算保证金级别亏损比例。" if margin_field else "未识别到保证金字段，无法计算真实 loss_pct_on_margin，只能计算 pnl_pct_on_notional。"
    missing = [k for k in ["notional", "margin", "fee"] if not fields.get(k)]
    raw_cols = ", ".join(map(str, raw.columns))

    top_example_lines = []
    for _, row in examples.head(20).iterrows():
        top_example_lines.append(
            f"- {row.get('case_category')}: trade_id={row.get('trade_id')} {row.get('symbol')} {row.get('side')} "
            f"pnl={fmt(row.get('realized_pnl'))} size={fmt(row.get('position_size'))} bucket={row.get('size_bucket')} "
            f"score={fmt(row.get('quality_score'), 1)}，原因：{row.get('review_reason')}"
        )
    if not top_example_lines:
        top_example_lines = ["- 无足够数据生成仓位案例。"]

    report = f"""# 仓位风险分析报告

## 1. 结论先行
- 仓位控制{position_core}。最大亏损前 20 笔中，large / very_large 仓位有 {relations['top_loss20_large_or_very_large_count']} 笔。
- very_large 仓位总盈亏为 {fmt(very_large_pnl)}，胜率为 {fmt(very_large_wr, pct=True)}。
- 最近两个月平均仓位为 {fmt(relations['recent_avg_position_size'])}，更早阶段为 {fmt(relations['earlier_avg_position_size'])}；{'最近两个月更激进' if recent_more_aggressive else '最近两个月没有明显放大平均仓位'}。
- 最近两个月 very_large 比例为 {fmt(relations['recent_very_large_ratio'], pct=True)}，更早阶段为 {fmt(relations['earlier_very_large_ratio'], pct=True)}。
- 冲动交易平均仓位为 {fmt(relations['impulse_avg_position_size'])}，计划型交易平均仓位为 {fmt(relations['plan_avg_position_size'])}。
- 亏损交易平均仓位为 {fmt(relations['loss_avg_position_size'])}，盈利交易平均仓位为 {fmt(relations['win_avg_position_size'])}。
- 亏损后一笔交易仓位变大比例为 {fmt(relations['after_loss_size_increase_ratio'], pct=True)}；盈利后一笔交易仓位变大比例为 {fmt(relations['after_win_size_increase_ratio'], pct=True)}。
- 当日累计亏损后仓位变大比例为 {fmt(relations['after_daily_loss_size_increase_ratio'], pct=True)}；当日累计盈利后仓位变大比例为 {fmt(relations['after_daily_profit_size_increase_ratio'], pct=True)}。
- 同一 symbol 短时间重复交易时，仓位继续变大的比例为 {fmt(relations['same_symbol_2h_size_increase_ratio'], pct=True)}。
- 模拟中改善金额最高的规则是规则 {best['rule'] if best is not None else 'N/A'}；最适合优先执行的规则是规则 {suitable['rule'] if suitable is not None else 'N/A'}，因为它对最大单笔亏损压缩更直接。
- 这些模拟是线性缩仓假设，不是真实回测，也没有考虑滑点、成交深度、保证金模式和强平风险。

## 2. 数据与字段说明
- 原始 CSV 行数：{len(raw)}；本次复用 trade_features 行数：{len(df)}。
- 仓位字段识别结果：
```json
{json.dumps(fields, ensure_ascii=False, indent=2)}
```
- 仓位估算方法：{size_method}。
- 保证金限制：{margin_note}
- 未识别字段：{', '.join(missing) if missing else '无'}。
- CSV 全部列名：{raw_cols}。
- 分位阈值：20%={fmt(quantiles.get(0.2))}，40%={fmt(quantiles.get(0.4))}，60%={fmt(quantiles.get(0.6))}，80%={fmt(quantiles.get(0.8))}，95%={fmt(quantiles.get(0.95))}。

## 3. 仓位分桶统计
{md_table(buckets, ['size_bucket','trade_count','avg_position_size','median_position_size','total_pnl','win_rate','avg_pnl','avg_loss','max_loss','avg_quality_score','impulse_tag_ratio','no_stop_loss_ratio','late_exit_ratio','revenge_trade_ratio','overtrade_same_symbol_ratio','avg_abs_mae_pct','avg_mfe_mae_ratio','top_5pct_size_count'])}

## 4. 大亏与仓位关系
- 最大亏损前 20 笔中，large / very_large 仓位占 {relations['top_loss20_large_or_very_large_count']} / {relations['top_loss20_count']}。
- very_large 仓位交易数为 {relations['very_large_trade_count']}，总盈亏 {fmt(relations['very_large_total_pnl'])}，胜率 {fmt(relations['very_large_win_rate'], pct=True)}。
- very_large 的 no_stop_loss 比例 {fmt(relations['very_large_no_stop_loss_ratio'], pct=True)}，late_exit 比例 {fmt(relations['very_large_late_exit_ratio'], pct=True)}，revenge_trade 比例 {fmt(relations['very_large_revenge_ratio'], pct=True)}，overtrade 比例 {fmt(relations['very_large_overtrade_ratio'], pct=True)}。
- 如果大亏集中在大仓位，说明问题不是单纯“方向错”，而是错误方向被仓位放大。

## 5. 计划型交易 vs 冲动型交易的仓位差异
- 冲动交易平均仓位：{fmt(relations['impulse_avg_position_size'])}。
- 计划型交易平均仓位：{fmt(relations['plan_avg_position_size'])}。
- 计划型交易是否更克制：{'是' if relations['plan_avg_position_size'] < relations['impulse_avg_position_size'] else '否，计划型平均仓位不低，需要继续限制单笔敞口'}。
- 计划型交易整体质量更高，但如果仓位进入 very_large，仍然需要单独复盘，不能因为“逻辑看起来对”就放大仓位。

## 6. 以前 vs 最近两个月的仓位变化
- 最近两个月切分点：{cutoff_recent}。
- 最近两个月平均仓位：{fmt(relations['recent_avg_position_size'])}。
- 更早阶段平均仓位：{fmt(relations['earlier_avg_position_size'])}。
- 最近两个月 very_large 比例：{fmt(relations['recent_very_large_ratio'], pct=True)}。
- 更早阶段 very_large 比例：{fmt(relations['earlier_very_large_ratio'], pct=True)}。
- 结论：{'最近两个月仓位更激进，尤其需要限制重复交易和冲动标签交易仓位。' if recent_more_aggressive else '最近两个月仓位没有明显更激进，主要风险更偏向交易频率、标签纪律和个别极端仓位。'}

## 7. 盈利后/亏损后的仓位变化
- after_loss_size_increase_ratio：{fmt(relations['after_loss_size_increase_ratio'], pct=True)}。含义：上一笔亏损后，下一笔交易仓位比上一笔更大的比例。
- after_win_size_increase_ratio：{fmt(relations['after_win_size_increase_ratio'], pct=True)}。含义：上一笔盈利后，下一笔交易仓位比上一笔更大的比例。
- after_daily_profit_size_increase_ratio：{fmt(relations['after_daily_profit_size_increase_ratio'], pct=True)}。含义：当日开仓前累计盈利时，本笔交易是否比上一笔仓位更大。
- after_daily_loss_size_increase_ratio：{fmt(relations['after_daily_loss_size_increase_ratio'], pct=True)}。含义：当日开仓前累计亏损时，本笔交易是否比上一笔仓位更大。
- 连亏期间仓位扩大比例：{fmt(relations['loss_streak_size_increase_ratio'], pct=True)}。
- 连赢期间仓位扩大比例：{fmt(relations['win_streak_size_increase_ratio'], pct=True)}。

## 8. 仓位控制规则模拟
{md_table(simulations, ['rule','description','original_total_pnl','simulated_total_pnl','improvement_amount','affected_trade_count','original_max_loss','simulated_max_loss','max_loss_compression'])}

- 改善金额最高：规则 {best['rule'] if best is not None else 'N/A'}。
- 最大亏损压缩最直接：规则 {suitable['rule'] if suitable is not None else 'N/A'}。
- 最适合你的优先规则：如果目标是先降低灾难性亏损，优先执行规则 {suitable['rule'] if suitable is not None else 'N/A'}；如果目标是最大化历史样本线性收益，参考规则 {best['rule'] if best is not None else 'N/A'}。

## 9. 典型案例
{chr(10).join(top_example_lines)}

## 10. 给我的仓位军规
- 单笔名义仓位不得超过当前样本 80% 分位：{fmt(quantiles.get(0.8))}；超过必须有明确止损和计划标签，否则禁止。
- 95% 分位以上仓位：{fmt(quantiles.get(0.95))} 以上只允许计划型交易，冲动标签一律缩到 30%。
- 上一笔亏损后 45 分钟内，下一笔仓位不得超过上一笔仓位的 50%。
- 同一 symbol 2 小时内再次交易，仓位不得超过上一笔同 symbol 仓位的 50%。
- 当日累计亏损后，不允许仓位比上一笔更大；必须先降到上一笔的 50% 以下。
- 当日累计盈利后，不允许因为盈利放大仓位；下一笔仍受常规上限约束。
- 妖币、小市值、急涨急跌后追单的交易，默认仓位上限为正常仓位的 30%。
- 没有明确 protective stop 的交易，仓位上限为 very_small 桶，且不允许补仓或反复开仓。
"""
    out_path.write_text(report, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze position sizing risk from existing trade review outputs.")
    parser.add_argument("--raw-csv", default="Binance-合约仓位历史记录-202605051747(UTC+8).csv")
    parser.add_argument("--trade-features", default="reports/trade_logic_evolution/trade_features.csv")
    parser.add_argument("--output-dir", default="reports/trade_logic_evolution")
    args = parser.parse_args()

    raw_path = Path(args.raw_csv)
    features_path = Path(args.trade_features)
    output_dir = Path(args.output_dir)
    chart_dir = output_dir / "charts"
    output_dir.mkdir(parents=True, exist_ok=True)

    if not raw_path.exists():
        raise FileNotFoundError(f"raw CSV not found: {raw_path}")
    if not features_path.exists():
        raise FileNotFoundError(f"trade_features not found: {features_path}")

    raw = read_csv_auto(raw_path)
    features = pd.read_csv(features_path)
    fields = detect_position_fields(raw)
    df = add_position_fields(features, raw, fields)
    df, quantiles = assign_size_buckets(df)
    df = add_sequential_features(df)

    latest = df["open_time"].dropna().max()
    cutoff_recent = latest - pd.DateOffset(months=2)
    buckets = bucket_metrics(df)
    relations = summarize_position_relations(df, cutoff_recent)
    simulations = simulate_rules(df, quantiles)
    examples = build_examples(df, chart_dir)

    buckets.to_csv(output_dir / "position_risk_by_bucket.csv", index=False)
    examples.to_csv(output_dir / "position_risk_examples.csv", index=False, quoting=csv.QUOTE_MINIMAL)
    generate_report(
        output_dir / "position_risk_analysis.md",
        df,
        raw,
        fields,
        buckets,
        relations,
        simulations,
        examples,
        quantiles,
        cutoff_recent,
    )

    print(f"wrote {output_dir / 'position_risk_analysis.md'}")
    print(f"wrote {output_dir / 'position_risk_by_bucket.csv'}")
    print(f"wrote {output_dir / 'position_risk_examples.csv'}")
    print(json.dumps(relations, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
