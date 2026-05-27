"""Offline backtest parameter grid. Pure dataclasses, no I/O."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class BacktestParameterSet:
    """Frozen parameter set for a single backtest run."""

    param_id: str
    label: str
    lookback_bars: int
    breakout_buffer_pct: float
    stop_loss_r: float
    take_profit_r: float
    max_hold_bars: int
    fee_bps: float
    slippage_bps: float
    min_body_pct: float
    cooldown_bars: int

    def __post_init__(self) -> None:
        errors = validate_param_set(self)
        if errors:
            raise ValueError(f"Invalid parameter set: {'; '.join(errors)}")


PARAM_PRESETS: Dict[str, dict] = {
    "conservative": {
        "lookback_bars": 30,
        "breakout_buffer_pct": 0.005,
        "stop_loss_r": 1.5,
        "take_profit_r": 3.0,
        "max_hold_bars": 100,
        "fee_bps": 10.0,
        "slippage_bps": 5.0,
        "min_body_pct": 0.5,
        "cooldown_bars": 10,
    },
    "balanced": {
        "lookback_bars": 20,
        "breakout_buffer_pct": 0.003,
        "stop_loss_r": 1.0,
        "take_profit_r": 2.0,
        "max_hold_bars": 80,
        "fee_bps": 10.0,
        "slippage_bps": 5.0,
        "min_body_pct": 0.4,
        "cooldown_bars": 5,
    },
    "aggressive": {
        "lookback_bars": 10,
        "breakout_buffer_pct": 0.002,
        "stop_loss_r": 0.75,
        "take_profit_r": 1.5,
        "max_hold_bars": 50,
        "fee_bps": 10.0,
        "slippage_bps": 5.0,
        "min_body_pct": 0.3,
        "cooldown_bars": 3,
    },
    "wide_stop": {
        "lookback_bars": 20,
        "breakout_buffer_pct": 0.003,
        "stop_loss_r": 2.0,
        "take_profit_r": 4.0,
        "max_hold_bars": 120,
        "fee_bps": 10.0,
        "slippage_bps": 5.0,
        "min_body_pct": 0.4,
        "cooldown_bars": 8,
    },
    "tight_stop": {
        "lookback_bars": 15,
        "breakout_buffer_pct": 0.002,
        "stop_loss_r": 0.5,
        "take_profit_r": 1.0,
        "max_hold_bars": 40,
        "fee_bps": 10.0,
        "slippage_bps": 5.0,
        "min_body_pct": 0.35,
        "cooldown_bars": 3,
    },
}


def validate_param_set(params) -> List[str]:
    """Return list of validation error strings. Empty list = valid."""
    errors = []
    if params.lookback_bars < 1:
        errors.append("lookback_bars must be >= 1")
    if params.breakout_buffer_pct < 0:
        errors.append("breakout_buffer_pct must be >= 0")
    if params.stop_loss_r <= 0:
        errors.append("stop_loss_r must be > 0")
    if params.take_profit_r <= 0:
        errors.append("take_profit_r must be > 0")
    if params.max_hold_bars < 1:
        errors.append("max_hold_bars must be >= 1")
    if params.fee_bps < 0:
        errors.append("fee_bps must be >= 0")
    if params.slippage_bps < 0:
        errors.append("slippage_bps must be >= 0")
    if not 0 <= params.min_body_pct <= 1:
        errors.append("min_body_pct must be in [0, 1]")
    if params.cooldown_bars < 0:
        errors.append("cooldown_bars must be >= 0")
    return errors


def build_param_grid(preset_labels: Tuple[str, ...] | List[str]) -> Tuple[BacktestParameterSet, ...]:
    """Build a tuple of BacktestParameterSet from named presets."""
    result = []
    for label in preset_labels:
        if label not in PARAM_PRESETS:
            raise KeyError(f"Unknown preset: {label}")
        preset = PARAM_PRESETS[label]
        result.append(
            BacktestParameterSet(
                param_id=f"preset_{label}",
                label=label,
                lookback_bars=preset["lookback_bars"],
                breakout_buffer_pct=preset["breakout_buffer_pct"],
                stop_loss_r=preset["stop_loss_r"],
                take_profit_r=preset["take_profit_r"],
                max_hold_bars=preset["max_hold_bars"],
                fee_bps=preset["fee_bps"],
                slippage_bps=preset["slippage_bps"],
                min_body_pct=preset["min_body_pct"],
                cooldown_bars=preset["cooldown_bars"],
            )
        )
    return tuple(result)
