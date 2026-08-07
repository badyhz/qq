#!/usr/bin/env python3
"""Temporary time-split validation for Market Accelerator SHORT entries.

Research branch only; do not merge.

The discovery run found only two zero-friction variants with positive aggregate
structure, so this validation script freezes those exact definitions and tests
them without parameter changes:

C_SHORT_ACCEL      = negative accelerator activation, no HTF filter
D_SHORT_ACCEL_HTF  = negative accelerator activation + HTF == DOWN

Activation remains unchanged:
    previous regime in {IDLE, DECELERATING}
    current regime in {START, FAST}
    signed_speed < 0

Execution remains unchanged:
- fully closed signal bar -> next bar open SHORT;
- stop = signal high + 0.10%;
- fixed 2R target;
- existing Shadow TradeIntent risk gate;
- existing simulator with entry_execution='bar_open';
- one exposure at a time;
- zero friction for structural validation;
- no threshold, stop, target, symbol or timeframe optimization.

Environment variables select only the validation sample:
RESEARCH_SYMBOLS, RESEARCH_START, RESEARCH_SPLIT, RESEARCH_END.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import sys

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from core.offline_backtest_metrics_engine import compute_run_metrics
from core.offline_backtest_trade_simulator import (
    TradeSimulationParams,
    simulate_trade,
)
from core.paper_trading.higher_timeframe_trend import align_higher_timeframe_trends
from core.paper_trading.indicator_composite_strategy import (
    AccelerationRegime,
    HigherTimeframeTrend,
)
from core.paper_trading.market_accelerator_port import (
    calculate_market_accelerator,
    classify_accelerator_series,
)
from core.paper_trading.trade_intent_risk_gate import validate_trade_intent
from scripts.prepare_indicator_composite_history import DEFAULT_SYMBOLS
from scripts.run_indicator_composite_backtest import _load_historical, _market_bars


START = os.environ.get("RESEARCH_START", "2025-08-01")
SPLIT = os.environ.get("RESEARCH_SPLIT", "2026-02-01")
END = os.environ.get("RESEARCH_END", "2026-07-31")
SYMBOLS = tuple(
    value.strip().upper()
    for value in os.environ.get(
        "RESEARCH_SYMBOLS", ",".join(DEFAULT_SYMBOLS)
    ).split(",")
    if value.strip()
)
LOWER_TF = "15m"
HIGHER_TF = "1h"
DATA_ROOT = Path("data/indicator_composite_history")
STOP_BUFFER_PCT = 0.10
TARGET_R = 2.0
MAX_RISK_PCT = 0.5
MAX_HOLD_BARS = 100
VARIANTS = ("C_SHORT_ACCEL", "D_SHORT_ACCEL_HTF")
_ACTIVE = {AccelerationRegime.START, AccelerationRegime.FAST}
_REARMED = {AccelerationRegime.IDLE, AccelerationRegime.DECELERATING}


def _epoch(day: str) -> float:
    return datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp()


def _day_after(day: str) -> float:
    parsed = datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return (parsed + timedelta(days=1)).timestamp()


def _entry_events(bars, trends):
    series = calculate_market_accelerator(bars)
    regimes = classify_accelerator_series(series.points)
    events: list[dict | None] = [None] * len(bars)
    for index in range(1, len(bars)):
        previous_regime = regimes[index - 1].regime
        current_regime = regimes[index].regime
        signed_speed = series.points[index].signed_speed
        if (
            previous_regime not in _REARMED
            or current_regime not in _ACTIVE
            or signed_speed is None
            or signed_speed >= 0
        ):
            continue
        events[index] = {
            "signed_speed": float(signed_speed),
            "regime": current_regime.value,
            "previous_regime": previous_regime.value,
            "htf": trends[index].value,
        }
    return tuple(events)


def _variant_accepts(event: dict, trend: HigherTimeframeTrend, variant: str) -> bool:
    if variant == "C_SHORT_ACCEL":
        return True
    if variant == "D_SHORT_ACCEL_HTF":
        return trend == HigherTimeframeTrend.DOWN
    raise ValueError(f"unknown variant: {variant}")


def _bar_dict(bar) -> dict:
    return {
        "timestamp": float(bar.timestamp),
        "open": float(bar.open),
        "high": float(bar.high),
        "low": float(bar.low),
        "close": float(bar.close),
        "volume": float(bar.volume),
        "symbol": str(bar.symbol),
        "timeframe": str(bar.timeframe),
    }


def _outcome_dict(outcome) -> dict:
    return {
        "trade_id": outcome.trade_id,
        "signal_id": outcome.signal_id,
        "entry_bar_index": outcome.entry_bar_index,
        "exit_bar_index": outcome.exit_bar_index,
        "entry_price": outcome.entry_price,
        "exit_price": outcome.exit_price,
        "exit_reason": outcome.exit_reason,
        "realized_r": outcome.realized_r,
        "gross_pnl": outcome.gross_pnl,
        "fees": outcome.fees,
        "slippage_cost": outcome.slippage_cost,
        "net_pnl": outcome.net_pnl,
        "mfe_r": outcome.mfe_r,
        "mae_r": outcome.mae_r,
        "hold_bars": outcome.hold_bars,
    }


def _run_variant(bars, trends, events, variant: str) -> dict:
    bar_dicts = [_bar_dict(bar) for bar in bars]
    params = TradeSimulationParams(
        slippage_pct=0.0,
        fee_pct=0.0,
        max_hold_bars=MAX_HOLD_BARS,
    )
    raw_signal_count = 0
    accepted_signal_count = 0
    blocked_no_next_bar = 0
    blocked_invalid_execution = 0
    blocked_risk_gate = 0
    blocked_overlap = 0
    unavailable_until = -1
    trades: list[dict] = []

    for signal_index, event in enumerate(events):
        if event is None or not _variant_accepts(event, trends[signal_index], variant):
            continue
        raw_signal_count += 1
        if signal_index + 1 >= len(bars):
            blocked_no_next_bar += 1
            continue

        entry_index = signal_index + 1
        entry_price = float(bars[entry_index].open)
        stop_price = float(bars[signal_index].high) * (
            1.0 + STOP_BUFFER_PCT / 100.0
        )
        if entry_price <= 0 or entry_price >= stop_price:
            blocked_invalid_execution += 1
            continue

        risk = stop_price - entry_price
        take_profit = entry_price - TARGET_R * risk
        if take_profit <= 0:
            blocked_invalid_execution += 1
            continue

        risk_distance_pct = risk / entry_price * 100.0
        reward_distance_pct = (entry_price - take_profit) / entry_price * 100.0
        gate = validate_trade_intent({
            "execution_mode": "shadow_only",
            "side": "SHORT",
            "intent_status": "SHADOW_READY",
            "rr_ratio": TARGET_R,
            "risk_distance_pct": risk_distance_pct,
            "reward_distance_pct": reward_distance_pct,
            "max_risk_pct": MAX_RISK_PCT,
            "entry_price": entry_price,
            "stop_loss": stop_price,
            "take_profit": take_profit,
        })
        if not gate.passed:
            blocked_risk_gate += 1
            continue

        accepted_signal_count += 1
        if entry_index <= unavailable_until:
            blocked_overlap += 1
            continue

        outcome = simulate_trade({
            "signal_id": f"accelerator_{variant}_{signal_index}",
            "signal_bar_index": signal_index,
            "entry_bar_index": entry_index,
            "entry_execution": "bar_open",
            "entry_price": entry_price,
            "stop_price": stop_price,
            "tp_price": take_profit,
        }, bar_dicts, params)
        trades.append(_outcome_dict(outcome))
        unavailable_until = outcome.exit_bar_index

    metrics = compute_run_metrics(trades)
    return {
        "variant": variant,
        "raw_signal_count": raw_signal_count,
        "accepted_signal_count": accepted_signal_count,
        "trade_count": len(trades),
        "blocked_no_next_bar": blocked_no_next_bar,
        "blocked_invalid_execution": blocked_invalid_execution,
        "blocked_risk_gate": blocked_risk_gate,
        "blocked_overlap": blocked_overlap,
        "metrics": metrics,
        "trades": trades,
    }


def _compact(result: dict) -> dict:
    metrics = result["metrics"]
    return {
        "raw_signals": result["raw_signal_count"],
        "accepted_signals": result["accepted_signal_count"],
        "trades": result["trade_count"],
        "win_rate": metrics["win_rate"],
        "expectancy_r": metrics["expectancy_r"],
        "profit_factor": metrics["profit_factor"],
        "max_drawdown_r": metrics["max_drawdown_r"],
        "avg_mfe_r": metrics["avg_mfe_r"],
        "avg_mae_r": metrics["avg_mae_r"],
        "avg_hold_bars": metrics["avg_hold_bars"],
        "blocked_invalid_execution": result["blocked_invalid_execution"],
        "blocked_risk_gate": result["blocked_risk_gate"],
        "blocked_overlap": result["blocked_overlap"],
    }


def _slice_by_time(bars, trends, events, start_epoch: float, end_epoch: float):
    selected = [
        (bar, trend, event)
        for bar, trend, event in zip(bars, trends, events)
        if start_epoch <= float(bar.timestamp) < end_epoch
    ]
    return (
        tuple(item[0] for item in selected),
        tuple(item[1] for item in selected),
        tuple(item[2] for item in selected),
    )


def _aggregate(per_symbol: list[dict], variant: str, phase: str) -> dict:
    all_r: list[float] = []
    positive_symbols: list[str] = []
    total_trades = 0
    worst_symbol_drawdown = 0.0

    for entry in per_symbol:
        result = entry["_results"][phase][variant]
        compact = entry[phase][variant]
        total_trades += compact["trades"]
        worst_symbol_drawdown = min(
            worst_symbol_drawdown,
            float(compact["max_drawdown_r"]),
        )
        if float(compact["expectancy_r"]) > 0:
            positive_symbols.append(entry["symbol"])
        all_r.extend(float(trade["realized_r"]) for trade in result["trades"])

    wins = [value for value in all_r if value > 0]
    losses = [value for value in all_r if value <= 0]
    gross_wins = sum(wins)
    gross_losses = sum(losses)
    combined_pf = (
        gross_wins / abs(gross_losses)
        if gross_losses != 0
        else (float("inf") if gross_wins > 0 else 0.0)
    )
    return {
        "phase": phase,
        "variant": variant,
        "total_trades": total_trades,
        "combined_win_rate": round(len(wins) / len(all_r), 6) if all_r else 0.0,
        "combined_expectancy_r": round(sum(all_r) / len(all_r), 6) if all_r else 0.0,
        "combined_profit_factor": round(combined_pf, 6),
        "positive_expectancy_symbols": positive_symbols,
        "positive_symbol_count": len(positive_symbols),
        "worst_symbol_drawdown_r": round(worst_symbol_drawdown, 6),
        "portfolio_drawdown_not_computed": True,
    }


def main() -> int:
    if not SYMBOLS:
        raise ValueError("RESEARCH_SYMBOLS produced an empty symbol set")
    start_epoch = _epoch(START)
    split_epoch = _epoch(SPLIT)
    end_epoch = _day_after(END)
    if not start_epoch < split_epoch < end_epoch:
        raise ValueError("research dates must satisfy START < SPLIT <= END")

    per_symbol: list[dict] = []
    for symbol in SYMBOLS:
        lower_path = DATA_ROOT / symbol / f"{symbol}_{LOWER_TF}.csv"
        higher_path = DATA_ROOT / symbol / f"{symbol}_{HIGHER_TF}.csv"
        lower_hist = _load_historical(lower_path, symbol, LOWER_TF, 500)
        higher_hist = _load_historical(higher_path, symbol, HIGHER_TF, 500)
        trends = align_higher_timeframe_trends(lower_hist, higher_hist)
        bars = _market_bars(lower_hist)
        events = _entry_events(bars, trends)

        first_bars, first_trends, first_events = _slice_by_time(
            bars, trends, events, start_epoch, split_epoch
        )
        second_bars, second_trends, second_events = _slice_by_time(
            bars, trends, events, split_epoch, end_epoch
        )

        results = {
            "full": {
                variant: _run_variant(bars, trends, events, variant)
                for variant in VARIANTS
            },
            "first_half": {
                variant: _run_variant(
                    first_bars, first_trends, first_events, variant
                )
                for variant in VARIANTS
            },
            "second_half": {
                variant: _run_variant(
                    second_bars, second_trends, second_events, variant
                )
                for variant in VARIANTS
            },
        }
        per_symbol.append({
            "symbol": symbol,
            "full": {
                variant: _compact(results["full"][variant])
                for variant in VARIANTS
            },
            "first_half": {
                variant: _compact(results["first_half"][variant])
                for variant in VARIANTS
            },
            "second_half": {
                variant: _compact(results["second_half"][variant])
                for variant in VARIANTS
            },
            "_results": results,
        })

    aggregate = {
        variant: {
            phase: _aggregate(per_symbol, variant, phase)
            for phase in ("full", "first_half", "second_half")
        }
        for variant in VARIANTS
    }
    serializable = [
        {key: value for key, value in entry.items() if key != "_results"}
        for entry in per_symbol
    ]
    output = {
        "experiment_id": "market_accelerator_short_timesplit_v1",
        "period": f"{START}..{END}",
        "split": SPLIT,
        "symbols": list(SYMBOLS),
        "variants": list(VARIANTS),
        "activation_definition": (
            "previous IDLE/DECELERATING -> current START/FAST; signed_speed<0"
        ),
        "formula_modified": False,
        "regime_thresholds_modified": False,
        "stop_buffer_pct": STOP_BUFFER_PCT,
        "target_r": TARGET_R,
        "friction": "zero",
        "entry_execution": "closed_signal_next_bar_open_v1",
        "parameter_optimization": False,
        "per_symbol": serializable,
        "aggregate": aggregate,
    }

    destination = Path("research_results/market_accelerator_short_timesplit.json")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(output, indent=2), encoding="utf-8")

    print("=== MARKET_ACCELERATOR_SHORT_TIMESPLIT ===")
    print("PERIOD", START, END, "SPLIT", SPLIT, "SYMBOLS", SYMBOLS)
    for variant in VARIANTS:
        print("---", variant, "---")
        for phase in ("full", "first_half", "second_half"):
            print(phase, aggregate[variant][phase])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
