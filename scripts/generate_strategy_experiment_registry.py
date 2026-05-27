#!/usr/bin/env python3
"""Generate deterministic strategy registry.

Usage:
    python3 scripts/generate_strategy_experiment_registry.py \
        --output-dir /tmp/multi_strategy_research_workbench \
        --strategies breakout,mean_reversion,momentum,volatility_compression

Output: strategy_registry.json

Safety: local only, no network, no exchange, no live.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure project root on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.strategy_research_interface import (
    DEFAULT_SAFETY_FLAGS,
    REQUIRED_BAR_FIELDS,
    REQUIRED_SAFETY_NOTES,
    StrategyDefinition,
)
from core.strategy_registry_core import StrategyRegistry


# --- Strategy adapter definitions ---

BREAKOUT_SCHEMA = {
    "lookback_bars": {"type": "int", "min": 5, "max": 100, "default": 20},
    "breakout_buffer_pct": {"type": "float", "min": 0.001, "max": 0.05, "default": 0.005},
    "min_body_pct": {"type": "float", "min": 0.0, "max": 1.0, "default": 0.5},
    "cooldown_bars": {"type": "int", "min": 0, "max": 50, "default": 3},
    "stop_loss_pct": {"type": "float", "min": 0.005, "max": 0.1, "default": 0.02},
    "take_profit_rr": {"type": "float", "min": 1.0, "max": 5.0, "default": 2.0},
}

MEAN_REVERSION_SCHEMA = {
    "lookback_bars": {"type": "int", "min": 5, "max": 200, "default": 50},
    "zscore_entry": {"type": "float", "min": 1.0, "max": 4.0, "default": 2.0},
    "zscore_exit": {"type": "float", "min": 0.0, "max": 2.0, "default": 0.5},
    "min_volume_ratio": {"type": "float", "min": 0.5, "max": 5.0, "default": 1.0},
    "cooldown_bars": {"type": "int", "min": 0, "max": 50, "default": 5},
    "stop_loss_pct": {"type": "float", "min": 0.005, "max": 0.1, "default": 0.02},
    "take_profit_rr": {"type": "float", "min": 1.0, "max": 5.0, "default": 2.0},
}

MOMENTUM_SCHEMA = {
    "momentum_lookback_bars": {"type": "int", "min": 5, "max": 200, "default": 30},
    "min_return_pct": {"type": "float", "min": 0.001, "max": 0.1, "default": 0.02},
    "ema_fast": {"type": "int", "min": 3, "max": 50, "default": 10},
    "ema_slow": {"type": "int", "min": 10, "max": 200, "default": 50},
    "min_slope_pct": {"type": "float", "min": 0.0, "max": 0.05, "default": 0.001},
    "cooldown_bars": {"type": "int", "min": 0, "max": 50, "default": 3},
    "stop_loss_pct": {"type": "float", "min": 0.005, "max": 0.1, "default": 0.02},
    "take_profit_rr": {"type": "float", "min": 1.0, "max": 5.0, "default": 2.0},
}

VOLATILITY_COMPRESSION_SCHEMA = {
    "compression_lookback_bars": {"type": "int", "min": 5, "max": 200, "default": 30},
    "max_range_pct": {"type": "float", "min": 0.001, "max": 0.1, "default": 0.02},
    "breakout_lookback_bars": {"type": "int", "min": 5, "max": 100, "default": 20},
    "breakout_buffer_pct": {"type": "float", "min": 0.001, "max": 0.05, "default": 0.005},
    "volume_expansion_ratio": {"type": "float", "min": 1.0, "max": 5.0, "default": 1.5},
    "cooldown_bars": {"type": "int", "min": 0, "max": 50, "default": 3},
    "stop_loss_pct": {"type": "float", "min": 0.005, "max": 0.1, "default": 0.02},
    "take_profit_rr": {"type": "float", "min": 1.0, "max": 5.0, "default": 2.0},
}

STRATEGY_DEFS = {
    "breakout": StrategyDefinition(
        strategy_id="breakout",
        strategy_family="breakout",
        display_name="Breakout Strategy",
        description="Detect price breakout above local lookback range. Research-only signal.",
        parameter_schema=BREAKOUT_SCHEMA,
        required_bar_fields=list(REQUIRED_BAR_FIELDS),
        signal_generation_contract={
            "input": "ordered OHLCV bars",
            "output": "research signals",
            "deterministic": True,
        },
        safety_notes=list(REQUIRED_SAFETY_NOTES),
        safety_flags=dict(DEFAULT_SAFETY_FLAGS),
    ),
    "mean_reversion": StrategyDefinition(
        strategy_id="mean_reversion",
        strategy_family="mean_reversion",
        display_name="Mean Reversion Strategy",
        description="Detect stretched move away from mean. Research-only signal.",
        parameter_schema=MEAN_REVERSION_SCHEMA,
        required_bar_fields=list(REQUIRED_BAR_FIELDS),
        signal_generation_contract={
            "input": "ordered OHLCV bars",
            "output": "research signals",
            "deterministic": True,
        },
        safety_notes=list(REQUIRED_SAFETY_NOTES),
        safety_flags=dict(DEFAULT_SAFETY_FLAGS),
    ),
    "momentum": StrategyDefinition(
        strategy_id="momentum",
        strategy_family="momentum",
        display_name="Momentum Continuation Strategy",
        description="Identify directional continuation after sustained momentum.",
        parameter_schema=MOMENTUM_SCHEMA,
        required_bar_fields=list(REQUIRED_BAR_FIELDS),
        signal_generation_contract={
            "input": "ordered OHLCV bars",
            "output": "research signals",
            "deterministic": True,
        },
        safety_notes=list(REQUIRED_SAFETY_NOTES),
        safety_flags=dict(DEFAULT_SAFETY_FLAGS),
    ),
    "volatility_compression": StrategyDefinition(
        strategy_id="volatility_compression",
        strategy_family="volatility_compression",
        display_name="Volatility Compression Breakout",
        description="Identify low volatility compression followed by expansion breakout.",
        parameter_schema=VOLATILITY_COMPRESSION_SCHEMA,
        required_bar_fields=list(REQUIRED_BAR_FIELDS),
        signal_generation_contract={
            "input": "ordered OHLCV bars",
            "output": "research signals",
            "deterministic": True,
        },
        safety_notes=list(REQUIRED_SAFETY_NOTES),
        safety_flags=dict(DEFAULT_SAFETY_FLAGS),
    ),
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate strategy registry")
    parser.add_argument("--output-dir", required=True, help="Output directory")
    parser.add_argument("--strategies", required=True, help="Comma-separated strategy ids")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    strategy_ids = [s.strip() for s in args.strategies.split(",") if s.strip()]
    if not strategy_ids:
        print("ERROR: no strategies specified", file=sys.stderr)
        return 1

    registry = StrategyRegistry()
    for sid in strategy_ids:
        defn = STRATEGY_DEFS.get(sid)
        if defn is None:
            print(f"ERROR: unknown strategy {sid!r}", file=sys.stderr)
            return 1
        errors = registry.register(defn)
        if errors:
            print(f"ERROR: strategy {sid!r} rejected: {errors}", file=sys.stderr)
            return 2

    out_file = output_dir / "strategy_registry.json"
    out_file.write_text(registry.to_json())
    print(f"Wrote {out_file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
