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
    read_csv_rows,
    safe_ratio,
    to_epoch_ms,
    to_float_nan,
)


FIELDS = [
    "shadow_candidate_id",
    "symbol",
    "side",
    "timeframe",
    "strategy_key",
    "signal_time",
    "entry_price",
    "planned_sl_price",
    "planned_tp_price",
    "risk_per_unit",
    "outcome",
    "outcome_status",
    "exit_price",
    "exit_time",
    "bars_to_exit",
    "mfe_r",
    "mae_r",
    "realized_r_multiple",
    "tp_was_touched",
    "sl_was_touched",
    "first_touch",
    "evaluation_window_bars",
    "missing_fields",
    "source_reports",
    "candidate_source",
    "collector_mode",
    "near_miss",
    "near_miss_reason",
    "signal_strength_score",
    "trend_score",
    "breakout_score",
    "risk_reward_score",
]

BY_HORIZON_FIELDS = [
    "shadow_candidate_id",
    "symbol",
    "side",
    "timeframe",
    "strategy_key",
    "horizon_bars",
    "is_primary_horizon",
    "outcome",
    "first_touch",
    "mfe_r",
    "mae_r",
    "realized_r_multiple",
    "tp_was_touched",
    "sl_was_touched",
    "bars_to_exit",
    "evaluation_status",
]

def _to_bool(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def _normalize_side(value: Any) -> str:
    text = str(value or "").strip().upper()
    if text in {"BUY", "LONG"}:
        return "LONG"
    if text in {"SELL", "SHORT"}:
        return "SHORT"
    return text or "LONG"


def _to_iso_utc(ts_ms: int) -> str:
    if ts_ms <= 0:
        return ""
    return datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc).isoformat()


def _load_jsonl_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            text = line.strip()
            if not text:
                continue
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                rows.append(payload)
    except OSError:
        return []
    return rows


def _default_levels(entry_price: float, side: str) -> tuple[float, float]:
    if not math.isfinite(entry_price) or entry_price <= 0:
        return float("nan"), float("nan")
    if side == "SHORT":
        return entry_price * 1.01, entry_price * 0.985
    return entry_price * 0.99, entry_price * 1.015


def _merge_shadow_candidates(
    *,
    shadow_candidates_jsonl: str,
    shadow_candidates_csv: str,
    universe_candidates_csv: str,
    include_universe_candidates: bool = True,
    include_observation: bool = True,
    include_near_miss: bool = True,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    jsonl_rows = _load_jsonl_rows(Path(shadow_candidates_jsonl))
    csv_rows = read_csv_rows(Path(shadow_candidates_csv))
    universe_rows = read_csv_rows(Path(universe_candidates_csv)) if bool(include_universe_candidates) else []
    merged: dict[str, dict[str, Any]] = {}
    source_counter = {
        "shadow_candidate_collection": 0,
        "shadow_universe_collection": 0,
        "shadow_candidates_jsonl": 0,
    }
    source_rows: list[tuple[str, dict[str, Any]]] = []
    source_rows.extend(("shadow_candidate_collection", row) for row in csv_rows)
    source_rows.extend(("shadow_universe_collection", row) for row in universe_rows)
    source_rows.extend(("shadow_candidates_jsonl", row) for row in jsonl_rows)

    for source, row in source_rows:
        candidate_id = str(row.get("candidate_id", row.get("shadow_candidate_id", ""))).strip()
        if not candidate_id:
            continue
        source_counter[source] = int(source_counter.get(source, 0)) + 1
        payload = dict(row)
        payload["candidate_id"] = candidate_id
        existing = dict(merged.get(candidate_id, {}))
        existing_sources = set(str(existing.get("source_reports", "")).split(";")) if str(existing.get("source_reports", "")).strip() else set()
        existing_sources.add(source)
        payload["source_reports"] = ";".join(sorted(existing_sources))
        payload["candidate_source"] = str(existing.get("candidate_source", "")).strip() or source
        merged[candidate_id] = {**existing, **payload}

    filtered: list[dict[str, Any]] = []
    for key in sorted(merged.keys()):
        item = dict(merged[key])
        is_observation = str(item.get("candidate_status", "")).strip().upper() == "SHADOW_OBSERVATION_ONLY"
        is_near_miss = _to_bool(item.get("near_miss"))
        if (not include_observation) and is_observation:
            continue
        if (not include_near_miss) and is_near_miss:
            continue
        filtered.append(item)
    return filtered, source_counter


def _evaluate_single_horizon(
    *,
    side: str,
    entry_price: float,
    sl_price: float,
    tp_price: float,
    risk_per_unit: float,
    future: list[dict[str, Any]],
) -> dict[str, Any]:
    if not future:
        return {
            "outcome": "INSUFFICIENT_DATA",
            "outcome_status": "PARTIAL",
            "exit_price": float("nan"),
            "exit_time": "",
            "bars_to_exit": 0,
            "mfe_r": float("nan"),
            "mae_r": float("nan"),
            "realized_r_multiple": float("nan"),
            "tp_was_touched": False,
            "sl_was_touched": False,
            "first_touch": "NONE",
        }

    tp_touched = False
    sl_touched = False
    first_touch = "NONE"
    outcome = "UNKNOWN"
    exit_price = float("nan")
    exit_time = ""
    bars_to_exit = len(future)

    for idx, bar in enumerate(future, start=1):
        high = to_float_nan(bar.get("high"))
        low = to_float_nan(bar.get("low"))
        if side == "SHORT":
            tp_hit = math.isfinite(tp_price) and math.isfinite(low) and low <= tp_price
            sl_hit = math.isfinite(sl_price) and math.isfinite(high) and high >= sl_price
        else:
            tp_hit = math.isfinite(tp_price) and math.isfinite(high) and high >= tp_price
            sl_hit = math.isfinite(sl_price) and math.isfinite(low) and low <= sl_price
        tp_touched = tp_touched or tp_hit
        sl_touched = sl_touched or sl_hit
        if not (tp_hit or sl_hit):
            continue
        bars_to_exit = idx
        exit_time = _to_iso_utc(int(bar.get("close_time_ms", 0) or 0))
        if tp_hit and sl_hit:
            first_touch = "BOTH_SAME_BAR"
            outcome = "SHADOW_SL_FIRST"
            exit_price = sl_price
        elif tp_hit:
            first_touch = "TP"
            outcome = "SHADOW_TP_FIRST"
            exit_price = tp_price
        else:
            first_touch = "SL"
            outcome = "SHADOW_SL_FIRST"
            exit_price = sl_price
        break

    highs = [to_float_nan(bar.get("high")) for bar in future if math.isfinite(to_float_nan(bar.get("high")))]
    lows = [to_float_nan(bar.get("low")) for bar in future if math.isfinite(to_float_nan(bar.get("low")))]
    closes = [to_float_nan(bar.get("close")) for bar in future if math.isfinite(to_float_nan(bar.get("close")))]
    final_close = closes[-1] if closes else float("nan")

    if outcome == "UNKNOWN":
        if not math.isfinite(final_close) or not math.isfinite(entry_price):
            outcome = "INSUFFICIENT_DATA"
            first_touch = "UNKNOWN"
        else:
            pnl_per_unit = (final_close - entry_price) if side != "SHORT" else (entry_price - final_close)
            if pnl_per_unit > 1e-12:
                outcome = "SHADOW_TIMEOUT_PROFIT"
            elif pnl_per_unit < -1e-12:
                outcome = "SHADOW_TIMEOUT_LOSS"
            else:
                outcome = "SHADOW_TIMEOUT_FLAT"
            exit_price = final_close
            exit_time = _to_iso_utc(int(future[-1].get("close_time_ms", 0) or 0))

    if not math.isfinite(exit_price) and math.isfinite(final_close):
        exit_price = final_close
    if not exit_time and future:
        exit_time = _to_iso_utc(int(future[-1].get("close_time_ms", 0) or 0))

    mfe_per = float("nan")
    mae_per = float("nan")
    if math.isfinite(entry_price) and highs and lows:
        if side == "SHORT":
            mfe_per = entry_price - min(lows)
            mae_per = max(highs) - entry_price
        else:
            mfe_per = max(highs) - entry_price
            mae_per = entry_price - min(lows)

    realized_per = float("nan")
    if math.isfinite(entry_price) and math.isfinite(exit_price):
        realized_per = (exit_price - entry_price) if side != "SHORT" else (entry_price - exit_price)

    mfe_r = safe_ratio(mfe_per, risk_per_unit)
    mae_r = safe_ratio(mae_per, risk_per_unit)
    realized_r = safe_ratio(realized_per, risk_per_unit)
    outcome_status = "OK" if outcome not in {"MISSING_KLINES", "INSUFFICIENT_DATA", "UNKNOWN"} else "PARTIAL"
    return {
        "outcome": outcome,
        "outcome_status": outcome_status,
        "exit_price": exit_price,
        "exit_time": exit_time,
        "bars_to_exit": bars_to_exit,
        "mfe_r": mfe_r,
        "mae_r": mae_r,
        "realized_r_multiple": realized_r,
        "tp_was_touched": bool(tp_touched),
        "sl_was_touched": bool(sl_touched),
        "first_touch": first_touch,
    }


def evaluate_shadow_candidate_outcomes(
    *,
    shadow_candidates_jsonl: str = "logs/shadow_candidates.jsonl",
    shadow_candidates_csv: str = "reports/shadow_candidate_collection/shadow_candidates.csv",
    universe_candidates_csv: str = "reports/shadow_universe_collection/shadow_universe_candidates.csv",
    kline_cache_dir: str = "data/cache/klines",
    output_dir: str = "reports/shadow_candidate_outcomes",
    evaluation_window_bars: int = 24,
    horizons: str = "",
    primary_horizon: int = 0,
    include_universe_candidates: bool = True,
    include_observation: bool = True,
    include_near_miss: bool = True,
) -> dict[str, Any]:
    candidates, candidate_sources = _merge_shadow_candidates(
        shadow_candidates_jsonl=shadow_candidates_jsonl,
        shadow_candidates_csv=shadow_candidates_csv,
        universe_candidates_csv=universe_candidates_csv,
        include_universe_candidates=bool(include_universe_candidates),
        include_observation=bool(include_observation),
        include_near_miss=bool(include_near_miss),
    )
    if str(horizons or "").strip():
        horizon_list = sorted({max(1, int(float(item.strip()))) for item in str(horizons).split(",") if item.strip()})
    else:
        horizon_list = [max(1, int(evaluation_window_bars or 24))]
    resolved_primary_horizon = int(primary_horizon or 0)
    if resolved_primary_horizon <= 0 or resolved_primary_horizon not in horizon_list:
        resolved_primary_horizon = horizon_list[0]

    rows: list[dict[str, Any]] = []
    by_horizon_rows: list[dict[str, Any]] = []
    for candidate in candidates:
        candidate_id = str(candidate.get("candidate_id", "")).strip()
        symbol = str(candidate.get("symbol", "")).strip().upper()
        side = _normalize_side(candidate.get("side", "LONG"))
        timeframe = str(candidate.get("timeframe", "5m")).strip() or "5m"
        strategy_key = str(candidate.get("strategy_key", "")).strip() or f"{symbol}_{side}_{timeframe}"
        signal_time = str(candidate.get("signal_time", candidate.get("created_at", ""))).strip()
        signal_ms = to_epoch_ms(signal_time)
        entry_price = to_float_nan(candidate.get("entry_price"))
        collector_mode = str(candidate.get("collector_mode", "")).strip().lower() or "unknown"
        near_miss = _to_bool(candidate.get("near_miss"))
        near_miss_reason = str(candidate.get("near_miss_reason", "")).strip()
        signal_strength_score = to_float_nan(candidate.get("signal_strength_score"))
        trend_score = to_float_nan(candidate.get("trend_score"))
        breakout_score = to_float_nan(candidate.get("breakout_score"))
        risk_reward_score = to_float_nan(candidate.get("risk_reward_score"))
        candidate_source = str(candidate.get("candidate_source", "")).strip() or "shadow_candidates_jsonl"
        source_reports = str(candidate.get("source_reports", "")).strip() or "shadow_candidates_jsonl"
        sl_price = to_float_nan(candidate.get("planned_sl_price", candidate.get("sl_price", candidate.get("stop_loss"))))
        tp_price = to_float_nan(candidate.get("planned_tp_price", candidate.get("tp_price", candidate.get("take_profit"))))
        missing: list[str] = []
        if not math.isfinite(sl_price) or not math.isfinite(tp_price):
            d_sl, d_tp = _default_levels(entry_price, side)
            if not math.isfinite(sl_price):
                sl_price = d_sl
            if not math.isfinite(tp_price):
                tp_price = d_tp
            missing.append("planned_levels_defaulted")

        risk_per_unit = abs(entry_price - sl_price) if (math.isfinite(entry_price) and math.isfinite(sl_price)) else float("nan")
        klines = load_cached_klines(cache_root=kline_cache_dir, symbol=symbol, timeframe=timeframe)
        if not klines:
            for h in horizon_list:
                by_horizon_rows.append(
                    {
                        "shadow_candidate_id": candidate_id,
                        "symbol": symbol,
                        "side": side,
                        "timeframe": timeframe,
                        "strategy_key": strategy_key,
                        "horizon_bars": h,
                        "is_primary_horizon": h == resolved_primary_horizon,
                        "outcome": "MISSING_KLINES",
                        "first_touch": "UNKNOWN",
                        "mfe_r": float("nan"),
                        "mae_r": float("nan"),
                        "realized_r_multiple": float("nan"),
                        "tp_was_touched": False,
                        "sl_was_touched": False,
                        "bars_to_exit": 0,
                        "evaluation_status": "PARTIAL",
                    }
                )
            rows.append(
                {
                    "shadow_candidate_id": candidate_id,
                    "symbol": symbol,
                    "side": side,
                    "timeframe": timeframe,
                    "strategy_key": strategy_key,
                    "signal_time": signal_time,
                    "entry_price": entry_price,
                    "planned_sl_price": sl_price,
                    "planned_tp_price": tp_price,
                    "risk_per_unit": risk_per_unit,
                    "outcome": "MISSING_KLINES",
                    "outcome_status": "PARTIAL",
                    "exit_price": float("nan"),
                    "exit_time": "",
                    "bars_to_exit": 0,
                    "mfe_r": float("nan"),
                    "mae_r": float("nan"),
                    "realized_r_multiple": float("nan"),
                    "tp_was_touched": False,
                    "sl_was_touched": False,
                    "first_touch": "UNKNOWN",
                    "evaluation_window_bars": resolved_primary_horizon,
                    "missing_fields": ";".join(sorted(set(missing + ["missing_klines"]))),
                    "source_reports": source_reports,
                    "candidate_source": candidate_source,
                    "collector_mode": collector_mode,
                    "near_miss": near_miss,
                    "near_miss_reason": near_miss_reason,
                    "signal_strength_score": signal_strength_score,
                    "trend_score": trend_score,
                    "breakout_score": breakout_score,
                    "risk_reward_score": risk_reward_score,
                }
            )
            continue

        entry_idx = find_bar_index(klines, signal_ms)
        if entry_idx < 0:
            for h in horizon_list:
                by_horizon_rows.append(
                    {
                        "shadow_candidate_id": candidate_id,
                        "symbol": symbol,
                        "side": side,
                        "timeframe": timeframe,
                        "strategy_key": strategy_key,
                        "horizon_bars": h,
                        "is_primary_horizon": h == resolved_primary_horizon,
                        "outcome": "INSUFFICIENT_DATA",
                        "first_touch": "UNKNOWN",
                        "mfe_r": float("nan"),
                        "mae_r": float("nan"),
                        "realized_r_multiple": float("nan"),
                        "tp_was_touched": False,
                        "sl_was_touched": False,
                        "bars_to_exit": 0,
                        "evaluation_status": "PARTIAL",
                    }
                )
            rows.append(
                {
                    "shadow_candidate_id": candidate_id,
                    "symbol": symbol,
                    "side": side,
                    "timeframe": timeframe,
                    "strategy_key": strategy_key,
                    "signal_time": signal_time,
                    "entry_price": entry_price,
                    "planned_sl_price": sl_price,
                    "planned_tp_price": tp_price,
                    "risk_per_unit": risk_per_unit,
                    "outcome": "INSUFFICIENT_DATA",
                    "outcome_status": "PARTIAL",
                    "exit_price": float("nan"),
                    "exit_time": "",
                    "bars_to_exit": 0,
                    "mfe_r": float("nan"),
                    "mae_r": float("nan"),
                    "realized_r_multiple": float("nan"),
                    "tp_was_touched": False,
                    "sl_was_touched": False,
                    "first_touch": "UNKNOWN",
                    "evaluation_window_bars": resolved_primary_horizon,
                    "missing_fields": ";".join(sorted(set(missing + ["signal_time_not_in_klines"]))),
                    "source_reports": source_reports,
                    "candidate_source": candidate_source,
                    "collector_mode": collector_mode,
                    "near_miss": near_miss,
                    "near_miss_reason": near_miss_reason,
                    "signal_strength_score": signal_strength_score,
                    "trend_score": trend_score,
                    "breakout_score": breakout_score,
                    "risk_reward_score": risk_reward_score,
                }
            )
            continue

        primary_row: dict[str, Any] | None = None
        for h in horizon_list:
            future = klines[entry_idx + 1 : entry_idx + 1 + h]
            metrics = _evaluate_single_horizon(
                side=side,
                entry_price=entry_price,
                sl_price=sl_price,
                tp_price=tp_price,
                risk_per_unit=risk_per_unit,
                future=future,
            )
            if str(metrics.get("outcome", "")).strip().upper() == "UNKNOWN":
                missing.append("unknown_outcome")
            horizon_row = {
                "shadow_candidate_id": candidate_id,
                "symbol": symbol,
                "side": side,
                "timeframe": timeframe,
                "strategy_key": strategy_key,
                "horizon_bars": h,
                "is_primary_horizon": h == resolved_primary_horizon,
                "outcome": metrics.get("outcome", "UNKNOWN"),
                "first_touch": metrics.get("first_touch", "UNKNOWN"),
                "mfe_r": metrics.get("mfe_r", float("nan")),
                "mae_r": metrics.get("mae_r", float("nan")),
                "realized_r_multiple": metrics.get("realized_r_multiple", float("nan")),
                "tp_was_touched": bool(metrics.get("tp_was_touched", False)),
                "sl_was_touched": bool(metrics.get("sl_was_touched", False)),
                "bars_to_exit": int(metrics.get("bars_to_exit", 0) or 0),
                "evaluation_status": str(metrics.get("outcome_status", "PARTIAL")).strip().upper(),
            }
            by_horizon_rows.append(horizon_row)
            if h == resolved_primary_horizon:
                primary_row = metrics
        primary_row = primary_row or _evaluate_single_horizon(
            side=side,
            entry_price=entry_price,
            sl_price=sl_price,
            tp_price=tp_price,
            risk_per_unit=risk_per_unit,
            future=[],
        )
        rows.append(
            {
                "shadow_candidate_id": candidate_id,
                "symbol": symbol,
                "side": side,
                "timeframe": timeframe,
                "strategy_key": strategy_key,
                "signal_time": signal_time,
                "entry_price": entry_price,
                "planned_sl_price": sl_price,
                "planned_tp_price": tp_price,
                "risk_per_unit": risk_per_unit,
                "outcome": primary_row.get("outcome", "UNKNOWN"),
                "outcome_status": primary_row.get("outcome_status", "PARTIAL"),
                "exit_price": primary_row.get("exit_price", float("nan")),
                "exit_time": primary_row.get("exit_time", ""),
                "bars_to_exit": int(primary_row.get("bars_to_exit", 0) or 0),
                "mfe_r": primary_row.get("mfe_r", float("nan")),
                "mae_r": primary_row.get("mae_r", float("nan")),
                "realized_r_multiple": primary_row.get("realized_r_multiple", float("nan")),
                "tp_was_touched": bool(primary_row.get("tp_was_touched", False)),
                "sl_was_touched": bool(primary_row.get("sl_was_touched", False)),
                "first_touch": primary_row.get("first_touch", "UNKNOWN"),
                "evaluation_window_bars": resolved_primary_horizon,
                "missing_fields": ";".join(sorted(set(missing))),
                "source_reports": source_reports,
                "candidate_source": candidate_source,
                "collector_mode": collector_mode,
                "near_miss": near_miss,
                "near_miss_reason": near_miss_reason,
                "signal_strength_score": signal_strength_score,
                "trend_score": trend_score,
                "breakout_score": breakout_score,
                "risk_reward_score": risk_reward_score,
            }
        )

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "shadow_candidate_outcomes.csv"
    summary_json = out_dir / "summary.json"
    summary_md = out_dir / "summary.md"
    by_horizon_csv = out_dir / "shadow_candidate_outcomes_by_horizon.csv"

    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in FIELDS})
    with by_horizon_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=BY_HORIZON_FIELDS)
        writer.writeheader()
        for row in by_horizon_rows:
            writer.writerow({field: row.get(field, "") for field in BY_HORIZON_FIELDS})

    summary = {
        "ok": True,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "candidate_count": len(candidates),
        "evaluated_count": len(rows),
        "candidate_sources": candidate_sources,
        "strict_candidate_count": sum(
            1 for row in rows if str(row.get("collector_mode", "")).strip().lower() == "strict"
        ),
        "observation_candidate_count": sum(
            1
            for row in rows
            if str(row.get("collector_mode", "")).strip().lower() == "observation"
            or str(row.get("candidate_source", "")).strip() == "shadow_universe_collection"
        ),
        "near_miss_candidate_count": sum(1 for row in rows if _to_bool(row.get("near_miss"))),
        "tp_first_count": sum(1 for row in rows if str(row.get("outcome", "")).strip().upper() == "SHADOW_TP_FIRST"),
        "sl_first_count": sum(1 for row in rows if str(row.get("outcome", "")).strip().upper() == "SHADOW_SL_FIRST"),
        "timeout_count": sum(1 for row in rows if str(row.get("outcome", "")).strip().upper().startswith("SHADOW_TIMEOUT_")),
        "timeout_profit_count": sum(1 for row in rows if str(row.get("outcome", "")).strip().upper() == "SHADOW_TIMEOUT_PROFIT"),
        "timeout_loss_count": sum(1 for row in rows if str(row.get("outcome", "")).strip().upper() == "SHADOW_TIMEOUT_LOSS"),
        "timeout_flat_count": sum(1 for row in rows if str(row.get("outcome", "")).strip().upper() == "SHADOW_TIMEOUT_FLAT"),
        "missing_klines_count": sum(1 for row in rows if str(row.get("outcome", "")).strip().upper() == "MISSING_KLINES"),
        "insufficient_data_count": sum(1 for row in rows if str(row.get("outcome", "")).strip().upper() == "INSUFFICIENT_DATA"),
        "horizons": horizon_list,
        "primary_horizon": resolved_primary_horizon,
        "primary_horizon_evaluated_count": len(rows),
        "by_horizon_outcome_counts": {
            str(h): {
                "SHADOW_TP_FIRST": sum(
                    1
                    for row in by_horizon_rows
                    if int(to_float_nan(row.get("horizon_bars"))) == h and str(row.get("outcome", "")).strip().upper() == "SHADOW_TP_FIRST"
                ),
                "SHADOW_SL_FIRST": sum(
                    1
                    for row in by_horizon_rows
                    if int(to_float_nan(row.get("horizon_bars"))) == h and str(row.get("outcome", "")).strip().upper() == "SHADOW_SL_FIRST"
                ),
                "SHADOW_TIMEOUT_PROFIT": sum(
                    1
                    for row in by_horizon_rows
                    if int(to_float_nan(row.get("horizon_bars"))) == h
                    and str(row.get("outcome", "")).strip().upper() == "SHADOW_TIMEOUT_PROFIT"
                ),
                "SHADOW_TIMEOUT_LOSS": sum(
                    1
                    for row in by_horizon_rows
                    if int(to_float_nan(row.get("horizon_bars"))) == h and str(row.get("outcome", "")).strip().upper() == "SHADOW_TIMEOUT_LOSS"
                ),
                "SHADOW_TIMEOUT_FLAT": sum(
                    1
                    for row in by_horizon_rows
                    if int(to_float_nan(row.get("horizon_bars"))) == h and str(row.get("outcome", "")).strip().upper() == "SHADOW_TIMEOUT_FLAT"
                ),
                "MISSING_KLINES": sum(
                    1
                    for row in by_horizon_rows
                    if int(to_float_nan(row.get("horizon_bars"))) == h and str(row.get("outcome", "")).strip().upper() == "MISSING_KLINES"
                ),
                "INSUFFICIENT_DATA": sum(
                    1
                    for row in by_horizon_rows
                    if int(to_float_nan(row.get("horizon_bars"))) == h and str(row.get("outcome", "")).strip().upper() == "INSUFFICIENT_DATA"
                ),
            }
            for h in horizon_list
        },
        "by_horizon_csv": str(by_horizon_csv),
        "csv_path": str(csv_path),
        "summary_json": str(summary_json),
        "summary_md": str(summary_md),
    }
    summary["reason"] = "ok"
    if len(candidates) == 0:
        summary["reason"] = "no_shadow_candidates"
    elif summary["missing_klines_count"] >= len(rows) and len(rows) > 0:
        summary["reason"] = "missing_klines"
    summary["final_verdict"] = "PASS"
    realized_r_values = [
        float(to_float_nan(row.get("realized_r_multiple")))
        for row in rows
        if math.isfinite(to_float_nan(row.get("realized_r_multiple")))
    ]
    summary["avg_shadow_realized_r_multiple"] = (
        round(sum(realized_r_values) / len(realized_r_values), 8) if realized_r_values else None
    )

    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Shadow Candidate Outcomes",
        "",
        f"- final_verdict: {summary['final_verdict']}",
        f"- candidate_count: {summary['candidate_count']}",
        f"- evaluated_count: {summary['evaluated_count']}",
        f"- tp_first_count: {summary['tp_first_count']}",
        f"- sl_first_count: {summary['sl_first_count']}",
        f"- timeout_count: {summary['timeout_count']}",
        f"- missing_klines_count: {summary['missing_klines_count']}",
        f"- reason: {summary['reason']}",
    ]
    summary_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate outcomes for shadow-only candidates from cached klines")
    parser.add_argument("--shadow-candidates-jsonl", default="logs/shadow_candidates.jsonl")
    parser.add_argument("--shadow-candidates-csv", default="reports/shadow_candidate_collection/shadow_candidates.csv")
    parser.add_argument("--universe-candidates-csv", default="reports/shadow_universe_collection/shadow_universe_candidates.csv")
    parser.add_argument("--kline-cache-dir", default="data/cache/klines")
    parser.add_argument("--output-dir", default="reports/shadow_candidate_outcomes")
    parser.add_argument("--evaluation-window-bars", type=int, default=24)
    parser.add_argument("--horizons", default="")
    parser.add_argument("--primary-horizon", type=int, default=0)
    parser.add_argument("--include-universe-candidates", dest="include_universe_candidates", action="store_true")
    parser.add_argument("--no-include-universe-candidates", dest="include_universe_candidates", action="store_false")
    parser.set_defaults(include_universe_candidates=True)
    parser.add_argument("--include-observation", dest="include_observation", action="store_true")
    parser.add_argument("--no-include-observation", dest="include_observation", action="store_false")
    parser.set_defaults(include_observation=True)
    parser.add_argument("--include-near-miss", dest="include_near_miss", action="store_true")
    parser.add_argument("--no-include-near-miss", dest="include_near_miss", action="store_false")
    parser.set_defaults(include_near_miss=True)
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = evaluate_shadow_candidate_outcomes(
        shadow_candidates_jsonl=str(args.shadow_candidates_jsonl or "logs/shadow_candidates.jsonl"),
        shadow_candidates_csv=str(args.shadow_candidates_csv or "reports/shadow_candidate_collection/shadow_candidates.csv"),
        universe_candidates_csv=str(args.universe_candidates_csv or "reports/shadow_universe_collection/shadow_universe_candidates.csv"),
        kline_cache_dir=str(args.kline_cache_dir or "data/cache/klines"),
        output_dir=str(args.output_dir or "reports/shadow_candidate_outcomes"),
        evaluation_window_bars=int(args.evaluation_window_bars or 24),
        horizons=str(args.horizons or ""),
        primary_horizon=int(args.primary_horizon or 0),
        include_universe_candidates=bool(args.include_universe_candidates),
        include_observation=bool(args.include_observation),
        include_near_miss=bool(args.include_near_miss),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"evaluated_count={result.get('evaluated_count', 0)}")
    print(f"final_verdict={result.get('final_verdict', '')}")
    print(f"reason={result.get('reason', '')}")


if __name__ == "__main__":
    main()
