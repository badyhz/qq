"""Strategy registry adapters — register all four adapters.

Integrates breakout, mean reversion, momentum, and volatility compression
adapters into the strategy registry.

No network, no exchange, no live, no submit.
"""
from __future__ import annotations

from typing import Dict, List

from core.strategy_research_breakout import (
    BREAKOUT_PARAMETER_SCHEMA,
    BreakoutResearchParams,
    generate_breakout_signals,
)
from core.strategy_research_interface import (
    DEFAULT_SAFETY_FLAGS,
    REQUIRED_BAR_FIELDS,
    REQUIRED_SAFETY_NOTES,
    StrategyDefinition,
)
from core.strategy_research_mean_reversion import (
    MEAN_REVERSION_PARAMETER_SCHEMA,
    MeanReversionParams,
    generate_mean_reversion_signals,
)
from core.strategy_research_momentum import (
    MOMENTUM_PARAMETER_SCHEMA,
    MomentumParams,
    generate_momentum_signals,
)
from core.strategy_research_volatility_compression import (
    VOLATILITY_COMPRESSION_PARAMETER_SCHEMA,
    VolatilityCompressionParams,
    generate_volatility_compression_signals,
)
from core.strategy_registry_core import StrategyRegistry


# --- Strategy definition registry entries ---

STRATEGY_DEFINITIONS: Dict[str, StrategyDefinition] = {
    "breakout": StrategyDefinition(
        strategy_id="breakout",
        strategy_family="breakout",
        display_name="Breakout Strategy",
        description="Detect price breakout above local lookback range.",
        parameter_schema=BREAKOUT_PARAMETER_SCHEMA,
        required_bar_fields=list(REQUIRED_BAR_FIELDS),
        signal_generation_contract={"input": "ordered OHLCV bars", "output": "research signals", "deterministic": True},
        safety_notes=list(REQUIRED_SAFETY_NOTES),
        safety_flags=dict(DEFAULT_SAFETY_FLAGS),
    ),
    "mean_reversion": StrategyDefinition(
        strategy_id="mean_reversion",
        strategy_family="mean_reversion",
        display_name="Mean Reversion Strategy",
        description="Detect stretched move away from mean using z-score.",
        parameter_schema=MEAN_REVERSION_PARAMETER_SCHEMA,
        required_bar_fields=list(REQUIRED_BAR_FIELDS),
        signal_generation_contract={"input": "ordered OHLCV bars", "output": "research signals", "deterministic": True},
        safety_notes=list(REQUIRED_SAFETY_NOTES),
        safety_flags=dict(DEFAULT_SAFETY_FLAGS),
    ),
    "momentum": StrategyDefinition(
        strategy_id="momentum",
        strategy_family="momentum",
        display_name="Momentum Continuation Strategy",
        description="Identify directional continuation after sustained momentum.",
        parameter_schema=MOMENTUM_PARAMETER_SCHEMA,
        required_bar_fields=list(REQUIRED_BAR_FIELDS),
        signal_generation_contract={"input": "ordered OHLCV bars", "output": "research signals", "deterministic": True},
        safety_notes=list(REQUIRED_SAFETY_NOTES),
        safety_flags=dict(DEFAULT_SAFETY_FLAGS),
    ),
    "volatility_compression": StrategyDefinition(
        strategy_id="volatility_compression",
        strategy_family="volatility_compression",
        display_name="Volatility Compression Breakout",
        description="Detect low volatility compression followed by expansion breakout.",
        parameter_schema=VOLATILITY_COMPRESSION_PARAMETER_SCHEMA,
        required_bar_fields=list(REQUIRED_BAR_FIELDS),
        signal_generation_contract={"input": "ordered OHLCV bars", "output": "research signals", "deterministic": True},
        safety_notes=list(REQUIRED_SAFETY_NOTES),
        safety_flags=dict(DEFAULT_SAFETY_FLAGS),
    ),
}

# --- Signal generator dispatch ---

SIGNAL_GENERATORS = {
    "breakout": generate_breakout_signals,
    "mean_reversion": generate_mean_reversion_signals,
    "momentum": generate_momentum_signals,
    "volatility_compression": generate_volatility_compression_signals,
}

# --- Parameter classes for adapter dispatch ---

PARAMETER_CLASSES = {
    "breakout": BreakoutResearchParams,
    "mean_reversion": MeanReversionParams,
    "momentum": MomentumParams,
    "volatility_compression": VolatilityCompressionParams,
}


def register_all_adapters(registry: StrategyRegistry, strategy_ids: List[str] = None) -> List[str]:
    """Register all (or specified) adapters in the registry.

    Returns list of errors (empty = all registered successfully).
    """
    if strategy_ids is None:
        strategy_ids = sorted(STRATEGY_DEFINITIONS.keys())

    errors: List[str] = []
    for sid in strategy_ids:
        defn = STRATEGY_DEFINITIONS.get(sid)
        if defn is None:
            errors.append(f"unknown strategy: {sid!r}")
            continue
        reg_errors = registry.register(defn)
        if reg_errors:
            errors.extend(reg_errors)
    return errors


def get_signal_generator(strategy_id: str):
    """Get signal generator function for a strategy."""
    return SIGNAL_GENERATORS.get(strategy_id)


def get_parameter_class(strategy_id: str):
    """Get parameter dataclass for a strategy."""
    return PARAMETER_CLASSES.get(strategy_id)
