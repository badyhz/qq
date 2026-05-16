from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.strategy_edge_common import (
    find_bar_index,
    load_cached_klines,
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
    "entry_time",
    "exit_time",
    "entry_price",
    "exit_price",
    "sl_price",
    "tp_price",
    "quantity",
    "risk_per_unit",
    "max_favorable_price",
    "max_adverse_price",
    "mfe_usdt",
    "mae_usdt",
    "mfe_r",
    "mae_r",
    "mfe_pct",
    "mae_pct",
    "bars_to_mfe",
    "bars_to_mae",
    "bars_to_exit",
    "tp_was_reachable",
    "sl_was_reachable",
    "exit_efficiency_pct",
    "mfe_capture_ratio",
    "mae_control_ratio",
    "analysis_status",
    "missing_fields",
    "source_reports",
]


def _slice_trade_window(
    *,
    klines: list[dict[str, Any]],
    entry_ts: int,
    exit_ts: int,
    fallback_bars: int = 120,
) -> tuple[list[dict[str, Any]], int, int]:
    if not klines:
        return [], -1, -1
    entry_idx = find_bar_index(klines, entry_ts)
    if entry_idx < 0:
        return [], -1, -1
    if exit_ts > 0:
        exit_idx = find_bar_index(klines, exit_ts)
        if exit_idx < entry_idx:
            exit_idx = min(len(klines) - 1, entry_idx + fallback_bars)
    else:
        exit_idx = min(len(klines) - 1, entry_idx + fallback_bars)
    return klines[entry_idx : exit_idx + 1], entry_idx, exit_idx


def analyze_post_entry_mfe_mae(
    *,
    lifecycle_csv: str = "reports/trade_lifecycle/trade_lifecycle.csv",
    cache_root: str = "data/cache/klines",
    output_dir: str = "reports/post_entry_mfe_mae",
    default_timeframe: str = "5m",
) -> dict[str, Any]:
    lifecycle_rows = read_csv_rows(Path(lifecycle_csv))
    rows: list[dict[str, Any]] = []
    for trade in lifecycle_rows:
        symbol = str(trade.get("symbol", "")).strip().upper()
        side = str(trade.get("side", "")).strip().upper()
        entry_time = str(trade.get("entry_time", ""))
        exit_time = str(trade.get("exit_time", ""))
        entry_ts = to_epoch_ms(entry_time)
        exit_ts = to_epoch_ms(exit_time)
        entry_price = to_float_nan(trade.get("entry_price"))
        exit_price = to_float_nan(trade.get("exit_price"))
        sl_price = to_float_nan(trade.get("sl_price"))
        tp_price = to_float_nan(trade.get("tp_price"))
        quantity = abs(to_float(trade.get("quantity", 0.0), 0.0))
        risk_per_unit = to_float_nan(trade.get("risk_per_unit"))
        if not math.isfinite(risk_per_unit):
            risk_per_unit = abs(entry_price - sl_price) if math.isfinite(entry_price) and math.isfinite(sl_price) else float("nan")
        klines = load_cached_klines(cache_root=cache_root, symbol=symbol, timeframe=default_timeframe)
        trade_klines, entry_idx, exit_idx = _slice_trade_window(klines=klines, entry_ts=entry_ts, exit_ts=exit_ts)
        missing: list[str] = []
        if not klines:
            missing.append("missing_symbol_klines")
        if entry_idx < 0:
            missing.append("missing_entry_bar")
        if not math.isfinite(entry_price) or entry_price <= 0:
            missing.append("missing_entry_price")

        max_favorable_price = float("nan")
        max_adverse_price = float("nan")
        mfe_per_unit = float("nan")
        mae_per_unit = float("nan")
        mfe_usdt = float("nan")
        mae_usdt = float("nan")
        mfe_r = float("nan")
        mae_r = float("nan")
        mfe_pct = float("nan")
        mae_pct = float("nan")
        bars_to_mfe = -1
        bars_to_mae = -1
        bars_to_exit = max(0, exit_idx - entry_idx) if entry_idx >= 0 and exit_idx >= entry_idx else 0
        tp_reachable = False
        sl_reachable = False
        mfe_capture_ratio = float("nan")
        mae_control_ratio = float("nan")
        analysis_status = "PASS"

        if trade_klines and math.isfinite(entry_price) and entry_price > 0:
            highs = [to_float(row.get("high", 0.0), 0.0) for row in trade_klines]
            lows = [to_float(row.get("low", 0.0), 0.0) for row in trade_klines]
            if side in {"SELL", "SHORT"}:
                min_low = min(lows) if lows else entry_price
                max_high = max(highs) if highs else entry_price
                max_favorable_price = min_low
                max_adverse_price = max_high
                mfe_per_unit = entry_price - min_low
                mae_per_unit = max_high - entry_price
                tp_reachable = any(low <= tp_price for low in lows) if math.isfinite(tp_price) and tp_price > 0 else False
                sl_reachable = any(high >= sl_price for high in highs) if math.isfinite(sl_price) and sl_price > 0 else False
                bars_to_mfe = next((idx for idx, low in enumerate(lows) if low == min_low), -1)
                bars_to_mae = next((idx for idx, high in enumerate(highs) if high == max_high), -1)
                realized_profit_per_unit = entry_price - exit_price if math.isfinite(exit_price) else float("nan")
            else:
                max_high = max(highs) if highs else entry_price
                min_low = min(lows) if lows else entry_price
                max_favorable_price = max_high
                max_adverse_price = min_low
                mfe_per_unit = max_high - entry_price
                mae_per_unit = entry_price - min_low
                tp_reachable = any(high >= tp_price for high in highs) if math.isfinite(tp_price) and tp_price > 0 else False
                sl_reachable = any(low <= sl_price for low in lows) if math.isfinite(sl_price) and sl_price > 0 else False
                bars_to_mfe = next((idx for idx, high in enumerate(highs) if high == max_high), -1)
                bars_to_mae = next((idx for idx, low in enumerate(lows) if low == min_low), -1)
                realized_profit_per_unit = exit_price - entry_price if math.isfinite(exit_price) else float("nan")

            mfe_per_unit = max(mfe_per_unit, 0.0)
            mae_per_unit = max(mae_per_unit, 0.0)
            mfe_usdt = mfe_per_unit * quantity if quantity > 0 else float("nan")
            mae_usdt = mae_per_unit * quantity if quantity > 0 else float("nan")
            mfe_r = safe_ratio(mfe_per_unit, risk_per_unit)
            mae_r = safe_ratio(mae_per_unit, risk_per_unit)
            mfe_pct = safe_ratio(mfe_per_unit, entry_price) * 100.0
            mae_pct = safe_ratio(mae_per_unit, entry_price) * 100.0
            mfe_capture_ratio = safe_ratio(realized_profit_per_unit, mfe_per_unit)
            mae_control_ratio = 1.0 - mae_r if math.isfinite(mae_r) else float("nan")
            if math.isfinite(mae_control_ratio):
                mae_control_ratio = max(-5.0, min(1.0, mae_control_ratio))
        else:
            analysis_status = "MISSING_KLINES" if "missing_symbol_klines" in missing else "PARTIAL"

        if missing and analysis_status == "PASS":
            analysis_status = "PARTIAL"

        row = {
            "trade_id": str(trade.get("trade_id", "")),
            "candidate_id": str(trade.get("candidate_id", "")),
            "symbol": symbol,
            "side": side,
            "entry_time": entry_time,
            "exit_time": exit_time,
            "entry_price": nan_to_empty(entry_price),
            "exit_price": nan_to_empty(exit_price),
            "sl_price": nan_to_empty(sl_price),
            "tp_price": nan_to_empty(tp_price),
            "quantity": quantity,
            "risk_per_unit": nan_to_empty(risk_per_unit),
            "max_favorable_price": nan_to_empty(max_favorable_price),
            "max_adverse_price": nan_to_empty(max_adverse_price),
            "mfe_usdt": nan_to_empty(mfe_usdt),
            "mae_usdt": nan_to_empty(mae_usdt),
            "mfe_r": nan_to_empty(mfe_r),
            "mae_r": nan_to_empty(mae_r),
            "mfe_pct": nan_to_empty(mfe_pct),
            "mae_pct": nan_to_empty(mae_pct),
            "bars_to_mfe": bars_to_mfe,
            "bars_to_mae": bars_to_mae,
            "bars_to_exit": bars_to_exit,
            "tp_was_reachable": tp_reachable,
            "sl_was_reachable": sl_reachable,
            "exit_efficiency_pct": nan_to_empty(to_float_nan(trade.get("exit_efficiency_pct"))),
            "mfe_capture_ratio": nan_to_empty(mfe_capture_ratio),
            "mae_control_ratio": nan_to_empty(mae_control_ratio),
            "analysis_status": analysis_status,
            "missing_fields": ";".join(sorted(set(missing))) if missing else "",
            "source_reports": str(trade.get("source_reports", "")),
        }
        rows.append(row)

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "post_entry_mfe_mae.csv"
    summary_json = out_dir / "summary.json"
    summary_md = out_dir / "summary.md"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in FIELDS})

    mfe_values = [to_float_nan(row.get("mfe_r")) for row in rows if math.isfinite(to_float_nan(row.get("mfe_r")))]
    mae_values = [to_float_nan(row.get("mae_r")) for row in rows if math.isfinite(to_float_nan(row.get("mae_r")))]
    summary = {
        "ok": True,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "total_rows": len(rows),
        "pass_count": sum(1 for row in rows if str(row.get("analysis_status", "")).upper() == "PASS"),
        "partial_count": sum(1 for row in rows if str(row.get("analysis_status", "")).upper() == "PARTIAL"),
        "missing_klines_count": sum(1 for row in rows if str(row.get("analysis_status", "")).upper() == "MISSING_KLINES"),
        "avg_mfe_r": round(sum(mfe_values) / len(mfe_values), 8) if mfe_values else float("nan"),
        "avg_mae_r": round(sum(mae_values) / len(mae_values), 8) if mae_values else float("nan"),
        "csv_path": str(csv_path),
        "summary_json": str(summary_json),
        "summary_md": str(summary_md),
    }
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Post Entry MFE/MAE Summary",
        "",
        f"- total_rows: {summary['total_rows']}",
        f"- pass_count: {summary['pass_count']}",
        f"- partial_count: {summary['partial_count']}",
        f"- missing_klines_count: {summary['missing_klines_count']}",
        f"- avg_mfe_r: {summary['avg_mfe_r']}",
        f"- avg_mae_r: {summary['avg_mae_r']}",
    ]
    summary_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Analyze post-entry MFE/MAE from cached klines")
    parser.add_argument("--lifecycle-csv", default="reports/trade_lifecycle/trade_lifecycle.csv")
    parser.add_argument("--cache-root", default="data/cache/klines")
    parser.add_argument("--output-dir", default="reports/post_entry_mfe_mae")
    parser.add_argument("--default-timeframe", default="5m")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = analyze_post_entry_mfe_mae(
        lifecycle_csv=str(args.lifecycle_csv or "reports/trade_lifecycle/trade_lifecycle.csv"),
        cache_root=str(args.cache_root or "data/cache/klines"),
        output_dir=str(args.output_dir or "reports/post_entry_mfe_mae"),
        default_timeframe=str(args.default_timeframe or "5m"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"total_rows={result.get('total_rows', 0)}")
    print(f"csv_path={result.get('csv_path', '')}")


if __name__ == "__main__":
    main()
