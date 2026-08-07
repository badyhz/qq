#!/usr/bin/env python3
"""Temporary multi-symbol IronTop SHORT research for INDICATOR_COMPOSITE_V1.

Research branch only; do not merge.

This experiment uses the exact recovered IronTop formula without changing its
30/55-bar highs, 5-bar speed, prior-55 speed baseline, 1.5 sigma threshold, or
weak-close rule.  It tests four pre-declared entry variants on the same 12-month
zero-friction sample:

A_STRONG_ONLY       = strength == 2
B_STRONG_HTF        = strength == 2 and higher-timeframe trend is not UP
C_ANY_IRON_TOP      = strength >= 1
D_ANY_IRON_TOP_HTF  = strength >= 1 and higher-timeframe trend is not UP

Execution is conservative and identical across variants:
- signal becomes known only after bar i closes;
- SHORT entry is bar i+1 open;
- stop is signal-bar high + 0.10%;
- target is fixed 2R;
- existing Shadow TradeIntent risk gate is reused;
- existing offline simulator runs with entry_execution='bar_open';
- one simulated exposure at a time, no overlapping positions;
- no parameter optimization, fees, slippage, accounts, orders, Testnet or Live.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
import statistics
import sys

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from core.offline_backtest_metrics_engine import compute_run_metrics
from core.offline_backtest_trade_simulator import (
    TradeSimulationParams,
    simulate_trade,
)
from core.paper_trading.aicoin_indicator_ports import evaluate_iron_top
from core.paper_trading.higher_timeframe_trend import align_higher_timeframe_trends
from core.paper_trading.indicator_composite_strategy import HigherTimeframeTrend
from core.paper_trading.trade_intent_risk_gate import validate_trade_intent
from scripts.prepare_indicator_composite_history import DEFAULT_SYMBOLS
from scripts.run_indicator_composite_backtest import _load_historical, _market_bars


START = "2025-08-01"
END = "2026-07-31"
LOWER_TF = "15m"
HIGHER_TF = "1h"
DATA_ROOT = Path("data/indicator_composite_history")
STOP_BUFFER_PCT = 0.10
TARGET_R = 2.0
MAX_RISK_PCT = 0.5
MAX_HOLD_BARS = 100

VARIANTS = (
    "A_STRONG_ONLY",
    "B_STRONG_HTF",
    "C_ANY_IRON_TOP",
    "D_ANY_IRON_TOP_HTF",
)


def _iron_strengths(bars) -> tuple[int, ...]:
    """Evaluate exact IronTop using only the minimum required rolling window."""
    strengths = [0] * len(bars)
    for index in range(60, len(bars)):
        result = evaluate_iron_top(bars[index - 60:index + 1])
        strengths[index] = result.strength
    return tuple(strengths)


def _variant_matches(
    strength: int,
    trend: HigherTimeframeTrend,
    variant: str,
) -> bool:
    if variant == "A_STRONG_ONLY":
        return strength == 2
    if variant == "B_STRONG_HTF":
        return strength == 2 and trend != HigherTimeframeTrend.UP
    if variant == "C_ANY_IRON_TOP":
        return strength >= 1
    if variant == "D_ANY_IRON_TOP_HTF":
        return strength >= 1 and trend != HigherTimeframeTrend.UP
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


def _run_variant(bars, strengths, trends, variant: str) -> dict:
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

    for signal_index, (strength, trend) in enumerate(zip(strengths, trends)):
        if not _variant_matches(strength, trend, variant):
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

        signal = {
            "signal_id": f"iron_top_short_{variant}_{signal_index}",
            "signal_bar_index": signal_index,
            "entry_bar_index": entry_index,
            "entry_execution": "bar_open",
            "entry_price": entry_price,
            "stop_price": stop_price,
            "tp_price": take_profit,
        }
        outcome = simulate_trade(signal, bar_dicts, params)
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


def _aggregate(per_symbol: list[dict], variant: str) -> dict:
    all_r: list[float] = []
    symbol_pfs: list[float] = []
    positive_symbols: list[str] = []
    worst_symbol_drawdown = 0.0
    total_raw_signals = 0

    for entry in per_symbol:
        full = entry["_full_results"][variant]
        compact = entry["variants"][variant]
        total_raw_signals += compact["raw_signals"]
        symbol_pfs.append(float(compact["profit_factor"]))
        worst_symbol_drawdown = min(
            worst_symbol_drawdown,
            float(compact["max_drawdown_r"]),
        )
        if float(compact["expectancy_r"]) > 0:
            positive_symbols.append(entry["symbol"])
        all_r.extend(float(trade["realized_r"]) for trade in full["trades"])

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
        "variant": variant,
        "symbol_count": len(per_symbol),
        "total_raw_signals": total_raw_signals,
        "total_trades": len(all_r),
        "combined_win_rate": round(len(wins) / len(all_r), 6) if all_r else 0.0,
        "combined_expectancy_r": round(sum(all_r) / len(all_r), 6) if all_r else 0.0,
        "combined_profit_factor": round(combined_pf, 6),
        "median_symbol_profit_factor": round(
            statistics.median(symbol_pfs), 6
        ) if symbol_pfs else 0.0,
        "positive_expectancy_symbols": positive_symbols,
        "positive_symbol_count": len(positive_symbols),
        "worst_symbol_drawdown_r": round(worst_symbol_drawdown, 6),
        "portfolio_drawdown_not_computed": True,
    }


def main() -> int:
    per_symbol: list[dict] = []

    for symbol in DEFAULT_SYMBOLS:
        lower_path = DATA_ROOT / symbol / f"{symbol}_{LOWER_TF}.csv"
        higher_path = DATA_ROOT / symbol / f"{symbol}_{HIGHER_TF}.csv"
        lower_hist = _load_historical(lower_path, symbol, LOWER_TF, 500)
        higher_hist = _load_historical(higher_path, symbol, HIGHER_TF, 500)
        trends = align_higher_timeframe_trends(lower_hist, higher_hist)
        bars = _market_bars(lower_hist)
        strengths = _iron_strengths(bars)

        full_results = {
            variant: _run_variant(bars, strengths, trends, variant)
            for variant in VARIANTS
        }
        per_symbol.append({
            "symbol": symbol,
            "lower_bars": len(lower_hist),
            "higher_bars": len(higher_hist),
            "iron_strength_1_count": sum(value == 1 for value in strengths),
            "iron_strength_2_count": sum(value == 2 for value in strengths),
            "variants": {
                variant: _compact(result)
                for variant, result in full_results.items()
            },
            "_full_results": full_results,
        })

    aggregates = {
        variant: _aggregate(per_symbol, variant)
        for variant in VARIANTS
    }
    serializable = [
        {key: value for key, value in entry.items() if key != "_full_results"}
        for entry in per_symbol
    ]
    output = {
        "experiment_id": "iron_top_short_multisymbol_v1",
        "period": f"{START}..{END}",
        "lower_timeframe": LOWER_TF,
        "higher_timeframe": HIGHER_TF,
        "symbols": list(DEFAULT_SYMBOLS),
        "variants": list(VARIANTS),
        "iron_top_formula_modified": False,
        "stop_buffer_pct": STOP_BUFFER_PCT,
        "target_r": TARGET_R,
        "max_risk_pct": MAX_RISK_PCT,
        "max_hold_bars": MAX_HOLD_BARS,
        "friction": "zero",
        "entry_execution": "closed_signal_next_bar_open_v1",
        "parameter_optimization": False,
        "per_symbol": serializable,
        "aggregate": aggregates,
    }

    destination = Path("research_results/iron_top_short_multisymbol.json")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(output, indent=2), encoding="utf-8")

    print("=== IRON_TOP_SHORT_MULTISYMBOL ===")
    for entry in serializable:
        print(
            entry["symbol"],
            "strength1=", entry["iron_strength_1_count"],
            "strength2=", entry["iron_strength_2_count"],
        )
        for variant in VARIANTS:
            values = entry["variants"][variant]
            print(
                " ", variant,
                "trades=", values["trades"],
                "win=", values["win_rate"],
                "exp=", values["expectancy_r"],
                "pf=", values["profit_factor"],
                "mdd=", values["max_drawdown_r"],
            )
    print("=== AGGREGATE ===")
    for variant in VARIANTS:
        print(variant, aggregates[variant])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
