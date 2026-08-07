#!/usr/bin/env python3
"""Temporary research-only reconstruction test for the later Bottom Treasure formula.

This file lives only on the temporary research branch. It does not claim to be
the final AiCoin port. Known recovered formula components are held constant;
the unresolved 30-bar pressure-maximum definition is tested both current-
inclusive and previous-only.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from core.indicator_composite_backtest import (
    CompositeBacktestConfig,
    run_indicator_composite_ablation,
)
from core.offline_backtest_trade_simulator import TradeSimulationParams
from core.paper_trading.higher_timeframe_trend import align_higher_timeframe_trends
from core.paper_trading.indicator_composite_adapter import (
    build_external_bottom_composite_states,
)
from scripts.run_indicator_composite_backtest import _load_historical, _market_bars


def _rma(values: list[float], length: int = 3) -> list[float]:
    if not values:
        return []
    alpha = 1.0 / length
    out = [float(values[0])]
    for value in values[1:]:
        out.append(alpha * float(value) + (1.0 - alpha) * out[-1])
    return out


def _ema(values: list[float], length: int = 3) -> list[float]:
    if not values:
        return []
    alpha = 2.0 / (length + 1.0)
    out = [float(values[0])]
    for value in values[1:]:
        out.append(alpha * float(value) + (1.0 - alpha) * out[-1])
    return out


def _bottom_triggers(bars, pressure_max_mode: str):
    lows = [float(bar.low) for bar in bars]
    closes = [float(bar.close) for bar in bars]

    low_diff = [0.0]
    for index in range(1, len(bars)):
        low_diff.append(lows[index] - lows[index - 1])

    low_change_abs = _rma([abs(value) for value in low_diff], 3)
    low_change_up = _rma(
        [value if value > 0 else 0.0 for value in low_diff],
        3,
    )
    low_pressure = [
        0.0 if up == 0 else absolute / up * 100.0
        for absolute, up in zip(low_change_abs, low_change_up)
    ]
    pressure_ema = _ema([value * 10.0 for value in low_pressure], 3)

    pressure_max_30 = []
    for index in range(len(bars)):
        if pressure_max_mode == "current_inclusive_30":
            start = max(0, index - 29)
            window = pressure_ema[start:index + 1]
        elif pressure_max_mode == "previous_30":
            start = max(0, index - 30)
            window = pressure_ema[start:index]
        else:
            raise ValueError(pressure_max_mode)
        pressure_max_30.append(max(window) if window else 0.0)

    raw_treasure: list[float] = []
    new_low_30: list[bool] = []
    for index in range(len(bars)):
        previous_lows = lows[max(0, index - 30):index]
        is_new_low = bool(previous_lows) and lows[index] < min(previous_lows)
        new_low_30.append(is_new_low)
        raw_treasure.append(
            (pressure_ema[index] + pressure_max_30[index] * 2.0) / 2.0
            if is_new_low
            else 0.0
        )

    treasure_raw = [value / 618.0 for value in _ema(raw_treasure, 3)]
    treasure = [min(value, 100.0) for value in treasure_raw]
    buy_raw = [
        index > 0
        and new_low_30[index]
        and treasure[index] > 10.0
        and closes[index] > lows[index - 1]
        for index in range(len(bars))
    ]
    buy = [
        value and (index == 0 or not buy_raw[index - 1])
        for index, value in enumerate(buy_raw)
    ]
    return buy, treasure


def main() -> int:
    lower_path = Path(
        "data/indicator_composite_history/BTCUSDT/BTCUSDT_15m.csv"
    )
    higher_path = Path(
        "data/indicator_composite_history/BTCUSDT/BTCUSDT_1h.csv"
    )
    lower_hist = _load_historical(lower_path, "BTCUSDT", "15m", 500)
    higher_hist = _load_historical(higher_path, "BTCUSDT", "1h", 500)
    trends = align_higher_timeframe_trends(lower_hist, higher_hist)
    bars = _market_bars(lower_hist)
    config = CompositeBacktestConfig(
        simulation=TradeSimulationParams(
            slippage_pct=0.0,
            fee_pct=0.0,
            max_hold_bars=100,
        )
    )

    output = {
        "symbol": "BTCUSDT",
        "period": "2025-08-01..2026-07-31",
        "friction": "zero",
        "formula_status": "research_hypothesis_not_final_aicoin_port",
        "hypotheses": [],
    }

    for mode in ("current_inclusive_30", "previous_30"):
        triggers, treasure = _bottom_triggers(bars, mode)
        states = build_external_bottom_composite_states(bars, triggers, trends)
        ablation = run_indicator_composite_ablation(bars, states, config)
        record = {
            "pressure_max_mode": mode,
            "raw_buy_count": sum(triggers),
            "treasure_over_10_count": sum(value > 10.0 for value in treasure),
            "variants": {},
        }
        for entry in ablation["variants"]:
            result = entry["result"]
            metrics = result["metrics"]
            record["variants"][entry["variant"]] = {
                "signals": result["signal_count"],
                "trades": result["trade_count"],
                "win_rate": metrics["win_rate"],
                "expectancy_r": metrics["expectancy_r"],
                "profit_factor": metrics["profit_factor"],
                "max_drawdown_r": metrics["max_drawdown_r"],
                "avg_mfe_r": metrics["avg_mfe_r"],
                "avg_mae_r": metrics["avg_mae_r"],
            }
        output["hypotheses"].append(record)

    destination = Path("research_results/btc_smma_bottom_hypotheses.json")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(output, indent=2), encoding="utf-8")

    for record in output["hypotheses"]:
        print(f"=== SMMA_HYPOTHESIS {record['pressure_max_mode']} ===")
        print(
            "raw_buy_count=",
            record["raw_buy_count"],
            "treasure_over_10_count=",
            record["treasure_over_10_count"],
        )
        for name, values in record["variants"].items():
            print(name, values)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
