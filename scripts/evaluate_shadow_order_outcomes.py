from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from core.public_market_data import fetch_binance_spot_klines_public_since
from core.signal_outcome import (
    build_shadow_order_outcome_rows,
    parse_shadow_order_plan,
    summarize_shadow_order_outcomes,
)
from scripts.shadow_order_outcome_common import calculate_shadow_order_metrics


def _parse_horizons(value: str) -> list[int]:
    text = str(value or "").strip()
    if not text:
        return [30, 60, 120]
    rows: list[int] = []
    for item in text.split(","):
        raw = item.strip()
        if not raw:
            continue
        try:
            number = int(raw)
        except ValueError:
            continue
        if number > 0:
            rows.append(number)
    rows = sorted(set(rows))
    return rows or [30, 60, 120]


def _load_shadow_order_plans(path: str) -> list[dict[str, Any]]:
    file_path = Path(path)
    if not file_path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in file_path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text:
            continue
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def _write_outcomes_csv(path: str, rows: list[dict[str, Any]]) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    headers = [
        "order_key",
        "symbol",
        "side",
        "entry_timestamp",
        "entry_timestamp_ms",
        "entry_price",
        "stop_loss",
        "take_profit",
        "horizon_bars",
        "outcome_status",
        "future_bars_status",
        "exit_reason",
        "order_level_exit_reason",
        "hit_take_profit",
        "hit_stop_loss",
        "bars_to_exit",
        "realized_return_pct",
        "realized_r",
        "mfe",
        "mae",
        "max_high",
        "min_low",
        "final_close",
        "fetched_future_bars",
        "first_future_bar_timestamp",
        "last_future_bar_timestamp",
        "order_plan_status",
        "skip_reason",
        "source_order_plan_raw",
    ]
    with file_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in headers})


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return int(default)


def _interval_ms(timeframe: str) -> int:
    text = str(timeframe or "5m").strip().lower()
    if not text:
        return 5 * 60 * 1000
    unit = text[-1]
    number = _to_int(text[:-1], 1)
    if unit == "m":
        return max(1, number) * 60 * 1000
    if unit == "h":
        return max(1, number) * 60 * 60 * 1000
    if unit == "d":
        return max(1, number) * 24 * 60 * 60 * 1000
    return 5 * 60 * 1000


def _align_to_next_open(entry_time_ms: int, timeframe: str) -> int:
    step = _interval_ms(timeframe)
    if entry_time_ms <= 0:
        return step
    slot = (entry_time_ms // step) * step
    return slot + step


def _build_failed_rows(
    *,
    plan: dict[str, Any],
    horizons: list[int],
    outcome_status: str,
    skip_reason: str,
    fetched_future_bars: int = 0,
    first_future_bar_timestamp: Any = None,
    last_future_bar_timestamp: Any = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for horizon in list(horizons or [30]):
        rows.append(
            {
                "order_key": (
                    f"{str(plan.get('symbol', '')).strip().upper()}|"
                    f"{int(plan.get('entry_timestamp_ms', 0) or 0)}|"
                    f"{float(plan.get('entry_price', 0.0) or 0.0):.10f}"
                ),
                "symbol": plan.get("symbol", ""),
                "side": plan.get("side", "LONG"),
                "entry_timestamp": plan.get("entry_timestamp", ""),
                "entry_timestamp_ms": plan.get("entry_timestamp_ms", 0),
                "entry_price": plan.get("entry_price", 0.0),
                "stop_loss": plan.get("stop_loss", 0.0),
                "take_profit": plan.get("take_profit", 0.0),
                "horizon_bars": int(horizon),
                "outcome_status": outcome_status,
                "future_bars_status": "n/a",
                "exit_reason": "open",
                "order_level_exit_reason": "open",
                "hit_take_profit": False,
                "hit_stop_loss": False,
                "bars_to_exit": 0,
                "realized_return_pct": 0.0,
                "realized_r": 0.0,
                "mfe": 0.0,
                "mae": 0.0,
                "max_high": float(plan.get("entry_price", 0.0) or 0.0),
                "min_low": float(plan.get("entry_price", 0.0) or 0.0),
                "final_close": float(plan.get("entry_price", 0.0) or 0.0),
                "fetched_future_bars": int(fetched_future_bars),
                "first_future_bar_timestamp": first_future_bar_timestamp,
                "last_future_bar_timestamp": last_future_bar_timestamp,
                "order_plan_status": plan.get("order_plan_status", ""),
                "skip_reason": skip_reason,
                "source_order_plan_raw": json.dumps(plan.get("source_order_plan_raw", {}), ensure_ascii=False),
            }
        )
    return rows


def evaluate_shadow_order_outcomes(
    *,
    shadow_order_plan_path: str,
    output_csv: str,
    market_data_source: str,
    horizon_bars: list[int],
    timeframe: str,
    debug: bool = False,
    execute_fetch: bool = False,
) -> dict[str, Any]:
    source = str(market_data_source or "binance_public").strip().lower()
    if source != "binance_public":
        raise ValueError("only binance_public is supported for shadow outcome evaluation")
    plans_raw = _load_shadow_order_plans(shadow_order_plan_path)
    resolved_horizons = _parse_horizons(",".join(str(item) for item in list(horizon_bars or [])))
    requested_limit = max(resolved_horizons) + 5 if resolved_horizons else 125
    dedup_skipped_count = 0

    rows: list[dict[str, Any]] = []
    seen_keys: set[tuple[str, int, str]] = set()
    unique_count = 0
    invalid_count = 0
    failed_order_keys: set[tuple[str, int, str]] = set()
    for raw_plan in plans_raw:
        parsed = parse_shadow_order_plan(raw_plan if isinstance(raw_plan, dict) else {})
        if not bool(parsed.get("ok", False)):
            invalid_count += 1
            error = str(parsed.get("error", "missing_required_field") or "missing_required_field")
            fallback_plan = {
                "symbol": str((raw_plan or {}).get("symbol", "")).strip().upper(),
                "side": "LONG",
                "entry_timestamp": "",
                "entry_timestamp_ms": 0,
                "entry_price": 0.0,
                "stop_loss": 0.0,
                "take_profit": 0.0,
                "order_plan_status": str((raw_plan or {}).get("order_plan_status", "")).strip(),
                "source_order_plan_raw": dict(raw_plan or {}),
            }
            rows.extend(
                _build_failed_rows(
                    plan=fallback_plan,
                    horizons=resolved_horizons,
                    outcome_status=error,
                    skip_reason=error,
                )
            )
            continue
        plan = dict(parsed.get("plan", {}))
        key = (
            str(plan.get("symbol", "")),
            int(plan.get("entry_timestamp_ms", 0) or 0),
            f"{float(plan.get('entry_price', 0.0) or 0.0):.10f}",
        )
        if key in seen_keys:
            dedup_skipped_count += 1
            continue
        seen_keys.add(key)
        unique_count += 1

        symbol = str(plan.get("symbol", "")).strip().upper()
        entry_ts = int(plan.get("entry_timestamp_ms", 0) or 0)
        tf = str(plan.get("timeframe", timeframe)).strip() or str(timeframe or "5m")
        fetch_start_time_ms = _align_to_next_open(entry_ts, tf)
        fetch_end_time_ms = fetch_start_time_ms + (_interval_ms(tf) * requested_limit)
        if not bool(execute_fetch):
            rows.extend(
                _build_failed_rows(
                    plan=plan,
                    horizons=resolved_horizons,
                    outcome_status="fetch_disabled",
                    skip_reason="network_fetch_disabled_without_execute_flag",
                )
            )
            failed_order_keys.add(key)
            if debug:
                print(
                    "debug shadow_outcome "
                    f"symbol={symbol} outcome_status=fetch_disabled "
                    "skip_reason=network_fetch_disabled_without_execute_flag",
                    flush=True,
                )
            continue

        kline_resp = fetch_binance_spot_klines_public_since(
            symbol=symbol,
            interval=tf,
            start_time_ms=fetch_start_time_ms,
            limit=requested_limit,
            end_time_ms=fetch_end_time_ms,
        )
        klines = [
            row
            for row in list(kline_resp.get("klines", []))
            if _to_int(row.get("timestamp", 0)) > entry_ts
        ]
        fetch_ok = bool(kline_resp.get("success", False))
        first_ts = _to_int(klines[0].get("timestamp"), 0) if klines else None
        last_ts = _to_int(klines[-1].get("timestamp"), 0) if klines else None
        if not fetch_ok:
            rows.extend(
                _build_failed_rows(
                    plan=plan,
                    horizons=resolved_horizons,
                    outcome_status="fetch_failed",
                    skip_reason=str(kline_resp.get("error", "fetch_failed") or "fetch_failed"),
                    fetched_future_bars=len(klines),
                    first_future_bar_timestamp=first_ts,
                    last_future_bar_timestamp=last_ts,
                )
            )
            failed_order_keys.add(key)
            if debug:
                print(
                    "debug shadow_outcome "
                    f"symbol={symbol} raw_timestamp={plan.get('raw_timestamp', '')} "
                    f"parsed_entry_timestamp_ms={entry_ts} entry_price={plan.get('entry_price', 0.0)} "
                    f"stop_loss={plan.get('stop_loss', 0.0)} take_profit={plan.get('take_profit', 0.0)} "
                    f"fetch_start_time_ms={fetch_start_time_ms} fetch_end_time_ms={fetch_end_time_ms} "
                    f"fetched_future_bars={len(klines)} first_future_bar_timestamp={first_ts} "
                    f"last_future_bar_timestamp={last_ts} outcome_status=fetch_failed "
                    f"skip_reason={kline_resp.get('error', '')}",
                    flush=True,
                )
            continue

        outcome_rows = build_shadow_order_outcome_rows(
            order_plan=plan,
            future_klines=klines,
            horizons=resolved_horizons,
        )
        for row in outcome_rows:
            row["fetched_future_bars"] = len(klines)
            row["first_future_bar_timestamp"] = first_ts
            row["last_future_bar_timestamp"] = last_ts
            if str(row.get("outcome_status", "")) in {"ok", "insufficient_future_bars"}:
                row["skip_reason"] = ""
        if len(outcome_rows) == 0:
            outcome_rows = _build_failed_rows(
                plan=plan,
                horizons=resolved_horizons,
                outcome_status="missing_required_field",
                skip_reason="unable_to_build_outcome_rows",
                fetched_future_bars=len(klines),
                first_future_bar_timestamp=first_ts,
                last_future_bar_timestamp=last_ts,
            )
            failed_order_keys.add(key)
        rows.extend(outcome_rows)
        if debug:
            statuses = sorted({str(item.get("outcome_status", "")).strip() for item in outcome_rows if str(item.get("outcome_status", "")).strip()})
            status_label = statuses[0] if len(statuses) == 1 else "mixed"
            print(
                "debug shadow_outcome "
                f"symbol={symbol} raw_timestamp={plan.get('raw_timestamp', '')} "
                f"parsed_entry_timestamp_ms={entry_ts} entry_price={plan.get('entry_price', 0.0)} "
                f"stop_loss={plan.get('stop_loss', 0.0)} take_profit={plan.get('take_profit', 0.0)} "
                f"fetch_start_time_ms={fetch_start_time_ms} fetch_end_time_ms={fetch_end_time_ms} "
                f"fetched_future_bars={len(klines)} first_future_bar_timestamp={first_ts} "
                f"last_future_bar_timestamp={last_ts} outcome_status={status_label} "
                f"horizon_statuses={'|'.join(statuses)} skip_reason=",
                flush=True,
            )

    _write_outcomes_csv(output_csv, rows)
    summary = summarize_shadow_order_outcomes(rows, total_orders=unique_count)
    offline_metrics = calculate_shadow_order_metrics(rows)
    summary["dedup_skipped_count"] = int(dedup_skipped_count)
    summary["failed_orders"] = max(0, int(unique_count) - int(summary.get("evaluated_orders", 0)))
    return {
        "shadow_order_plan_path": shadow_order_plan_path,
        "output_csv": output_csv,
        "market_data_source": source,
        "timeframe": timeframe,
        "horizon_bars": list(resolved_horizons),
        "total_raw_orders": len(plans_raw),
        "total_orders": unique_count,
        "dedup_skipped_count": int(dedup_skipped_count),
        "invalid_order_plans": int(invalid_count),
        "failed_orders": int(summary.get("failed_orders", 0)),
        "rows_count": len(rows),
        "execute_fetch": bool(execute_fetch),
        "network_enabled": bool(execute_fetch),
        "offline_metrics": offline_metrics,
        "summary": summary,
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate shadow order plan outcomes from jsonl")
    parser.add_argument("--shadow-order-plan-path", default="logs/shadow_order_plans.jsonl")
    parser.add_argument("--output-csv", default="logs/shadow_order_outcomes.csv")
    parser.add_argument("--market-data-source", default="binance_public")
    parser.add_argument("--horizon-bars", default="30,60,120")
    parser.add_argument("--timeframe", default="5m")
    parser.add_argument("--execute-fetch", action="store_true")
    parser.add_argument("--debug", action="store_true")
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    horizons = _parse_horizons(str(args.horizon_bars or "30,60,120"))
    result = evaluate_shadow_order_outcomes(
        shadow_order_plan_path=str(args.shadow_order_plan_path or "logs/shadow_order_plans.jsonl"),
        output_csv=str(args.output_csv or "logs/shadow_order_outcomes.csv"),
        market_data_source=str(args.market_data_source or "binance_public"),
        horizon_bars=horizons,
        timeframe=str(args.timeframe or "5m"),
        debug=bool(args.debug),
        execute_fetch=bool(args.execute_fetch),
    )
    summary = dict(result.get("summary", {}))
    print(f"total_orders={summary.get('total_orders', result.get('total_orders', 0))}")
    print(f"unique_orders={summary.get('unique_orders', summary.get('evaluated_orders', 0))}")
    print(f"horizon_rows={summary.get('horizon_rows', result.get('rows_count', 0))}")
    print(f"evaluated_horizon_rows={summary.get('evaluated_horizon_rows', 0)}")
    print(f"evaluated_orders={summary.get('evaluated_orders', 0)}")
    print(f"order_level_tp_count={summary.get('order_level_tp_count', 0)}")
    print(f"order_level_sl_count={summary.get('order_level_sl_count', 0)}")
    print(f"order_level_open_count={summary.get('order_level_open_count', 0)}")
    print(f"order_level_win_rate={summary.get('order_level_win_rate', 0.0)}")
    print(f"horizon_level_tp_count={summary.get('horizon_level_tp_count', 0)}")
    print(f"horizon_level_sl_count={summary.get('horizon_level_sl_count', 0)}")
    print(f"horizon_level_open_count={summary.get('horizon_level_open_count', 0)}")
    print(f"horizon_level_win_rate={summary.get('horizon_level_win_rate', 0.0)}")
    print(f"order_level_expectancy_r={summary.get('order_level_expectancy_r', 0.0)}")
    print(f"horizon_level_expectancy_r={summary.get('horizon_level_expectancy_r', 0.0)}")
    print(f"avg_realized_r={summary.get('avg_realized_r', 0.0)}")
    print(f"avg_mfe={summary.get('avg_mfe', 0.0)}")
    print(f"avg_mae={summary.get('avg_mae', 0.0)}")
    print(f"win_rate={summary.get('win_rate', 0.0)}")
    print(f"expectancy_r={summary.get('expectancy_r', 0.0)}")
    print(f"output_csv={result.get('output_csv', '')}")


if __name__ == "__main__":
    main()
