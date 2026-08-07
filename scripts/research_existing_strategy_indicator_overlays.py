#!/usr/bin/env python3
"""Deferred Stage-2 check: existing MACD 5m with the same two overlays.

Research branch only; do not merge.

This closes the only timeframe intentionally omitted from Stage 1. The existing
`macd_rebound_watch` authority is called directly on the latest 120 completed
bars. HIGH/MEDIUM candidates only, matching the production payload contract.

Variants are frozen from Stage 1:
- BASELINE
- ACCEL_POSITIVE_NON_EXTREME: signed_speed > 0 and regime != EXTREME
- IRON_TOP_VETO: reject Iron Top strength >= 1

No combinations, threshold tuning, symbol selection or new indicator rule.
Execution is next-bar-open, existing candidate stop/target levels are preserved,
actual fill geometry is revalidated, one exposure at a time. Fees 0 / 0.5 bp
per side are hypothetical research stress only; slippage is zero.
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
from core.paper_trading.aicoin_indicator_ports import evaluate_iron_top
from core.paper_trading.indicator_composite_strategy import AccelerationRegime
from core.paper_trading.market_accelerator_port import (
    calculate_market_accelerator,
    classify_accelerator_series,
)
from core.paper_trading.strategy_registry import SignalCandidate, analyze_for_strategy
from core.paper_trading.trade_intent_risk_gate import validate_trade_intent
from scripts.run_indicator_composite_backtest import _load_historical, _market_bars

START = "2025-08-01"
END = "2026-07-31"
WINDOW_BARS = 120
MAX_HOLD_BARS = 100
FEE_BPS_GRID = (0.0, 0.5)
SYMBOLS = ("BTCUSDT", "ETHUSDT", "BNBUSDT", "SUIUSDT", "1000PEPEUSDT")
TIMEFRAME = "5m"
VARIANTS = ("BASELINE", "ACCEL_POSITIVE_NON_EXTREME", "IRON_TOP_VETO")
DATA_ROOT = Path("data/existing_strategy_overlay_history")


def _candidate_at(bars, index: int) -> SignalCandidate | None:
    if index + 1 < WINDOW_BARS:
        return None
    result = analyze_for_strategy(
        strategy_id="macd_rebound_watch",
        strategy_type="macd_rebound_watch",
        bars=list(bars[index - WINDOW_BARS + 1:index + 1]),
    )
    candidate = result.candidate if result.success else None
    if candidate is None or candidate.priority not in {"HIGH", "MEDIUM"}:
        return None
    return candidate


def _iron_strength(bars, index: int) -> int:
    return evaluate_iron_top(bars[index - WINDOW_BARS + 1:index + 1]).strength


def _accepts(variant: str, bars, index: int, accelerator, regimes) -> bool:
    if variant == "BASELINE":
        return True
    if variant == "ACCEL_POSITIVE_NON_EXTREME":
        signed_speed = accelerator.points[index].signed_speed
        return (
            signed_speed is not None
            and signed_speed > 0
            and regimes[index].regime != AccelerationRegime.EXTREME
        )
    if variant == "IRON_TOP_VETO":
        return _iron_strength(bars, index) == 0
    raise ValueError(variant)


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


def _simulate(symbol: str, bars, candidates, accelerator, regimes, variant: str, fee_bps: float) -> dict:
    params = TradeSimulationParams(
        fee_pct=fee_bps / 10000.0,
        slippage_pct=0.0,
        max_hold_bars=MAX_HOLD_BARS,
    )
    bar_dicts = [_bar_dict(bar) for bar in bars]
    unavailable_until = -1
    base_candidates = 0
    overlay_pass = 0
    blocked_geometry = 0
    blocked_overlap = 0
    trades = []

    for signal_index, candidate in enumerate(candidates):
        if candidate is None:
            continue
        base_candidates += 1
        if not _accepts(variant, bars, signal_index, accelerator, regimes):
            continue
        overlay_pass += 1

        entry_index = signal_index + 1
        if entry_index >= len(bars) or entry_index <= unavailable_until:
            if entry_index <= unavailable_until:
                blocked_overlap += 1
            continue

        entry = float(bars[entry_index].open)
        stop = float(candidate.invalidation_level)
        target = float(candidate.take_profit_observation)
        risk = entry - stop
        reward = target - entry
        if entry <= 0 or risk <= 0 or reward <= 0:
            blocked_geometry += 1
            continue

        risk_pct = risk / entry * 100.0
        reward_pct = reward / entry * 100.0
        actual_rr = reward / risk
        gate = validate_trade_intent({
            "execution_mode": "shadow_only",
            "side": "LONG",
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
                "signal_id": f"macd5m_{symbol}_{variant}_{signal_index}",
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
            "symbol": symbol,
            "variant": variant,
            "realized_r": outcome.realized_r,
            "gross_pnl": outcome.gross_pnl,
            "fees": outcome.fees,
            "slippage_cost": outcome.slippage_cost,
            "net_pnl": outcome.net_pnl,
            "mfe_r": outcome.mfe_r,
            "mae_r": outcome.mae_r,
            "hold_bars": outcome.hold_bars,
        })
        unavailable_until = outcome.exit_bar_index

    return {
        "symbol": symbol,
        "variant": variant,
        "fee_bps_per_side": fee_bps,
        "base_candidate_count": base_candidates,
        "overlay_pass_count": overlay_pass,
        "coverage": round(overlay_pass / base_candidates, 6) if base_candidates else 0.0,
        "blocked_geometry": blocked_geometry,
        "blocked_overlap": blocked_overlap,
        "trade_count": len(trades),
        "metrics": compute_run_metrics(trades),
        "trades": trades,
    }


def _aggregate(results, variant: str, fee_bps: float) -> dict:
    selected = [r for r in results if r["variant"] == variant and r["fee_bps_per_side"] == fee_bps]
    trades = [trade for result in selected for trade in result["trades"]]
    metrics = compute_run_metrics(trades)
    base = sum(result["base_candidate_count"] for result in selected)
    passed = sum(result["overlay_pass_count"] for result in selected)
    return {
        "variant": variant,
        "fee_bps_per_side": fee_bps,
        "series_count": len(selected),
        "base_candidate_count": base,
        "overlay_pass_count": passed,
        "coverage": round(passed / base, 6) if base else 0.0,
        "trade_count": len(trades),
        "win_rate": metrics["win_rate"],
        "expectancy_r": metrics["expectancy_r"],
        "profit_factor": metrics["profit_factor"],
        "avg_mfe_r": metrics["avg_mfe_r"],
        "avg_mae_r": metrics["avg_mae_r"],
        "avg_hold_bars": metrics["avg_hold_bars"],
        "positive_symbols": [
            result["symbol"] for result in selected
            if float(result["metrics"]["expectancy_r"]) > 0
        ],
        "portfolio_drawdown_not_computed": True,
    }


def main() -> int:
    results = []
    for symbol in SYMBOLS:
        path = DATA_ROOT / symbol / f"{symbol}_{TIMEFRAME}.csv"
        history = _load_historical(path, symbol, TIMEFRAME, 1000)
        bars = _market_bars(history)
        accelerator = calculate_market_accelerator(bars)
        regimes = classify_accelerator_series(accelerator.points)
        candidates = [None] * len(bars)
        for index in range(WINDOW_BARS - 1, len(bars)):
            candidates[index] = _candidate_at(bars, index)

        for variant in VARIANTS:
            for fee_bps in FEE_BPS_GRID:
                result = _simulate(symbol, bars, candidates, accelerator, regimes, variant, fee_bps)
                results.append(result)
                print(symbol, variant, fee_bps, result["trade_count"], result["metrics"])

    aggregate = {
        variant: {
            str(fee): _aggregate(results, variant, fee)
            for fee in FEE_BPS_GRID
        }
        for variant in VARIANTS
    }
    output = {
        "experiment_id": "existing_macd_5m_indicator_overlays_stage2_v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "period": f"{START}..{END}",
        "strategy_type": "macd_rebound_watch",
        "timeframe": TIMEFRAME,
        "symbols": list(SYMBOLS),
        "candidate_authority": "core.paper_trading.strategy_registry.analyze_for_strategy",
        "decision_window_bars": WINDOW_BARS,
        "variants": list(VARIANTS),
        "overlay_combinations": False,
        "threshold_tuning": False,
        "symbol_selection": False,
        "entry_execution": "closed_signal_next_bar_open_v1",
        "existing_candidate_stop_target_preserved": True,
        "actual_fill_geometry_revalidated": True,
        "fee_grid_bps_per_side": list(FEE_BPS_GRID),
        "fee_grid_status": "hypothetical_research_stress_not_p1_03",
        "slippage_pct": 0.0,
        "aggregate": aggregate,
        "per_series": [
            {key: value for key, value in result.items() if key != "trades"}
            for result in results
        ],
        "safety": ["OFFLINE_RESEARCH_ONLY", "NO_PRODUCTION_CHANGE", "NO_P1_03_ACTIVATION", "NO_TESTNET", "NO_LIVE", "NO_ORDER"],
    }
    destination = Path("research_results/existing_macd_5m_indicator_overlays_stage2.json")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print("=== AGGREGATE ===")
    for variant, fees in aggregate.items():
        for fee, values in fees.items():
            print(variant, fee, values)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
