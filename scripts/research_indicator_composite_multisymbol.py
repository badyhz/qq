#!/usr/bin/env python3
"""Two-year lifecycle research for the recovered Market Accelerator.

Research branch only; do not merge.

The entry is frozen from C_SHORT_ACCEL:
- previous regime in {IDLE, DECELERATING};
- current regime in {START, FAST};
- signed_speed < 0;
- signal close -> next-bar-open SHORT;
- protective stop = signal-bar high + 0.10%;
- one exposure at a time.

The only strategy change is role-correct exit behavior.  There is no fixed 2R
profit target.  After entry, hold the short while negative acceleration remains
active and exit on the next bar open after the first completed bar where any of
these is true:
- regime becomes DECELERATING;
- regime becomes IDLE;
- signed_speed becomes non-negative.

A 100-bar fail-safe maximum hold remains. Fees are isolated with a hypothetical
0 / 0.5 / 1 bp-per-side grid; slippage stays zero. Fee values are research
stress inputs, not P1-03 assumptions.
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
from core.paper_trading.indicator_composite_strategy import AccelerationRegime
from core.paper_trading.market_accelerator_port import (
    calculate_market_accelerator,
    classify_accelerator_series,
)
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
MAX_HOLD_BARS = 100
FEE_BPS_GRID = (0.0, 0.5, 1.0)
_ACTIVE = {AccelerationRegime.START, AccelerationRegime.FAST}
_REARMED = {AccelerationRegime.IDLE, AccelerationRegime.DECELERATING}
_EXIT_REGIMES = {AccelerationRegime.IDLE, AccelerationRegime.DECELERATING}


def _epoch(day: str) -> float:
    return datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp()


def _day_after(day: str) -> float:
    dt = datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return (dt + timedelta(days=1)).timestamp()


def _indicator_state(bars):
    series = calculate_market_accelerator(bars)
    regimes = classify_accelerator_series(series.points)
    entries = [False] * len(bars)
    exits = [False] * len(bars)

    for index in range(1, len(bars)):
        point = series.points[index]
        signed_speed = point.signed_speed
        entries[index] = bool(
            regimes[index - 1].regime in _REARMED
            and regimes[index].regime in _ACTIVE
            and signed_speed is not None
            and signed_speed < 0
        )
        exits[index] = bool(
            regimes[index].regime in _EXIT_REGIMES
            or (signed_speed is not None and signed_speed >= 0)
        )
    return tuple(entries), tuple(exits)


def _simulate_symbol(symbol: str, bars, entries, exits, fee_bps: float) -> dict:
    fee_pct = fee_bps / 10000.0
    unavailable_until = -1
    trades: list[dict] = []
    blocked_invalid = 0
    blocked_overlap = 0
    raw_signals = 0

    for signal_index, active in enumerate(entries):
        if not active:
            continue
        raw_signals += 1
        entry_index = signal_index + 1
        if entry_index >= len(bars):
            continue
        if entry_index <= unavailable_until:
            blocked_overlap += 1
            continue

        entry_price = float(bars[entry_index].open)
        stop_price = float(bars[signal_index].high) * (1.0 + STOP_BUFFER_PCT / 100.0)
        if entry_price <= 0 or entry_price >= stop_price:
            blocked_invalid += 1
            continue

        risk_distance = stop_price - entry_price
        risk_distance_pct = risk_distance / entry_price * 100.0
        if risk_distance_pct <= 0 or risk_distance_pct > 5.0:
            blocked_invalid += 1
            continue

        best_favorable = 0.0
        worst_adverse = 0.0
        exit_index = entry_index
        exit_price = entry_price
        exit_reason = "END_OF_DATA"
        scan_end = min(entry_index + MAX_HOLD_BARS, len(bars) - 1)

        for index in range(entry_index, scan_end + 1):
            high = float(bars[index].high)
            low = float(bars[index].low)
            best_favorable = max(
                best_favorable,
                (entry_price - low) / risk_distance,
            )
            worst_adverse = max(
                worst_adverse,
                (high - entry_price) / risk_distance,
            )

            if high >= stop_price:
                exit_index = index
                exit_price = stop_price
                exit_reason = "STOP_LOSS"
                break

            # Exit signal is only known after this bar closes, so fill at the
            # next bar open. Do not inspect the next bar's high/low first.
            if exits[index] and index + 1 < len(bars):
                exit_index = index + 1
                exit_price = float(bars[index + 1].open)
                exit_reason = "ACCELERATOR_DECELERATION"
                break

            if index == scan_end:
                if index + 1 < len(bars):
                    exit_index = index + 1
                    exit_price = float(bars[index + 1].open)
                else:
                    exit_index = index
                    exit_price = float(bars[index].close)
                exit_reason = "MAX_HOLD"

        gross_pnl = entry_price - exit_price
        fees = (entry_price + exit_price) * fee_pct
        net_pnl = gross_pnl - fees
        realized_r = net_pnl / risk_distance
        trades.append({
            "trade_id": f"lifecycle_{symbol}_{signal_index}",
            "signal_id": f"accelerator_short_{symbol}_{signal_index}",
            "entry_bar_index": entry_index,
            "exit_bar_index": exit_index,
            "entry_timestamp": float(bars[entry_index].timestamp),
            "entry_price": entry_price,
            "exit_price": exit_price,
            "exit_reason": exit_reason,
            "realized_r": round(realized_r, 6),
            "gross_pnl": round(gross_pnl, 6),
            "fees": round(fees, 6),
            "slippage_cost": 0.0,
            "net_pnl": round(net_pnl, 6),
            "mfe_r": round(best_favorable, 6),
            "mae_r": round(worst_adverse, 6),
            "hold_bars": exit_index - entry_index,
            "risk_distance_pct": risk_distance_pct,
        })
        unavailable_until = exit_index

    metrics = compute_run_metrics(trades)
    return {
        "symbol": symbol,
        "fee_bps_per_side": fee_bps,
        "raw_signals": raw_signals,
        "trade_count": len(trades),
        "blocked_invalid_execution": blocked_invalid,
        "blocked_overlap": blocked_overlap,
        "metrics": metrics,
        "trades": trades,
    }


def _phase_trades(results: list[dict], lower: float, upper: float) -> list[dict]:
    return [
        trade
        for result in results
        for trade in result["trades"]
        if lower <= float(trade["entry_timestamp"]) < upper
    ]


def _aggregate(results: list[dict], lower: float, upper: float) -> dict:
    trades = _phase_trades(results, lower, upper)
    metrics = compute_run_metrics(trades)
    risks = [float(trade["risk_distance_pct"]) for trade in trades]
    holds = [int(trade["hold_bars"]) for trade in trades]
    exit_reasons: dict[str, int] = {}
    for trade in trades:
        reason = str(trade["exit_reason"])
        exit_reasons[reason] = exit_reasons.get(reason, 0) + 1

    positive_symbols = []
    for result in results:
        symbol_trades = [
            trade for trade in result["trades"]
            if lower <= float(trade["entry_timestamp"]) < upper
        ]
        symbol_metrics = compute_run_metrics(symbol_trades)
        if float(symbol_metrics["expectancy_r"]) > 0:
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
        "mean_hold_bars": round(statistics.mean(holds), 3) if holds else 0.0,
        "positive_expectancy_symbols": positive_symbols,
        "positive_symbol_count": len(positive_symbols),
        "exit_reasons": exit_reasons,
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
        entries, exits = _indicator_state(bars)
        loaded[symbol] = (bars, entries, exits)

    rows = []
    for fee_bps in FEE_BPS_GRID:
        results = [
            _simulate_symbol(symbol, bars, entries, exits, fee_bps)
            for symbol, (bars, entries, exits) in loaded.items()
        ]
        phases = {
            "full": _aggregate(results, start_epoch, end_epoch),
            "first_year": _aggregate(results, start_epoch, split_epoch),
            "second_year": _aggregate(results, split_epoch, end_epoch),
        }
        rows.append({
            "fee_bps_per_side": fee_bps,
            "nominal_round_trip_fee_bps": fee_bps * 2.0,
            "phases": phases,
        })

    output = {
        "experiment_id": "market_accelerator_short_lifecycle_exit_v1",
        "period": f"{START}..{END}",
        "split": SPLIT,
        "symbols": list(SYMBOLS),
        "entry_definition": "previous IDLE/DECELERATING -> START/FAST; signed_speed<0",
        "exit_definition": "next open after DECELERATING/IDLE or signed_speed>=0",
        "fixed_take_profit": None,
        "protective_stop_buffer_pct": STOP_BUFFER_PCT,
        "max_hold_bars": MAX_HOLD_BARS,
        "fee_grid_bps_per_side": list(FEE_BPS_GRID),
        "fee_grid_status": "hypothetical_research_stress_not_p1_03",
        "slippage_pct": 0.0,
        "formula_modified": False,
        "regime_thresholds_modified": False,
        "parameter_optimization": False,
        "risk_gate_note": "dynamic exit cannot be represented by the current fixed-RR TradeIntent gate; structural stop constraints are enforced in this temporary research only",
        "rows": rows,
    }
    destination = Path("research_results/market_accelerator_short_lifecycle_exit.json")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(output, indent=2), encoding="utf-8")

    print("=== MARKET_ACCELERATOR_SHORT_LIFECYCLE_EXIT ===")
    for row in rows:
        print("FEE_BPS_PER_SIDE", row["fee_bps_per_side"])
        for phase in ("full", "first_year", "second_year"):
            print(phase, row["phases"][phase])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
