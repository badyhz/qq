from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.strategy_edge_common import (
    atr,
    ema,
    find_bar_index,
    load_cached_klines,
    load_shadow_plan_rows,
    match_plan_for_trade,
    nan_to_empty,
    read_csv_rows,
    safe_ratio,
    to_float,
    to_float_nan,
    to_epoch_ms,
)


FIELDS = [
    "trade_id",
    "candidate_id",
    "symbol",
    "side",
    "timeframe",
    "signal_time",
    "entry_time",
    "entry_price",
    "ema21",
    "ema55",
    "ema200",
    "price_vs_ema21_pct",
    "price_vs_ema55_pct",
    "price_vs_ema200_pct",
    "ema21_slope_pct",
    "ema55_slope_pct",
    "breakout_level",
    "breakout_distance_pct",
    "breakout_body_pct",
    "close_position_in_bar",
    "atr_pct",
    "volume_ratio",
    "btc_regime_status",
    "btc_return_pct",
    "btc_above_ema",
    "risk_reward_ratio",
    "stop_distance_pct",
    "take_profit_distance_pct",
    "snapshot_status",
    "missing_fields",
    "source_reports",
]


def _calc_row(
    *,
    trade: dict[str, Any],
    timeframe: str,
    signal_time: str,
    cache_root: str,
) -> dict[str, Any]:
    symbol = str(trade.get("symbol", "")).strip().upper()
    side = str(trade.get("side", "")).strip().upper()
    entry_time = str(trade.get("entry_time", "")).strip()
    entry_price = to_float_nan(trade.get("entry_price"))
    sl_price = to_float_nan(trade.get("sl_price"))
    tp_price = to_float_nan(trade.get("tp_price"))
    entry_ts = to_epoch_ms(entry_time)
    missing: list[str] = []

    klines = load_cached_klines(cache_root=cache_root, symbol=symbol, timeframe=timeframe)
    idx = find_bar_index(klines, entry_ts) if klines and entry_ts > 0 else -1
    if not klines:
        missing.append("missing_symbol_klines")
    if idx < 0:
        missing.append("missing_entry_bar")

    ema21 = ema55 = ema200 = float("nan")
    price_vs_ema21 = price_vs_ema55 = price_vs_ema200 = float("nan")
    ema21_slope = ema55_slope = float("nan")
    breakout_level = breakout_distance_pct = float("nan")
    breakout_body_pct = close_position = float("nan")
    atr_pct = volume_ratio = float("nan")

    if idx >= 0:
        closes = [to_float(item.get("close", 0.0), 0.0) for item in klines[: idx + 1]]
        highs = [to_float(item.get("high", 0.0), 0.0) for item in klines[: idx + 1]]
        lows = [to_float(item.get("low", 0.0), 0.0) for item in klines[: idx + 1]]
        volumes = [to_float(item.get("volume", 0.0), 0.0) for item in klines[: idx + 1]]
        if len(closes) >= 1:
            ema21_list = ema(closes, 21)
            ema55_list = ema(closes, 55)
            ema200_list = ema(closes, 200)
            ema21 = ema21_list[-1] if ema21_list else float("nan")
            ema55 = ema55_list[-1] if ema55_list else float("nan")
            ema200 = ema200_list[-1] if ema200_list else float("nan")
            price_vs_ema21 = safe_ratio(entry_price - ema21, ema21) * 100.0 if math.isfinite(ema21) else float("nan")
            price_vs_ema55 = safe_ratio(entry_price - ema55, ema55) * 100.0 if math.isfinite(ema55) else float("nan")
            price_vs_ema200 = safe_ratio(entry_price - ema200, ema200) * 100.0 if math.isfinite(ema200) else float("nan")
            if len(ema21_list) > 5 and ema21_list[-6] != 0:
                ema21_slope = (ema21_list[-1] - ema21_list[-6]) / ema21_list[-6] * 100.0
            else:
                missing.append("insufficient_ema21_slope_window")
            if len(ema55_list) > 5 and ema55_list[-6] != 0:
                ema55_slope = (ema55_list[-1] - ema55_list[-6]) / ema55_list[-6] * 100.0
            else:
                missing.append("insufficient_ema55_slope_window")

            start = max(0, idx - 20)
            if side in {"SELL", "SHORT"}:
                breakout_level = min(lows[start : idx + 1]) if lows[start : idx + 1] else float("nan")
                breakout_distance_pct = safe_ratio(breakout_level - entry_price, entry_price) * 100.0 if entry_price > 0 else float("nan")
            else:
                breakout_level = max(highs[start : idx + 1]) if highs[start : idx + 1] else float("nan")
                breakout_distance_pct = safe_ratio(entry_price - breakout_level, entry_price) * 100.0 if entry_price > 0 else float("nan")

            row = klines[idx]
            bar_open = to_float(row.get("open", 0.0), 0.0)
            bar_high = to_float(row.get("high", 0.0), 0.0)
            bar_low = to_float(row.get("low", 0.0), 0.0)
            bar_close = to_float(row.get("close", 0.0), 0.0)
            spread = bar_high - bar_low
            breakout_body_pct = safe_ratio(abs(bar_close - bar_open), spread) * 100.0 if spread > 0 else float("nan")
            close_position = safe_ratio(bar_close - bar_low, spread) if spread > 0 else float("nan")

            atr_values = atr(klines[: idx + 1], 14)
            atr_now = atr_values[-1] if atr_values else float("nan")
            atr_pct = safe_ratio(atr_now, bar_close) * 100.0 if bar_close > 0 else float("nan")
            if len(volumes) >= 2:
                lookback = min(20, len(volumes) - 1)
                history = volumes[-(lookback + 1) : -1]
                avg_volume = sum(history) / max(1, len(history))
                volume_ratio = safe_ratio(volumes[-1], avg_volume) if avg_volume > 0 else float("nan")
                if lookback < 10:
                    missing.append("short_volume_window")
            else:
                missing.append("insufficient_volume_window")

    btc_regime_status = "UNKNOWN"
    btc_return_pct = float("nan")
    btc_above_ema = ""
    btc_rows = load_cached_klines(cache_root=cache_root, symbol="BTCUSDT", timeframe=timeframe)
    btc_idx = find_bar_index(btc_rows, entry_ts) if btc_rows and entry_ts > 0 else -1
    if btc_idx >= 0:
        btc_closes = [to_float(item.get("close", 0.0), 0.0) for item in btc_rows[: btc_idx + 1]]
        if btc_closes:
            btc_ema = ema(btc_closes, 21)
            btc_above = btc_closes[-1] > btc_ema[-1] if btc_ema else False
            btc_above_ema = "true" if btc_above else "false"
            lookback = 12
            if len(btc_closes) > lookback and btc_closes[-lookback - 1] > 0:
                btc_return_pct = (btc_closes[-1] - btc_closes[-lookback - 1]) / btc_closes[-lookback - 1] * 100.0
            if side in {"SELL", "SHORT"}:
                btc_regime_status = "SUPPORTIVE" if (not btc_above) else "AGAINST"
            else:
                btc_regime_status = "SUPPORTIVE" if btc_above else "AGAINST"
    else:
        missing.append("missing_btc_regime_klines")

    rr = safe_ratio(abs(tp_price - entry_price), abs(entry_price - sl_price))
    stop_distance_pct = safe_ratio(abs(entry_price - sl_price), entry_price) * 100.0 if entry_price > 0 and math.isfinite(sl_price) else float("nan")
    tp_distance_pct = safe_ratio(abs(tp_price - entry_price), entry_price) * 100.0 if entry_price > 0 and math.isfinite(tp_price) else float("nan")

    status = "PASS"
    if missing:
        status = "PARTIAL"
    if "missing_symbol_klines" in missing:
        status = "MISSING_KLINES"

    return {
        "trade_id": str(trade.get("trade_id", "")),
        "candidate_id": str(trade.get("candidate_id", "")),
        "symbol": symbol,
        "side": side,
        "timeframe": timeframe,
        "signal_time": signal_time,
        "entry_time": entry_time,
        "entry_price": nan_to_empty(entry_price),
        "ema21": nan_to_empty(ema21),
        "ema55": nan_to_empty(ema55),
        "ema200": nan_to_empty(ema200),
        "price_vs_ema21_pct": nan_to_empty(price_vs_ema21),
        "price_vs_ema55_pct": nan_to_empty(price_vs_ema55),
        "price_vs_ema200_pct": nan_to_empty(price_vs_ema200),
        "ema21_slope_pct": nan_to_empty(ema21_slope),
        "ema55_slope_pct": nan_to_empty(ema55_slope),
        "breakout_level": nan_to_empty(breakout_level),
        "breakout_distance_pct": nan_to_empty(breakout_distance_pct),
        "breakout_body_pct": nan_to_empty(breakout_body_pct),
        "close_position_in_bar": nan_to_empty(close_position),
        "atr_pct": nan_to_empty(atr_pct),
        "volume_ratio": nan_to_empty(volume_ratio),
        "btc_regime_status": btc_regime_status,
        "btc_return_pct": nan_to_empty(btc_return_pct),
        "btc_above_ema": btc_above_ema,
        "risk_reward_ratio": nan_to_empty(rr if math.isfinite(rr) else to_float_nan(trade.get("risk_reward_ratio"))),
        "stop_distance_pct": nan_to_empty(stop_distance_pct if math.isfinite(stop_distance_pct) else to_float_nan(trade.get("stop_distance_pct"))),
        "take_profit_distance_pct": nan_to_empty(tp_distance_pct if math.isfinite(tp_distance_pct) else to_float_nan(trade.get("take_profit_distance_pct"))),
        "snapshot_status": status,
        "missing_fields": ";".join(sorted(set(missing))) if missing else "",
        "source_reports": str(trade.get("source_reports", "")),
    }


def generate_signal_snapshot_csv(
    *,
    lifecycle_csv: str = "reports/trade_lifecycle/trade_lifecycle.csv",
    shadow_plan_jsonl: str = "logs/shadow_order_plans.jsonl",
    cache_root: str = "data/cache/klines",
    output_dir: str = "reports/signal_snapshot",
) -> dict[str, Any]:
    lifecycle_rows = read_csv_rows(Path(lifecycle_csv))
    plans = load_shadow_plan_rows(shadow_plan_jsonl)
    rows: list[dict[str, Any]] = []
    for trade in lifecycle_rows:
        plan = match_plan_for_trade(trade_row=trade, plans=plans)
        timeframe = str(plan.get("timeframe", "5m") if plan else "5m")
        signal_time = str(plan.get("entry_timestamp", trade.get("entry_time", "")) if plan else trade.get("entry_time", ""))
        rows.append(_calc_row(trade=trade, timeframe=timeframe, signal_time=signal_time, cache_root=cache_root))

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "signal_snapshot.csv"
    json_path = out_dir / "signal_snapshot.json"
    md_path = out_dir / "summary.md"

    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in FIELDS})

    summary = {
        "ok": True,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "total_rows": len(rows),
        "pass_count": sum(1 for row in rows if str(row.get("snapshot_status", "")).upper() == "PASS"),
        "partial_count": sum(1 for row in rows if str(row.get("snapshot_status", "")).upper() == "PARTIAL"),
        "missing_klines_count": sum(1 for row in rows if str(row.get("snapshot_status", "")).upper() == "MISSING_KLINES"),
        "csv_path": str(csv_path),
        "json_path": str(json_path),
        "summary_md_path": str(md_path),
        "rows": rows,
    }
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    md_lines = [
        "# Signal Snapshot Summary",
        "",
        f"- total_rows: {summary['total_rows']}",
        f"- pass_count: {summary['pass_count']}",
        f"- partial_count: {summary['partial_count']}",
        f"- missing_klines_count: {summary['missing_klines_count']}",
    ]
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return summary


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate entry signal snapshot CSV from offline data")
    parser.add_argument("--lifecycle-csv", default="reports/trade_lifecycle/trade_lifecycle.csv")
    parser.add_argument("--shadow-plan-jsonl", default="logs/shadow_order_plans.jsonl")
    parser.add_argument("--cache-root", default="data/cache/klines")
    parser.add_argument("--output-dir", default="reports/signal_snapshot")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = generate_signal_snapshot_csv(
        lifecycle_csv=str(args.lifecycle_csv or "reports/trade_lifecycle/trade_lifecycle.csv"),
        shadow_plan_jsonl=str(args.shadow_plan_jsonl or "logs/shadow_order_plans.jsonl"),
        cache_root=str(args.cache_root or "data/cache/klines"),
        output_dir=str(args.output_dir or "reports/signal_snapshot"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"total_rows={result.get('total_rows', 0)}")
    print(f"csv_path={result.get('csv_path', '')}")


if __name__ == "__main__":
    main()
