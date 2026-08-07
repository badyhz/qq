#!/usr/bin/env python3
"""Temporary multi-symbol robustness research for INDICATOR_COMPOSITE_V1.

Research branch only; do not merge. Uses only the exact, formula-free price
event already confirmed by the user:

    prior-30 new low + close above previous bar low

It runs the existing A/B/C ablation on the full 12-month sample and then, with
no parameter changes, checks the full C strategy independently in the first and
second six-month halves. Full-history states are built before slicing so the
second half retains realistic indicator warm-up from prior history while every
state remains no-lookahead.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import statistics
import sys

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from core.indicator_composite_backtest import (
    CompositeBacktestConfig,
    run_indicator_composite_ablation,
    run_indicator_composite_backtest,
)
from core.offline_backtest_trade_simulator import TradeSimulationParams
from core.paper_trading.higher_timeframe_trend import align_higher_timeframe_trends
from core.paper_trading.indicator_composite_adapter import (
    build_external_bottom_composite_states,
)
from scripts.prepare_indicator_composite_history import DEFAULT_SYMBOLS
from scripts.run_indicator_composite_backtest import _load_historical, _market_bars


START = "2025-08-01"
SPLIT = "2026-02-01"
END = "2026-07-31"
LOWER_TF = "15m"
HIGHER_TF = "1h"
DATA_ROOT = Path("data/indicator_composite_history")


def _epoch(day: str) -> float:
    return datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp()


def _dedupe_immediate(raw: list[bool]) -> list[bool]:
    return [
        value and (index == 0 or not raw[index - 1])
        for index, value in enumerate(raw)
    ]


def _confirmed_price_action_triggers(bars) -> list[bool]:
    lows = [float(bar.low) for bar in bars]
    closes = [float(bar.close) for bar in bars]
    raw: list[bool] = []
    for index in range(len(bars)):
        previous_lows = lows[max(0, index - 30):index]
        new_low_30 = bool(previous_lows) and lows[index] < min(previous_lows)
        reclaim = index > 0 and closes[index] > lows[index - 1]
        raw.append(new_low_30 and reclaim)
    return _dedupe_immediate(raw)


def _compact_result(result: dict) -> dict:
    metrics = result["metrics"]
    return {
        "signals": result["signal_count"],
        "trades": result["trade_count"],
        "win_rate": metrics["win_rate"],
        "expectancy_r": metrics["expectancy_r"],
        "profit_factor": metrics["profit_factor"],
        "max_drawdown_r": metrics["max_drawdown_r"],
        "avg_mfe_r": metrics["avg_mfe_r"],
        "avg_mae_r": metrics["avg_mae_r"],
        "blocked_risk_gate": result["blocked_risk_gate"],
        "blocked_invalid_execution": result["blocked_invalid_execution"],
        "blocked_no_next_bar": result["blocked_no_next_bar"],
    }


def _slice_by_time(bars, states, start_epoch: float, end_epoch: float):
    pairs = [
        (bar, state)
        for bar, state in zip(bars, states)
        if start_epoch <= float(bar.timestamp) < end_epoch
    ]
    return (
        tuple(pair[0] for pair in pairs),
        tuple(pair[1] for pair in pairs),
    )


def _aggregate_c(per_symbol: list[dict]) -> dict:
    all_r: list[float] = []
    pfs: list[float] = []
    positive_symbols: list[str] = []
    pf_over_one_symbols: list[str] = []
    stable_both_halves: list[str] = []
    total_signals = 0
    worst_symbol_drawdown = 0.0

    for entry in per_symbol:
        c_full = entry["_c_full"]
        compact = entry["variants"]["C_BOTTOM_ACCELERATOR_HTF"]
        total_signals += compact["signals"]
        pfs.append(float(compact["profit_factor"]))
        worst_symbol_drawdown = min(
            worst_symbol_drawdown,
            float(compact["max_drawdown_r"]),
        )
        if float(compact["expectancy_r"]) > 0:
            positive_symbols.append(entry["symbol"])
        if float(compact["profit_factor"]) > 1:
            pf_over_one_symbols.append(entry["symbol"])

        h1 = entry["walk_forward_halves"]["first_half"]
        h2 = entry["walk_forward_halves"]["second_half"]
        if (
            h1["trades"] >= 10
            and h2["trades"] >= 10
            and float(h1["expectancy_r"]) > 0
            and float(h2["expectancy_r"]) > 0
            and float(h1["profit_factor"]) > 1
            and float(h2["profit_factor"]) > 1
        ):
            stable_both_halves.append(entry["symbol"])

        all_r.extend(float(trade["realized_r"]) for trade in c_full["trades"])

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
        "symbol_count": len(per_symbol),
        "total_signals": total_signals,
        "total_trades": len(all_r),
        "combined_win_rate": round(len(wins) / len(all_r), 6) if all_r else 0.0,
        "combined_expectancy_r": round(sum(all_r) / len(all_r), 6) if all_r else 0.0,
        "combined_profit_factor": round(combined_pf, 6),
        "median_symbol_profit_factor": round(statistics.median(pfs), 6) if pfs else 0.0,
        "worst_symbol_drawdown_r": round(worst_symbol_drawdown, 6),
        "positive_expectancy_symbols": positive_symbols,
        "profit_factor_over_one_symbols": pf_over_one_symbols,
        "positive_symbol_count": len(positive_symbols),
        "pf_over_one_symbol_count": len(pf_over_one_symbols),
        "stable_positive_both_halves": stable_both_halves,
        "stable_positive_both_halves_count": len(stable_both_halves),
        "stability_rule": "each_half_trades>=10_and_expectancy>0_and_pf>1",
        "portfolio_drawdown_not_computed": True,
    }


def main() -> int:
    config = CompositeBacktestConfig(
        simulation=TradeSimulationParams(
            slippage_pct=0.0,
            fee_pct=0.0,
            max_hold_bars=100,
        )
    )
    records: list[dict] = []
    start_epoch = _epoch(START)
    split_epoch = _epoch(SPLIT)
    end_epoch = _epoch("2026-08-01")

    for symbol in DEFAULT_SYMBOLS:
        lower_path = DATA_ROOT / symbol / f"{symbol}_{LOWER_TF}.csv"
        higher_path = DATA_ROOT / symbol / f"{symbol}_{HIGHER_TF}.csv"
        lower_hist = _load_historical(lower_path, symbol, LOWER_TF, 500)
        higher_hist = _load_historical(higher_path, symbol, HIGHER_TF, 500)
        trends = align_higher_timeframe_trends(lower_hist, higher_hist)
        bars = _market_bars(lower_hist)
        triggers = _confirmed_price_action_triggers(bars)
        states = build_external_bottom_composite_states(bars, triggers, trends)
        ablation = run_indicator_composite_ablation(bars, states, config)

        variants = {
            entry["variant"]: _compact_result(entry["result"])
            for entry in ablation["variants"]
        }
        c_full = next(
            entry["result"]
            for entry in ablation["variants"]
            if entry["variant"] == "C_BOTTOM_ACCELERATOR_HTF"
        )

        first_bars, first_states = _slice_by_time(
            bars, states, start_epoch, split_epoch
        )
        second_bars, second_states = _slice_by_time(
            bars, states, split_epoch, end_epoch
        )
        first_result = run_indicator_composite_backtest(
            first_bars, first_states, config
        )
        second_result = run_indicator_composite_backtest(
            second_bars, second_states, config
        )

        records.append({
            "symbol": symbol,
            "lower_bars": len(lower_hist),
            "higher_bars": len(higher_hist),
            "trigger_count": sum(triggers),
            "variants": variants,
            "walk_forward_halves": {
                "first_half": _compact_result(first_result),
                "second_half": _compact_result(second_result),
            },
            "_c_full": c_full,
        })

    aggregate = _aggregate_c(records)
    serializable_records = []
    for entry in records:
        serializable_records.append({
            key: value for key, value in entry.items() if key != "_c_full"
        })

    output = {
        "experiment_id": "confirmed_price_action_multisymbol_v1",
        "definition": "prior_30_new_low_and_close_above_previous_low",
        "period": f"{START}..{END}",
        "walk_forward_split": SPLIT,
        "lower_timeframe": LOWER_TF,
        "higher_timeframe": HIGHER_TF,
        "friction": "zero",
        "entry_execution": "closed_signal_next_bar_open_v1",
        "parameter_optimization": False,
        "symbols": list(DEFAULT_SYMBOLS),
        "per_symbol": serializable_records,
        "aggregate_c": aggregate,
    }

    destination = Path("research_results/multisymbol_confirmed_price_action.json")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(output, indent=2), encoding="utf-8")

    print("=== MULTISYMBOL_CONFIRMED_PRICE_ACTION ===")
    for entry in serializable_records:
        c = entry["variants"]["C_BOTTOM_ACCELERATOR_HTF"]
        h1 = entry["walk_forward_halves"]["first_half"]
        h2 = entry["walk_forward_halves"]["second_half"]
        print(
            entry["symbol"],
            "FULL trades=", c["trades"], "exp=", c["expectancy_r"], "pf=", c["profit_factor"],
            "H1 trades=", h1["trades"], "exp=", h1["expectancy_r"], "pf=", h1["profit_factor"],
            "H2 trades=", h2["trades"], "exp=", h2["expectancy_r"], "pf=", h2["profit_factor"],
        )
    print("AGGREGATE_C", aggregate)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
