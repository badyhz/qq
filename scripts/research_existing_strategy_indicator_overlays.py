#!/usr/bin/env python3
"""Untouched older-year holdout for the existing weak_short_watch baseline.

Research branch only; do not merge.

This intentionally removes every new indicator overlay. The signal authority is
exactly the repository's existing production path:

    core.paper_trading.strategy_registry.analyze_for_strategy

Contract:
- XRPUSDT / ARBUSDT / DOGEUSDT;
- 15m + 1h;
- 2024-08-01 .. 2025-07-31, untouched older year;
- latest 120 completed bars per decision, matching live public-kline default;
- only HIGH/MEDIUM candidates, matching run_enabled_strategies payload behavior;
- signal known after bar close -> next-bar-open execution;
- existing candidate stop and 2R target preserved;
- actual next-open geometry revalidated with the existing Shadow risk gate;
- one exposure at a time per symbol/timeframe;
- 0 / 0.5 bp per-side hypothetical fee stress, zero slippage;
- no parameter tuning, symbol selection, indicator filter or production change.

The full-year simulation is authoritative. First/second-half metrics are only
subsets of those already simulated trades, bucketed by signal time, so no
artificial half-year boundary truncates an open trade.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from core.offline_backtest_metrics_engine import compute_run_metrics
from core.offline_backtest_trade_simulator import TradeSimulationParams, simulate_trade
from core.paper_trading.strategy_registry import SignalCandidate, analyze_for_strategy
from core.paper_trading.trade_intent_risk_gate import validate_trade_intent
from scripts.run_indicator_composite_backtest import _load_historical, _market_bars

START = "2024-08-01"
SPLIT = "2025-02-01"
END = "2025-07-31"
WINDOW_BARS = 120
MAX_HOLD_BARS = 100
FEE_BPS_GRID = (0.0, 0.5)
SYMBOLS = ("XRPUSDT", "ARBUSDT", "DOGEUSDT")
TIMEFRAMES = ("15m", "1h")
DATA_ROOT = Path("data/existing_strategy_overlay_history")


def _epoch(day: str) -> float:
    return datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp()


SPLIT_EPOCH = _epoch(SPLIT)


def _candidate_at(bars, index: int) -> SignalCandidate | None:
    if index + 1 < WINDOW_BARS:
        return None
    result = analyze_for_strategy(
        strategy_id="weak_short_watch",
        strategy_type="weak_short_watch",
        bars=list(bars[index - WINDOW_BARS + 1:index + 1]),
    )
    candidate = result.candidate if result.success else None
    if candidate is None or candidate.priority not in {"HIGH", "MEDIUM"}:
        return None
    return candidate


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


def _simulate_series(symbol: str, timeframe: str, bars, candidates, fee_bps: float) -> dict:
    params = TradeSimulationParams(
        fee_pct=fee_bps / 10000.0,
        slippage_pct=0.0,
        max_hold_bars=MAX_HOLD_BARS,
    )
    bar_dicts = [_bar_dict(bar) for bar in bars]
    unavailable_until = -1
    candidate_count = 0
    blocked_no_next_bar = 0
    blocked_geometry = 0
    blocked_overlap = 0
    trades: list[dict] = []

    for signal_index, candidate in enumerate(candidates):
        if candidate is None:
            continue
        candidate_count += 1
        entry_index = signal_index + 1
        if entry_index >= len(bars):
            blocked_no_next_bar += 1
            continue
        if entry_index <= unavailable_until:
            blocked_overlap += 1
            continue

        entry = float(bars[entry_index].open)
        stop = float(candidate.invalidation_level)
        target = float(candidate.take_profit_observation)
        risk = stop - entry
        reward = entry - target
        if entry <= 0 or stop <= 0 or target <= 0 or risk <= 0 or reward <= 0:
            blocked_geometry += 1
            continue

        risk_pct = risk / entry * 100.0
        reward_pct = reward / entry * 100.0
        actual_rr = reward / risk
        gate = validate_trade_intent({
            "execution_mode": "shadow_only",
            "side": "SHORT",
            "intent_status": "SHADOW_READY",
            "rr_ratio": actual_rr,
            "risk_distance_pct": risk_pct,
            "reward_distance_pct": reward_pct,
            "max_risk_pct": 0.5,
            "entry_price": entry,
            "stop_loss": stop,
            "take_profit": target,
        })
        if not gate.passed:
            blocked_geometry += 1
            continue

        outcome = simulate_trade(
            {
                "signal_id": f"weak_short_holdout_{symbol}_{timeframe}_{signal_index}",
                "entry_bar_index": entry_index,
                "entry_execution": "bar_open",
                "entry_price": entry,
                "stop_price": stop,
                "tp_price": target,
            },
            bar_dicts,
            params,
        )
        trades.append({
            "strategy_type": "weak_short_watch",
            "symbol": symbol,
            "timeframe": timeframe,
            "signal_time": float(bars[signal_index].timestamp),
            "signal_index": signal_index,
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
            "planned_watch_state": candidate.watch_state,
            "planned_priority": candidate.priority,
            "planned_rr": candidate.rr_ratio,
            "actual_rr_at_fill": round(actual_rr, 6),
        })
        unavailable_until = outcome.exit_bar_index

    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "fee_bps_per_side": fee_bps,
        "candidate_count": candidate_count,
        "blocked_no_next_bar": blocked_no_next_bar,
        "blocked_geometry": blocked_geometry,
        "blocked_overlap": blocked_overlap,
        "trade_count": len(trades),
        "metrics": compute_run_metrics(trades),
        "trades": trades,
    }


def _phase_trades(trades: list[dict], phase: str) -> list[dict]:
    if phase == "full":
        return trades
    if phase == "first_half":
        return [trade for trade in trades if trade["signal_time"] < SPLIT_EPOCH]
    if phase == "second_half":
        return [trade for trade in trades if trade["signal_time"] >= SPLIT_EPOCH]
    raise ValueError(phase)


def _compact_metrics(trades: list[dict]) -> dict:
    metrics = compute_run_metrics(trades)
    return {
        "trade_count": len(trades),
        "win_rate": metrics["win_rate"],
        "expectancy_r": metrics["expectancy_r"],
        "profit_factor": metrics["profit_factor"],
        "avg_mfe_r": metrics["avg_mfe_r"],
        "avg_mae_r": metrics["avg_mae_r"],
        "avg_hold_bars": metrics["avg_hold_bars"],
        "max_drawdown_r_not_portfolio_valid": metrics["max_drawdown_r"],
    }


def _aggregate(results: list[dict], fee_bps: float, phase: str) -> dict:
    selected = [result for result in results if result["fee_bps_per_side"] == fee_bps]
    trades = [
        trade
        for result in selected
        for trade in _phase_trades(result["trades"], phase)
    ]
    compact = _compact_metrics(trades)
    positive_series = []
    for result in selected:
        phase_series = _phase_trades(result["trades"], phase)
        series_metrics = compute_run_metrics(phase_series)
        if phase_series and float(series_metrics["expectancy_r"]) > 0:
            positive_series.append(f"{result['symbol']}:{result['timeframe']}")
    compact.update({
        "fee_bps_per_side": fee_bps,
        "phase": phase,
        "series_count": len(selected),
        "positive_expectancy_series": positive_series,
        "positive_series_count": len(positive_series),
        "portfolio_drawdown_not_computed": True,
    })
    return compact


def main() -> int:
    results: list[dict] = []

    for symbol in SYMBOLS:
        for timeframe in TIMEFRAMES:
            path = DATA_ROOT / symbol / f"{symbol}_{timeframe}.csv"
            history = _load_historical(path, symbol, timeframe, 1000)
            bars = _market_bars(history)
            candidates: list[SignalCandidate | None] = [None] * len(bars)
            for index in range(WINDOW_BARS - 1, len(bars)):
                candidates[index] = _candidate_at(bars, index)

            for fee_bps in FEE_BPS_GRID:
                result = _simulate_series(symbol, timeframe, bars, candidates, fee_bps)
                results.append(result)
                print(
                    symbol,
                    timeframe,
                    f"fee={fee_bps}bp",
                    f"candidates={result['candidate_count']}",
                    f"trades={result['trade_count']}",
                    f"pf={result['metrics']['profit_factor']}",
                    f"exp={result['metrics']['expectancy_r']}",
                )

    aggregate = {
        str(fee): {
            phase: _aggregate(results, fee, phase)
            for phase in ("full", "first_half", "second_half")
        }
        for fee in FEE_BPS_GRID
    }
    per_series = []
    for result in results:
        phases = {
            phase: _compact_metrics(_phase_trades(result["trades"], phase))
            for phase in ("full", "first_half", "second_half")
        }
        per_series.append({
            "symbol": result["symbol"],
            "timeframe": result["timeframe"],
            "fee_bps_per_side": result["fee_bps_per_side"],
            "candidate_count": result["candidate_count"],
            "blocked_no_next_bar": result["blocked_no_next_bar"],
            "blocked_geometry": result["blocked_geometry"],
            "blocked_overlap": result["blocked_overlap"],
            "phases": phases,
        })

    output = {
        "experiment_id": "weak_short_existing_baseline_older_holdout_v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "period": f"{START}..{END}",
        "split": SPLIT,
        "strategy_type": "weak_short_watch",
        "symbols": list(SYMBOLS),
        "timeframes": list(TIMEFRAMES),
        "candidate_authority": "core.paper_trading.strategy_registry.analyze_for_strategy",
        "decision_window_bars": WINDOW_BARS,
        "priority_contract": "HIGH_MEDIUM_ONLY_matches_run_enabled_strategies_payload",
        "indicator_overlays": False,
        "parameter_tuning": False,
        "symbol_selection": False,
        "entry_execution": "closed_signal_next_bar_open_v1",
        "existing_candidate_stop_target_preserved": True,
        "actual_fill_geometry_revalidated": True,
        "fee_grid_bps_per_side": list(FEE_BPS_GRID),
        "fee_grid_status": "hypothetical_research_stress_not_p1_03",
        "slippage_pct": 0.0,
        "aggregate": aggregate,
        "per_series": per_series,
        "safety": [
            "OFFLINE_RESEARCH_ONLY",
            "PUBLIC_HISTORY_ONLY",
            "NO_INDICATOR_OVERLAY",
            "NO_PRODUCTION_CHANGE",
            "NO_P1_03_ACTIVATION",
            "NO_TESTNET",
            "NO_LIVE",
            "NO_ORDER",
            "NO_ACCOUNT",
            "NO_SECRET",
        ],
    }

    destination = Path("research_results/weak_short_existing_baseline_older_holdout.json")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(output, indent=2), encoding="utf-8")

    print("=== AGGREGATE ===")
    for fee, phases in aggregate.items():
        print("FEE", fee)
        for phase, values in phases.items():
            print(phase, values)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
