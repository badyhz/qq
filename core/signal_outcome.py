from __future__ import annotations

from datetime import datetime, timezone
import json
from typing import Any, Optional


def evaluate_signal_forward_outcome(
    *,
    signal: dict[str, Any],
    future_klines: list[dict[str, Any]],
    horizons: Optional[list[int]] = None,
    exit_params: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    row = dict(signal or {})
    resolved_horizons = _normalize_horizons(horizons)
    symbol = str(row.get("symbol", "")).strip().upper()
    side_hint = str(row.get("side", row.get("direction", "LONG"))).strip().upper()
    side = "SHORT" if side_hint in {"SHORT", "SELL"} else "LONG"
    entry_price = _to_float(row.get("entry_price", row.get("entry", row.get("reference_price", 0.0))))
    stop_loss = _to_float(row.get("stop_loss", row.get("stop", 0.0)))
    take_profit = _to_float(row.get("take_profit", row.get("tp", 0.0)))
    signal_time = row.get("timestamp", row.get("signal_time", ""))
    warnings: list[str] = []
    resolved_exit = _resolve_exit_params(exit_params)

    if not isinstance(row, dict) or row == {}:
        warnings.append("invalid_signal_payload")
    if entry_price <= 0:
        warnings.append("missing_entry_price")
    risk_distance = entry_price - stop_loss
    if resolved_exit["rr_target"] is not None and risk_distance > 0:
        take_profit = entry_price + risk_distance * float(resolved_exit["rr_target"])
    normalized_future = [_normalize_kline(item) for item in list(future_klines or []) if isinstance(item, dict)]

    results: dict[str, Any] = {}
    for horizon in resolved_horizons:
        clipped = normalized_future[:horizon]
        if len(clipped) < horizon:
            warnings.append(f"insufficient_future_bars:{horizon}")
        outcome = _compute_outcome_for_horizon(
            side=side,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            rows=clipped,
            horizon=horizon,
            exit_params=resolved_exit,
        )
        results[str(horizon)] = outcome

    return {
        "symbol": symbol,
        "side": side,
        "entry_price": entry_price,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "signal_time": str(signal_time or ""),
        "horizons": resolved_horizons,
        "per_horizon_results": results,
        "warnings": list(dict.fromkeys(warnings)),
        "exit_params": resolved_exit,
    }


def summarize_outcomes_by_horizon(
    *,
    outcomes: list[dict[str, Any]],
    horizons: Optional[list[int]] = None,
) -> dict[str, Any]:
    resolved_horizons = _normalize_horizons(horizons)
    rows: dict[str, Any] = {}
    for horizon in resolved_horizons:
        key = str(horizon)
        return_values: list[float] = []
        mfe_values: list[float] = []
        mae_values: list[float] = []
        tp_hits = 0
        sl_hits = 0
        breakeven_hits = 0
        trail_stop_hits = 0
        expectancy_r_values: list[float] = []
        total = 0
        for outcome in list(outcomes or []):
            if not isinstance(outcome, dict):
                continue
            per = outcome.get("per_horizon_results", {})
            if not isinstance(per, dict):
                continue
            item = per.get(key)
            if not isinstance(item, dict):
                continue
            total += 1
            if bool(item.get("hit_take_profit", False)):
                tp_hits += 1
            if bool(item.get("hit_stop_loss", False)):
                sl_hits += 1
            if bool(item.get("hit_breakeven_stop", False)):
                breakeven_hits += 1
            if bool(item.get("hit_trailing_stop", False)):
                trail_stop_hits += 1
            return_values.append(_to_float(item.get("return_at_horizon_pct", 0.0)))
            mfe_values.append(_to_float(item.get("max_favorable_excursion_pct", 0.0)))
            mae_values.append(_to_float(item.get("max_adverse_excursion_pct", 0.0)))
            expectancy_r_values.append(_to_float(item.get("realized_r", 0.0)))
        rows[key] = {
            "horizon": int(horizon),
            "candidate_count": total,
            "avg_return_at_horizon": round(sum(return_values) / len(return_values), 6) if return_values else 0.0,
            "tp_hit_rate": round(tp_hits / total, 6) if total > 0 else 0.0,
            "sl_hit_rate": round(sl_hits / total, 6) if total > 0 else 0.0,
            "breakeven_hit_rate": round(breakeven_hits / total, 6) if total > 0 else 0.0,
            "trail_stop_hit_rate": round(trail_stop_hits / total, 6) if total > 0 else 0.0,
            "avg_mfe": round(sum(mfe_values) / len(mfe_values), 6) if mfe_values else 0.0,
            "avg_mae": round(sum(mae_values) / len(mae_values), 6) if mae_values else 0.0,
            "expectancy_r": round(sum(expectancy_r_values) / len(expectancy_r_values), 6) if expectancy_r_values else 0.0,
            "avg_realized_r": round(sum(expectancy_r_values) / len(expectancy_r_values), 6) if expectancy_r_values else 0.0,
        }
    return rows


def summarize_outcomes_for_primary_horizon(
    *,
    outcomes: list[dict[str, Any]],
    primary_horizon: int,
) -> dict[str, Any]:
    key = str(max(1, int(primary_horizon)))
    count = 0
    tp_hits = 0
    sl_hits = 0
    avg_return_values: list[float] = []
    avg_mfe_values: list[float] = []
    avg_mae_values: list[float] = []
    avg_realized_r_values: list[float] = []
    oi_values: list[float] = []
    taker_values: list[float] = []
    funding_values: list[float] = []

    for outcome in list(outcomes or []):
        if not isinstance(outcome, dict):
            continue
        per = outcome.get("per_horizon_results", {})
        if not isinstance(per, dict):
            continue
        item = per.get(key)
        if not isinstance(item, dict):
            continue
        count += 1
        if bool(item.get("hit_take_profit", False)):
            tp_hits += 1
        if bool(item.get("hit_stop_loss", False)):
            sl_hits += 1
        avg_return_values.append(_to_float(item.get("return_at_horizon_pct", 0.0), default=0.0))
        avg_mfe_values.append(_to_float(item.get("max_favorable_excursion_pct", 0.0), default=0.0))
        avg_mae_values.append(_to_float(item.get("max_adverse_excursion_pct", 0.0), default=0.0))
        avg_realized_r_values.append(_to_float(item.get("realized_r", 0.0), default=0.0))
        oi_v = _to_optional_float(outcome.get("oi_change_pct"))
        taker_v = _to_optional_float(outcome.get("taker_buy_ratio"))
        funding_v = _to_optional_float(outcome.get("funding_rate"))
        if oi_v is not None:
            oi_values.append(oi_v)
        if taker_v is not None:
            taker_values.append(taker_v)
        if funding_v is not None:
            funding_values.append(funding_v)

    tp_hit_rate = (tp_hits / count) if count > 0 else 0.0
    sl_hit_rate = (sl_hits / count) if count > 0 else 0.0
    return {
        "candidate_count": int(count),
        "expectancy_r": round(sum(avg_realized_r_values) / len(avg_realized_r_values), 6) if avg_realized_r_values else 0.0,
        "avg_realized_r": round(sum(avg_realized_r_values) / len(avg_realized_r_values), 6) if avg_realized_r_values else 0.0,
        "tp_hit_rate": round(tp_hit_rate, 6),
        "sl_hit_rate": round(sl_hit_rate, 6),
        "tp_sl_balance": round(tp_hit_rate - sl_hit_rate, 6),
        "avg_return_at_horizon": round(sum(avg_return_values) / len(avg_return_values), 6) if avg_return_values else 0.0,
        "avg_mfe": round(sum(avg_mfe_values) / len(avg_mfe_values), 6) if avg_mfe_values else 0.0,
        "avg_mae": round(sum(avg_mae_values) / len(avg_mae_values), 6) if avg_mae_values else 0.0,
        "avg_oi_change_pct": round(sum(oi_values) / len(oi_values), 6) if oi_values else None,
        "avg_taker_buy_ratio": round(sum(taker_values) / len(taker_values), 6) if taker_values else None,
        "avg_funding_rate": round(sum(funding_values) / len(funding_values), 9) if funding_values else None,
    }


def summarize_outcomes_by_symbol(
    *,
    outcomes: list[dict[str, Any]],
    primary_horizon: int,
) -> list[dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = {}
    for outcome in list(outcomes or []):
        if not isinstance(outcome, dict):
            continue
        symbol = str(outcome.get("symbol", "")).strip().upper()
        if not symbol:
            continue
        buckets.setdefault(symbol, []).append(outcome)
    rows: list[dict[str, Any]] = []
    for symbol, grouped in buckets.items():
        row = summarize_outcomes_for_primary_horizon(outcomes=grouped, primary_horizon=primary_horizon)
        rows.append({"symbol": symbol, **row})
    rows.sort(key=lambda item: (int(item.get("candidate_count", 0)), float(item.get("expectancy_r", 0.0))), reverse=True)
    return rows


def summarize_outcomes_by_time_bucket(
    *,
    outcomes: list[dict[str, Any]],
    primary_horizon: int,
    bucket_seconds: int = 24 * 60 * 60,
) -> list[dict[str, Any]]:
    resolved_bucket_seconds = max(60, int(bucket_seconds))
    buckets: dict[str, list[dict[str, Any]]] = {}
    for outcome in list(outcomes or []):
        if not isinstance(outcome, dict):
            continue
        ts_ms = _to_epoch_ms(outcome.get("signal_time", outcome.get("timestamp")))
        if ts_ms <= 0:
            continue
        bucket_start_ms = (ts_ms // (resolved_bucket_seconds * 1000)) * (resolved_bucket_seconds * 1000)
        bucket_start = datetime.fromtimestamp(bucket_start_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
        buckets.setdefault(bucket_start, []).append(outcome)
    rows: list[dict[str, Any]] = []
    for bucket_start, grouped in sorted(buckets.items(), key=lambda item: item[0]):
        row = summarize_outcomes_for_primary_horizon(outcomes=grouped, primary_horizon=primary_horizon)
        rows.append({"date": bucket_start, "bucket_start": bucket_start, **row})
    return rows


def normalize_shadow_order_plan(plan: dict[str, Any]) -> Optional[dict[str, Any]]:
    parsed = parse_shadow_order_plan(plan)
    if not bool(parsed.get("ok", False)):
        return None
    return dict(parsed.get("plan", {}))


def parse_shadow_order_plan(plan: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(plan, dict):
        return {"ok": False, "error": "missing_required_field", "plan": None}
    payload_candidate = plan.get("payload")
    base = payload_candidate if isinstance(payload_candidate, dict) and len(payload_candidate) > 0 else plan
    symbol = str(base.get("symbol", plan.get("symbol", ""))).strip().upper()
    side_hint = str(base.get("position_side", base.get("side", plan.get("side", "LONG")))).strip().upper()
    side = "SHORT" if side_hint in {"SHORT", "SELL"} else "LONG"
    timeframe = str(base.get("timeframe", plan.get("timeframe", "5m"))).strip() or "5m"
    timestamp_raw = base.get(
        "timestamp",
        plan.get("timestamp", plan.get("entry_timestamp_ms", plan.get("entry_timestamp", ""))),
    )
    entry_timestamp_ms = _to_epoch_ms(timestamp_raw)
    entry_price = _to_float(base.get("entry_price", plan.get("entry_price", base.get("entry", plan.get("entry", 0.0)))))
    stop_loss = _to_float(base.get("stop_loss", plan.get("stop_loss", base.get("stop", plan.get("stop", 0.0)))))
    take_profit = _to_float(base.get("take_profit", plan.get("take_profit", base.get("tp", plan.get("tp", 0.0)))))
    if entry_timestamp_ms <= 0:
        return {"ok": False, "error": "timestamp_parse_failed", "plan": None}
    if (not symbol) or entry_price <= 0 or stop_loss <= 0 or take_profit <= 0:
        return {"ok": False, "error": "missing_required_field", "plan": None}
    return {
        "ok": True,
        "error": "",
        "plan": {
            "symbol": symbol,
            "side": side,
            "timeframe": timeframe,
            "raw_timestamp": timestamp_raw,
            "entry_timestamp": _to_iso(entry_timestamp_ms),
            "entry_timestamp_ms": entry_timestamp_ms,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "order_plan_status": str(plan.get("order_plan_status", base.get("order_plan_status", ""))).strip(),
            "source_order_plan_raw": dict(plan),
        },
    }


def dedupe_shadow_order_plans(order_plans: list[dict[str, Any]]) -> dict[str, Any]:
    unique: list[dict[str, Any]] = []
    seen: set[tuple[str, int, str]] = set()
    duplicates = 0
    invalid = 0
    for raw in list(order_plans or []):
        normalized = normalize_shadow_order_plan(raw if isinstance(raw, dict) else {})
        if normalized is None:
            invalid += 1
            continue
        key = (
            str(normalized.get("symbol", "")),
            int(normalized.get("entry_timestamp_ms", 0)),
            f"{_to_float(normalized.get('entry_price', 0.0)):.10f}",
        )
        if key in seen:
            duplicates += 1
            continue
        seen.add(key)
        unique.append(normalized)
    return {
        "unique_order_plans": unique,
        "duplicates_removed": duplicates,
        "invalid_order_plans": invalid,
    }


def build_shadow_order_outcome_rows(
    *,
    order_plan: dict[str, Any],
    future_klines: list[dict[str, Any]],
    horizons: Optional[list[int]] = None,
) -> list[dict[str, Any]]:
    plan = normalize_shadow_order_plan(order_plan)
    if plan is None:
        return []
    resolved_horizons = _normalize_horizons(horizons)
    entry_ts = int(plan.get("entry_timestamp_ms", 0))
    future_rows = []
    for row in list(future_klines or []):
        if not isinstance(row, dict):
            continue
        ts = _to_epoch_ms(row.get("timestamp"))
        if ts <= entry_ts:
            continue
        future_rows.append(row)
    outcome = evaluate_signal_forward_outcome(
        signal={
            "symbol": plan["symbol"],
            "side": plan["side"],
            "entry_price": plan["entry_price"],
            "stop_loss": plan["stop_loss"],
            "take_profit": plan["take_profit"],
            "timestamp": plan["entry_timestamp"],
        },
        future_klines=future_rows,
        horizons=resolved_horizons,
    )
    per_h = outcome.get("per_horizon_results", {}) if isinstance(outcome, dict) else {}
    rows: list[dict[str, Any]] = []
    order_key = (
        f"{plan['symbol']}|{int(plan['entry_timestamp_ms'])}|"
        f"{_to_float(plan['entry_price'], default=0.0):.10f}"
    )
    for horizon in resolved_horizons:
        key = str(horizon)
        item = per_h.get(key, {}) if isinstance(per_h, dict) else {}
        first_hit = str(item.get("first_hit", "none"))
        if first_hit == "take_profit_first":
            exit_reason = "take_profit"
        elif first_hit == "stop_loss_first":
            exit_reason = "stop_loss"
        else:
            exit_reason = "open"
        bars_used = int(item.get("bars_used", 0) or 0)
        horizon_int = int(horizon)
        first_hit_exists = first_hit in {"take_profit_first", "stop_loss_first"}
        outcome_status = "ok"
        future_bars_status = "complete"
        if bars_used < horizon_int:
            if first_hit_exists:
                outcome_status = "ok"
                future_bars_status = "insufficient_but_exit_resolved"
            else:
                outcome_status = "insufficient_future_bars"
                future_bars_status = "insufficient"
        rows.append(
            {
                "order_key": order_key,
                "symbol": plan["symbol"],
                "side": plan["side"],
                "entry_timestamp": plan["entry_timestamp"],
                "entry_timestamp_ms": int(plan["entry_timestamp_ms"]),
                "entry_price": plan["entry_price"],
                "stop_loss": plan["stop_loss"],
                "take_profit": plan["take_profit"],
                "horizon_bars": horizon_int,
                "exit_reason": exit_reason,
                "hit_take_profit": bool(item.get("hit_take_profit", False)),
                "hit_stop_loss": bool(item.get("hit_stop_loss", False)),
                "bars_to_exit": int(item.get("bars_to_first_hit", 0) or 0),
                "realized_return_pct": _to_float(item.get("realized_return_pct", 0.0)),
                "realized_r": _to_float(item.get("realized_r", 0.0)),
                "mfe": _to_float(item.get("max_favorable_excursion_pct", 0.0)),
                "mae": _to_float(item.get("max_adverse_excursion_pct", 0.0)),
                "max_high": _to_float(item.get("highest_high", plan["entry_price"])),
                "min_low": _to_float(item.get("lowest_low", plan["entry_price"])),
                "final_close": _to_float(item.get("close_at_horizon", plan["entry_price"])),
                "order_plan_status": plan.get("order_plan_status", ""),
                "outcome_status": outcome_status,
                "future_bars_status": future_bars_status,
                "fetched_future_bars": len(future_rows),
                "first_future_bar_timestamp": _to_epoch_ms(future_rows[0].get("timestamp")) if future_rows else None,
                "last_future_bar_timestamp": _to_epoch_ms(future_rows[-1].get("timestamp")) if future_rows else None,
                "order_level_exit_reason": "",
                "skip_reason": "",
                "source_order_plan_raw": json.dumps(plan.get("source_order_plan_raw", {}), ensure_ascii=False),
            }
        )
    return rows


def summarize_shadow_order_outcomes(outcome_rows: list[dict[str, Any]], total_orders: int) -> dict[str, Any]:
    rows = [row for row in list(outcome_rows or []) if isinstance(row, dict)]
    horizon_rows = len(rows)
    evaluable_rows = [row for row in rows if str(row.get("outcome_status", "")).strip() in {"ok", "insufficient_future_bars"}]
    evaluated_horizon_rows = len(evaluable_rows)

    def _build_order_key(row: dict[str, Any]) -> str:
        explicit = str(row.get("order_key", "")).strip()
        if explicit:
            return explicit
        return (
            f"{str(row.get('symbol', '')).strip().upper()}|"
            f"{int(_to_epoch_ms(row.get('entry_timestamp_ms', row.get('entry_timestamp'))))}|"
            f"{_to_float(row.get('entry_price', 0.0)):.10f}"
        )

    order_buckets: dict[str, list[dict[str, Any]]] = {}
    for row in evaluable_rows:
        key = _build_order_key(row)
        order_buckets.setdefault(key, []).append(row)

    order_level_realized_r_values: list[float] = []
    order_level_mfe_values: list[float] = []
    order_level_mae_values: list[float] = []
    order_level_tp_count = 0
    order_level_sl_count = 0
    order_level_open_count = 0
    for key, grouped in order_buckets.items():
        has_tp = any(bool(item.get("hit_take_profit", False)) for item in grouped)
        has_sl = any(bool(item.get("hit_stop_loss", False)) for item in grouped)
        if has_tp:
            order_exit_reason = "take_profit"
            order_level_tp_count += 1
        elif has_sl:
            order_exit_reason = "stop_loss"
            order_level_sl_count += 1
        else:
            order_exit_reason = "open"
            order_level_open_count += 1

        exit_candidates = [item for item in grouped if int(item.get("bars_to_exit", 0) or 0) > 0]
        if exit_candidates:
            selected = min(
                exit_candidates,
                key=lambda item: (
                    int(item.get("bars_to_exit", 10**9) or 10**9),
                    int(item.get("horizon_bars", 10**9) or 10**9),
                ),
            )
        else:
            selected = max(grouped, key=lambda item: int(item.get("horizon_bars", 0) or 0))
        selected_r = _to_float(selected.get("realized_r", 0.0))
        selected_mfe = _to_float(selected.get("mfe", 0.0))
        selected_mae = _to_float(selected.get("mae", 0.0))
        order_level_realized_r_values.append(selected_r)
        order_level_mfe_values.append(selected_mfe)
        order_level_mae_values.append(selected_mae)
        for row in grouped:
            row["order_level_exit_reason"] = order_exit_reason

    horizon_level_tp_count = sum(1 for row in evaluable_rows if str(row.get("exit_reason", "")) == "take_profit")
    horizon_level_sl_count = sum(1 for row in evaluable_rows if str(row.get("exit_reason", "")) == "stop_loss")
    horizon_level_open_count = sum(1 for row in evaluable_rows if str(row.get("exit_reason", "")) == "open")

    order_level_expectancy_r = (
        sum(order_level_realized_r_values) / len(order_level_realized_r_values)
        if order_level_realized_r_values
        else 0.0
    )
    horizon_level_expectancy_r = (
        sum(_to_float(row.get("realized_r", 0.0)) for row in evaluable_rows) / len(evaluable_rows)
        if evaluable_rows
        else 0.0
    )
    order_level_win_count = sum(1 for value in order_level_realized_r_values if value > 0)
    horizon_level_win_count = sum(1 for row in evaluable_rows if _to_float(row.get("realized_r", 0.0)) > 0)
    unique_orders = len(order_buckets)
    failed_orders = max(0, int(total_orders) - int(unique_orders))
    return {
        "total_orders": int(total_orders),
        "unique_orders": int(unique_orders),
        "horizon_rows": int(horizon_rows),
        "evaluated_horizon_rows": int(evaluated_horizon_rows),
        "evaluated_orders": int(unique_orders),
        "failed_orders": int(failed_orders),
        "order_level_tp_count": int(order_level_tp_count),
        "order_level_sl_count": int(order_level_sl_count),
        "order_level_open_count": int(order_level_open_count),
        "order_level_win_rate": round((order_level_win_count / unique_orders), 6) if unique_orders > 0 else 0.0,
        "horizon_level_tp_count": int(horizon_level_tp_count),
        "horizon_level_sl_count": int(horizon_level_sl_count),
        "horizon_level_open_count": int(horizon_level_open_count),
        "horizon_level_win_rate": (
            round((horizon_level_win_count / evaluated_horizon_rows), 6) if evaluated_horizon_rows > 0 else 0.0
        ),
        "order_level_expectancy_r": round(order_level_expectancy_r, 6),
        "horizon_level_expectancy_r": round(horizon_level_expectancy_r, 6),
        "avg_realized_r": round(order_level_expectancy_r, 6),
        "avg_mfe": (
            round(sum(order_level_mfe_values) / len(order_level_mfe_values), 6) if order_level_mfe_values else 0.0
        ),
        "avg_mae": (
            round(sum(order_level_mae_values) / len(order_level_mae_values), 6) if order_level_mae_values else 0.0
        ),
        "win_rate": round((order_level_win_count / unique_orders), 6) if unique_orders > 0 else 0.0,
        "expectancy_r": round(order_level_expectancy_r, 6),
        "tp_count": int(order_level_tp_count),
        "sl_count": int(order_level_sl_count),
        "open_count": int(order_level_open_count),
    }


def _compute_outcome_for_horizon(
    *,
    side: str,
    entry_price: float,
    stop_loss: float,
    take_profit: float,
    rows: list[dict[str, Any]],
    horizon: int,
    exit_params: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    resolved_exit = _resolve_exit_params(exit_params)
    if entry_price <= 0:
        return {
            "horizon": int(horizon),
            "bars_used": len(rows),
            "max_favorable_excursion_pct": 0.0,
            "max_adverse_excursion_pct": 0.0,
            "highest_high": 0.0,
            "lowest_low": 0.0,
            "close_at_horizon": 0.0,
            "return_at_horizon_pct": 0.0,
            "hit_take_profit": False,
            "hit_stop_loss": False,
            "first_hit": "none",
            "bars_to_first_hit": 0,
            "hit_breakeven_stop": False,
            "hit_trailing_stop": False,
            "realized_return_pct": 0.0,
            "realized_r": 0.0,
        }
    highs = [float(item.get("high", 0.0)) for item in rows]
    lows = [float(item.get("low", 0.0)) for item in rows]
    closes = [float(item.get("close", 0.0)) for item in rows]
    highest_high = max(highs) if highs else entry_price
    lowest_low = min(lows) if lows else entry_price
    close_at_horizon = closes[-1] if closes else entry_price

    if side == "LONG":
        mfe = max(((value - entry_price) / entry_price) * 100.0 for value in highs) if highs else 0.0
        mae = max(((entry_price - value) / entry_price) * 100.0 for value in lows) if lows else 0.0
        ret = ((close_at_horizon - entry_price) / entry_price) * 100.0 if closes else 0.0
    else:
        mfe = max(((entry_price - value) / entry_price) * 100.0 for value in lows) if lows else 0.0
        mae = max(((value - entry_price) / entry_price) * 100.0 for value in highs) if highs else 0.0
        ret = ((entry_price - close_at_horizon) / entry_price) * 100.0 if closes else 0.0

    initial_stop_loss = float(stop_loss)
    risk_distance = entry_price - initial_stop_loss if side == "LONG" else initial_stop_loss - entry_price
    active_stop_loss = float(initial_stop_loss)
    effective_take_profit = float(take_profit)
    be_level = (
        entry_price + risk_distance * float(resolved_exit["breakeven_at_r"])
        if side == "LONG" and resolved_exit["breakeven_at_r"] is not None and risk_distance > 0
        else None
    )
    trail_trigger_level = (
        entry_price + risk_distance * float(resolved_exit["trail_at_r"])
        if side == "LONG" and resolved_exit["trail_at_r"] is not None and risk_distance > 0
        else None
    )
    trail_distance = (
        risk_distance * float(resolved_exit["trail_distance_r"])
        if side == "LONG" and resolved_exit["trail_distance_r"] is not None and risk_distance > 0
        else None
    )
    breakeven_active = False
    trailing_active = False
    highest_since_trailing = 0.0

    hit_take_profit = False
    hit_stop_loss = False
    first_hit = "none"
    bars_to_first_hit = 0
    hit_breakeven_stop = False
    hit_trailing_stop = False
    exit_price = close_at_horizon

    for idx, bar in enumerate(rows):
        high_v = float(bar.get("high", 0.0))
        low_v = float(bar.get("low", 0.0))
        tp_bar = False
        sl_bar = False
        if side == "LONG":
            tp_bar = effective_take_profit > 0 and high_v >= effective_take_profit
            sl_bar = active_stop_loss > 0 and low_v <= active_stop_loss
        else:
            tp_bar = effective_take_profit > 0 and low_v <= effective_take_profit
            sl_bar = active_stop_loss > 0 and high_v >= active_stop_loss
        if tp_bar:
            hit_take_profit = True
        if sl_bar:
            hit_stop_loss = True
        if tp_bar or sl_bar:
            bars_to_first_hit = idx + 1
            if tp_bar and sl_bar:
                first_hit = "stop_loss_first"
                exit_price = active_stop_loss
            elif sl_bar:
                first_hit = "stop_loss_first"
                exit_price = active_stop_loss
            else:
                first_hit = "take_profit_first"
                exit_price = effective_take_profit
            if sl_bar and active_stop_loss >= entry_price:
                hit_breakeven_stop = True
            if sl_bar and trailing_active and active_stop_loss > entry_price:
                hit_trailing_stop = True
            break

        # 触发后从下一根开始生效，因此在当根未出场后再更新。
        if side == "LONG":
            if be_level is not None and not breakeven_active and high_v >= be_level:
                breakeven_active = True
                active_stop_loss = max(active_stop_loss, entry_price)
            if trail_trigger_level is not None and trail_distance is not None:
                if not trailing_active and high_v >= trail_trigger_level:
                    trailing_active = True
                    highest_since_trailing = high_v
                    active_stop_loss = max(active_stop_loss, highest_since_trailing - trail_distance)
                elif trailing_active:
                    highest_since_trailing = max(highest_since_trailing, high_v)
                    active_stop_loss = max(active_stop_loss, highest_since_trailing - trail_distance)

    if side == "LONG":
        realized_return_pct = ((exit_price - entry_price) / entry_price) * 100.0 if entry_price > 0 else 0.0
        realized_r = ((exit_price - entry_price) / risk_distance) if risk_distance > 0 else 0.0
    else:
        realized_return_pct = ((entry_price - exit_price) / entry_price) * 100.0 if entry_price > 0 else 0.0
        realized_r = ((entry_price - exit_price) / risk_distance) if risk_distance > 0 else 0.0
    if first_hit == "none":
        hit_breakeven_stop = False
        hit_trailing_stop = False

    return {
        "horizon": int(horizon),
        "bars_used": len(rows),
        "max_favorable_excursion_pct": round(max(mfe, 0.0), 6),
        "max_adverse_excursion_pct": round(max(mae, 0.0), 6),
        "highest_high": highest_high,
        "lowest_low": lowest_low,
        "close_at_horizon": close_at_horizon,
        "return_at_horizon_pct": round(ret, 6),
        "hit_take_profit": bool(hit_take_profit),
        "hit_stop_loss": bool(hit_stop_loss),
        "first_hit": first_hit,
        "bars_to_first_hit": int(bars_to_first_hit),
        "initial_stop_loss": initial_stop_loss,
        "effective_take_profit": effective_take_profit,
        "final_stop_loss": round(active_stop_loss, 10),
        "breakeven_active": bool(breakeven_active),
        "trailing_active": bool(trailing_active),
        "hit_breakeven_stop": bool(hit_breakeven_stop),
        "hit_trailing_stop": bool(hit_trailing_stop),
        "realized_return_pct": round(realized_return_pct, 6),
        "realized_r": round(realized_r, 6),
    }


def _normalize_horizons(horizons: Optional[list[int]]) -> list[int]:
    if not isinstance(horizons, list) or len(horizons) == 0:
        return [5, 15, 30]
    rows = sorted({max(1, int(item)) for item in horizons if int(item) > 0})
    return rows or [5, 15, 30]


def _normalize_kline(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "timestamp": row.get("timestamp", _now_iso()),
        "open": _to_float(row.get("open", 0.0)),
        "high": _to_float(row.get("high", 0.0)),
        "low": _to_float(row.get("low", 0.0)),
        "close": _to_float(row.get("close", 0.0)),
        "volume": _to_float(row.get("volume", 0.0)),
    }


def _to_float(value: Any, *, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _to_optional_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_epoch_ms(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, datetime):
        return int(value.timestamp() * 1000)
    if isinstance(value, (int, float)):
        raw = float(value)
        if raw <= 0:
            return 0
        if raw < 1e11:
            return int(raw * 1000)
        return int(raw)
    text = str(value).strip()
    if not text:
        return 0
    try:
        number = float(text)
        if number > 0:
            if number < 1e11:
                return int(number * 1000)
            return int(number)
    except ValueError:
        pass
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return int(parsed.timestamp() * 1000)
    except ValueError:
        return 0


def _to_iso(ts_ms: int) -> str:
    if int(ts_ms) <= 0:
        return _now_iso()
    return datetime.fromtimestamp(int(ts_ms) / 1000, tz=timezone.utc).isoformat()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _resolve_exit_params(exit_params: Optional[dict[str, Any]]) -> dict[str, Optional[float]]:
    row = dict(exit_params or {})
    rr_target = _to_optional_positive_float(row.get("rr_target"))
    breakeven_at_r = _to_optional_positive_float(row.get("breakeven_at_r"))
    trail_at_r = _to_optional_positive_float(row.get("trail_at_r"))
    trail_distance_r = _to_optional_positive_float(row.get("trail_distance_r"))
    if trail_at_r is None:
        trail_distance_r = None
    return {
        "rr_target": rr_target,
        "breakeven_at_r": breakeven_at_r,
        "trail_at_r": trail_at_r,
        "trail_distance_r": trail_distance_r,
    }


def _to_optional_positive_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in {"", "none", "null", "na", "off"}:
        return None
    number = _to_float(value, default=0.0)
    if number <= 0:
        return None
    return float(number)
