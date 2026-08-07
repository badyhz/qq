#!/usr/bin/env python3
"""Two-year FAST-confirmed Market Accelerator SHORT research.

Research branch only; do not merge.

This is the final pre-declared structural interpretation for the recovered
疾速500 indicator and targets the user's original 'only catch big moves' intent.
No threshold is tuned: the existing START/FAST/EXTREME levels remain 20/40/80.

Entry event:
- current regime == FAST;
- previous regime in {IDLE, START, DECELERATING};
- previous regime is NOT FAST/EXTREME;
- signed_speed < 0;
- signal close -> next-bar-open SHORT.

Execution:
- stop = signal-bar high + 0.10%;
- fixed 2R target;
- existing Shadow TradeIntent risk gate;
- existing offline simulator with bar-open execution;
- one exposure at a time;
- EXTREME is never a new entry;
- 100-bar maximum hold.

Fee grid 0 / 0.5 / 1 bp per side is hypothetical research stress only, not an
approved P1-03 assumption. Slippage stays zero so fee robustness is isolated.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import statistics
import sys

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from core.offline_backtest_metrics_engine import compute_run_metrics
from core.offline_backtest_trade_simulator import TradeSimulationParams, simulate_trade
from core.paper_trading.indicator_composite_strategy import AccelerationRegime
from core.paper_trading.market_accelerator_port import (
    calculate_market_accelerator,
    classify_accelerator_series,
)
from core.paper_trading.trade_intent_risk_gate import validate_trade_intent
from scripts.prepare_indicator_composite_history import DEFAULT_SYMBOLS
from scripts.run_indicator_composite_backtest import _load_historical, _market_bars

START = os.environ.get("RESEARCH_START", "2024-08-01")
SPLIT = os.environ.get("RESEARCH_SPLIT", "2025-08-01")
END = os.environ.get("RESEARCH_END", "2026-07-31")
SYMBOLS = tuple(
    value.strip().upper()
    for value in os.environ.get("RESEARCH_SYMBOLS", ",".join(DEFAULT_SYMBOLS)).split(",")
    if value.strip()
)
LOWER_TF = "15m"
DATA_ROOT = Path("data/indicator_composite_history")
STOP_BUFFER_PCT = 0.10
TARGET_R = 2.0
MAX_RISK_PCT = 0.5
MAX_HOLD_BARS = 100
FEE_BPS_GRID = (0.0, 0.5, 1.0)
_PRE_FAST = {
    AccelerationRegime.IDLE,
    AccelerationRegime.START,
    AccelerationRegime.DECELERATING,
}


def _epoch(day: str) -> float:
    return datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp()


def _day_after(day: str) -> float:
    dt = datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return (dt + timedelta(days=1)).timestamp()


def _fast_entries(bars) -> tuple[bool, ...]:
    series = calculate_market_accelerator(bars)
    regimes = classify_accelerator_series(series.points)
    entries = [False] * len(bars)
    for index in range(1, len(bars)):
        signed_speed = series.points[index].signed_speed
        entries[index] = bool(
            regimes[index - 1].regime in _PRE_FAST
            and regimes[index].regime == AccelerationRegime.FAST
            and signed_speed is not None
            and signed_speed < 0
        )
    return tuple(entries)


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


def _run_symbol(symbol: str, bars, entries, fee_bps: float) -> dict:
    bar_dicts = [_bar_dict(bar) for bar in bars]
    params = TradeSimulationParams(
        slippage_pct=0.0,
        fee_pct=fee_bps / 10000.0,
        max_hold_bars=MAX_HOLD_BARS,
    )
    unavailable_until = -1
    trades: list[dict] = []
    raw_signals = 0
    blocked_invalid = 0
    blocked_risk_gate = 0
    blocked_overlap = 0

    for signal_index, active in enumerate(entries):
        if not active:
            continue
        raw_signals += 1
        entry_index = signal_index + 1
        if entry_index >= len(bars):
            continue

        entry_price = float(bars[entry_index].open)
        stop_price = float(bars[signal_index].high) * (1.0 + STOP_BUFFER_PCT / 100.0)
        if entry_price <= 0 or entry_price >= stop_price:
            blocked_invalid += 1
            continue

        risk = stop_price - entry_price
        take_profit = entry_price - TARGET_R * risk
        if take_profit <= 0:
            blocked_invalid += 1
            continue

        risk_distance_pct = risk / entry_price * 100.0
        gate = validate_trade_intent({
            "execution_mode": "shadow_only",
            "side": "SHORT",
            "intent_status": "SHADOW_READY",
            "rr_ratio": TARGET_R,
            "risk_distance_pct": risk_distance_pct,
            "reward_distance_pct": TARGET_R * risk_distance_pct,
            "max_risk_pct": MAX_RISK_PCT,
            "entry_price": entry_price,
            "stop_loss": stop_price,
            "take_profit": take_profit,
        })
        if not gate.passed:
            blocked_risk_gate += 1
            continue
        if entry_index <= unavailable_until:
            blocked_overlap += 1
            continue

        outcome = simulate_trade(
            {
                "signal_id": f"fast_short_{symbol}_{signal_index}",
                "entry_bar_index": entry_index,
                "entry_execution": "bar_open",
                "entry_price": entry_price,
                "stop_price": stop_price,
                "tp_price": take_profit,
            },
            bar_dicts,
            params,
        )
        trades.append({
            "trade_id": outcome.trade_id,
            "signal_id": outcome.signal_id,
            "entry_timestamp": float(bars[entry_index].timestamp),
            "entry_bar_index": outcome.entry_bar_index,
            "exit_bar_index": outcome.exit_bar_index,
            "realized_r": outcome.realized_r,
            "gross_pnl": outcome.gross_pnl,
            "fees": outcome.fees,
            "slippage_cost": outcome.slippage_cost,
            "net_pnl": outcome.net_pnl,
            "mfe_r": outcome.mfe_r,
            "mae_r": outcome.mae_r,
            "hold_bars": outcome.hold_bars,
            "risk_distance_pct": risk_distance_pct,
        })
        unavailable_until = outcome.exit_bar_index

    return {
        "symbol": symbol,
        "fee_bps_per_side": fee_bps,
        "raw_signals": raw_signals,
        "trade_count": len(trades),
        "blocked_invalid_execution": blocked_invalid,
        "blocked_risk_gate": blocked_risk_gate,
        "blocked_overlap": blocked_overlap,
        "metrics": compute_run_metrics(trades),
        "trades": trades,
    }


def _aggregate(results: list[dict], lower: float, upper: float) -> dict:
    trades = [
        trade
        for result in results
        for trade in result["trades"]
        if lower <= float(trade["entry_timestamp"]) < upper
    ]
    metrics = compute_run_metrics(trades)
    risks = [float(trade["risk_distance_pct"]) for trade in trades]
    holds = [int(trade["hold_bars"]) for trade in trades]
    positive_symbols = []
    for result in results:
        symbol_trades = [
            trade for trade in result["trades"]
            if lower <= float(trade["entry_timestamp"]) < upper
        ]
        if float(compute_run_metrics(symbol_trades)["expectancy_r"]) > 0:
            positive_symbols.append(result["symbol"])
    return {
        "total_trades": len(trades),
        "win_rate": metrics["win_rate"],
        "expectancy_r": metrics["expectancy_r"],
        "profit_factor": metrics["profit_factor"],
        "max_drawdown_r_not_portfolio_valid": metrics["max_drawdown_r"],
        "avg_mfe_r": metrics["avg_mfe_r"],
        "avg_mae_r": metrics["avg_mae_r"],
        "median_risk_distance_pct": round(statistics.median(risks), 6) if risks else 0.0,
        "mean_risk_distance_pct": round(statistics.mean(risks), 6) if risks else 0.0,
        "median_hold_bars": round(statistics.median(holds), 3) if holds else 0.0,
        "positive_expectancy_symbols": positive_symbols,
        "positive_symbol_count": len(positive_symbols),
        "portfolio_drawdown_not_computed": True,
    }


def main() -> int:
    start_epoch = _epoch(START)
    split_epoch = _epoch(SPLIT)
    end_epoch = _day_after(END)
    if not SYMBOLS or not start_epoch < split_epoch < end_epoch:
        raise ValueError("invalid symbols or research window")

    loaded = {}
    for symbol in SYMBOLS:
        path = DATA_ROOT / symbol / f"{symbol}_{LOWER_TF}.csv"
        history = _load_historical(path, symbol, LOWER_TF, 500)
        bars = _market_bars(history)
        loaded[symbol] = (bars, _fast_entries(bars))

    rows = []
    for fee_bps in FEE_BPS_GRID:
        results = [
            _run_symbol(symbol, bars, entries, fee_bps)
            for symbol, (bars, entries) in loaded.items()
        ]
        rows.append({
            "fee_bps_per_side": fee_bps,
            "nominal_round_trip_fee_bps": fee_bps * 2.0,
            "phases": {
                "full": _aggregate(results, start_epoch, end_epoch),
                "first_year": _aggregate(results, start_epoch, split_epoch),
                "second_year": _aggregate(results, split_epoch, end_epoch),
            },
        })

    output = {
        "experiment_id": "market_accelerator_fast_confirmed_short_v1",
        "period": f"{START}..{END}",
        "split": SPLIT,
        "symbols": list(SYMBOLS),
        "entry_definition": "current FAST; previous IDLE/START/DECELERATING; signed_speed<0",
        "extreme_entry": False,
        "stop_buffer_pct": STOP_BUFFER_PCT,
        "target_r": TARGET_R,
        "max_hold_bars": MAX_HOLD_BARS,
        "fee_grid_bps_per_side": list(FEE_BPS_GRID),
        "fee_grid_status": "hypothetical_research_stress_not_p1_03",
        "slippage_pct": 0.0,
        "formula_modified": False,
        "regime_thresholds_modified": False,
        "parameter_optimization": False,
        "entry_execution": "closed_signal_next_bar_open_v1",
        "rows": rows,
    }
    destination = Path("research_results/market_accelerator_fast_confirmed_short.json")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(output, indent=2), encoding="utf-8")

    print("=== MARKET_ACCELERATOR_FAST_CONFIRMED_SHORT ===")
    for row in rows:
        print("FEE_BPS_PER_SIDE", row["fee_bps_per_side"])
        for phase in ("full", "first_year", "second_year"):
            print(phase, row["phases"][phase])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
