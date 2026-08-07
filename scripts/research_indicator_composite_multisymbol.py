#!/usr/bin/env python3
"""Two-year fee sensitivity for the frozen Market Accelerator SHORT candidate.

Research branch only; do not merge.

Candidate C_SHORT_ACCEL is unchanged from prior discovery/validation:
- previous regime in {IDLE, DECELERATING};
- current regime in {START, FAST};
- signed_speed < 0;
- no HTF filter;
- fully closed signal bar -> next-bar-open SHORT;
- stop = signal-bar high + 0.10%;
- target = 2R;
- existing Shadow TradeIntent risk gate;
- one exposure at a time.

Only the per-side fee assumption changes.  Grid values are hypothetical research
stress inputs, NOT approved P1-03 assumptions. Slippage remains zero so the fee
break-even point is isolated cleanly.
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
FEE_BPS_GRID = (0.0, 0.5, 1.0, 1.5, 2.0)
_ACTIVE = {AccelerationRegime.START, AccelerationRegime.FAST}
_REARMED = {AccelerationRegime.IDLE, AccelerationRegime.DECELERATING}


def _epoch(day: str) -> float:
    return datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp()


def _day_after(day: str) -> float:
    dt = datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return (dt + timedelta(days=1)).timestamp()


def _events(bars) -> tuple[bool, ...]:
    series = calculate_market_accelerator(bars)
    regimes = classify_accelerator_series(series.points)
    output = [False] * len(bars)
    for index in range(1, len(bars)):
        signed_speed = series.points[index].signed_speed
        output[index] = bool(
            regimes[index - 1].regime in _REARMED
            and regimes[index].regime in _ACTIVE
            and signed_speed is not None
            and signed_speed < 0
        )
    return tuple(output)


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


def _slice(bars, events, start_epoch: float, end_epoch: float):
    selected = [
        (bar, event)
        for bar, event in zip(bars, events)
        if start_epoch <= float(bar.timestamp) < end_epoch
    ]
    return tuple(item[0] for item in selected), tuple(item[1] for item in selected)


def _run_symbol(symbol: str, bars, events, fee_bps: float) -> dict:
    bar_dicts = [_bar_dict(bar) for bar in bars]
    params = TradeSimulationParams(
        slippage_pct=0.0,
        fee_pct=fee_bps / 10000.0,
        max_hold_bars=MAX_HOLD_BARS,
    )
    unavailable_until = -1
    raw_signals = 0
    blocked_invalid_execution = 0
    blocked_risk_gate = 0
    blocked_overlap = 0
    risk_distances: list[float] = []
    trades: list[dict] = []

    for signal_index, active in enumerate(events):
        if not active:
            continue
        raw_signals += 1
        if signal_index + 1 >= len(bars):
            continue

        entry_index = signal_index + 1
        entry_price = float(bars[entry_index].open)
        stop_price = float(bars[signal_index].high) * (1.0 + STOP_BUFFER_PCT / 100.0)
        if entry_price <= 0 or entry_price >= stop_price:
            blocked_invalid_execution += 1
            continue

        risk = stop_price - entry_price
        take_profit = entry_price - TARGET_R * risk
        if take_profit <= 0:
            blocked_invalid_execution += 1
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
                "signal_id": f"accel_short_{symbol}_{signal_index}",
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
        risk_distances.append(risk_distance_pct)
        unavailable_until = outcome.exit_bar_index

    metrics = compute_run_metrics(trades)
    return {
        "symbol": symbol,
        "fee_bps_per_side": fee_bps,
        "raw_signals": raw_signals,
        "trade_count": len(trades),
        "blocked_invalid_execution": blocked_invalid_execution,
        "blocked_risk_gate": blocked_risk_gate,
        "blocked_overlap": blocked_overlap,
        "median_risk_distance_pct": round(statistics.median(risk_distances), 6) if risk_distances else 0.0,
        "mean_risk_distance_pct": round(statistics.mean(risk_distances), 6) if risk_distances else 0.0,
        "metrics": metrics,
        "trades": trades,
    }


def _aggregate(results: list[dict]) -> dict:
    trades = [trade for result in results for trade in result["trades"]]
    metrics = compute_run_metrics(trades)
    risk_distances = [float(trade["risk_distance_pct"]) for trade in trades]
    return {
        "total_trades": len(trades),
        "win_rate": metrics["win_rate"],
        "expectancy_r": metrics["expectancy_r"],
        "profit_factor": metrics["profit_factor"],
        "max_drawdown_r_not_portfolio_valid": metrics["max_drawdown_r"],
        "avg_mfe_r": metrics["avg_mfe_r"],
        "avg_mae_r": metrics["avg_mae_r"],
        "median_risk_distance_pct": round(statistics.median(risk_distances), 6) if risk_distances else 0.0,
        "mean_risk_distance_pct": round(statistics.mean(risk_distances), 6) if risk_distances else 0.0,
        "positive_expectancy_symbols": [
            result["symbol"] for result in results
            if float(result["metrics"]["expectancy_r"]) > 0
        ],
        "portfolio_drawdown_not_computed": True,
    }


def main() -> int:
    start_epoch = _epoch(START)
    split_epoch = _epoch(SPLIT)
    end_epoch = _day_after(END)
    if not SYMBOLS or not start_epoch < split_epoch < end_epoch:
        raise ValueError("invalid symbols or research date window")

    loaded = {}
    for symbol in SYMBOLS:
        path = DATA_ROOT / symbol / f"{symbol}_{LOWER_TF}.csv"
        history = _load_historical(path, symbol, LOWER_TF, 500)
        bars = _market_bars(history)
        loaded[symbol] = (bars, _events(bars))

    rows = []
    for fee_bps in FEE_BPS_GRID:
        phases = {}
        for phase, lower, upper in (
            ("full", start_epoch, end_epoch),
            ("first_year", start_epoch, split_epoch),
            ("second_year", split_epoch, end_epoch),
        ):
            results = []
            for symbol, (bars, events) in loaded.items():
                phase_bars, phase_events = _slice(bars, events, lower, upper)
                results.append(_run_symbol(symbol, phase_bars, phase_events, fee_bps))
            phases[phase] = {
                "aggregate": _aggregate(results),
                "per_symbol": [
                    {
                        "symbol": result["symbol"],
                        "trades": result["trade_count"],
                        "win_rate": result["metrics"]["win_rate"],
                        "expectancy_r": result["metrics"]["expectancy_r"],
                        "profit_factor": result["metrics"]["profit_factor"],
                        "median_risk_distance_pct": result["median_risk_distance_pct"],
                    }
                    for result in results
                ],
            }
        rows.append({
            "fee_bps_per_side": fee_bps,
            "nominal_round_trip_fee_bps": fee_bps * 2.0,
            "phases": phases,
        })

    output = {
        "experiment_id": "market_accelerator_short_fee_sensitivity_v1",
        "candidate": "C_SHORT_ACCEL",
        "period": f"{START}..{END}",
        "split": SPLIT,
        "symbols": list(SYMBOLS),
        "activation_definition": "previous IDLE/DECELERATING -> current START/FAST; signed_speed<0",
        "formula_modified": False,
        "regime_thresholds_modified": False,
        "stop_buffer_pct": STOP_BUFFER_PCT,
        "target_r": TARGET_R,
        "slippage_pct": 0.0,
        "fee_grid_bps_per_side": list(FEE_BPS_GRID),
        "fee_grid_status": "hypothetical_research_stress_not_p1_03",
        "entry_execution": "closed_signal_next_bar_open_v1",
        "parameter_optimization": False,
        "rows": rows,
    }
    destination = Path("research_results/market_accelerator_short_fee_sensitivity.json")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(output, indent=2), encoding="utf-8")

    print("=== MARKET_ACCELERATOR_SHORT_FEE_SENSITIVITY ===")
    for row in rows:
        print("FEE_BPS_PER_SIDE", row["fee_bps_per_side"])
        for phase in ("full", "first_year", "second_year"):
            print(phase, row["phases"][phase]["aggregate"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
