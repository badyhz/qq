"""Strategy research interface — dataclasses and validation contracts.

Defines StrategyDefinition, StrategySignal, and validation functions
for the multi-strategy research workbench.

All functions are pure, deterministic, offline-only.
No network, no exchange, no live, no submit.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# --- Allowed values ---

ALLOWED_STRATEGY_FAMILIES = frozenset({
    "breakout",
    "mean_reversion",
    "momentum",
    "volatility_compression",
})

ALLOWED_SIGNAL_SIDES = frozenset({"LONG", "SHORT", "FLAT"})

REQUIRED_SAFETY_NOTES = frozenset({
    "local pure function",
    "offline only",
    "no exchange client",
    "no live trading",
    "research signal only",
})

REQUIRED_BAR_FIELDS = ("timestamp", "open", "high", "low", "close", "volume")

FORBIDDEN_IMPORTS = frozenset({
    "live_runner",
    "submit_approved",
    "playbook",
    "testnet",
    "runtime",
    "planner",
    "binance_connector",
    "binance_http",
    "binance_testnet",
    "exchange",
    "credential_manager",
})

DEFAULT_SAFETY_FLAGS = {
    "no_live": True,
    "no_submit": True,
    "no_exchange": True,
    "no_network": True,
    "no_runtime_integration": True,
    "no_planner_integration": True,
}


# --- Dataclasses ---

@dataclass(frozen=True)
class StrategyDefinition:
    """Defines a research-only strategy adapter."""
    strategy_id: str
    strategy_family: str
    display_name: str
    description: str
    parameter_schema: Dict[str, Any]
    required_bar_fields: List[str]
    signal_generation_contract: Dict[str, Any]
    output_signal_format: str = "StrategySignal"
    safety_notes: List[str] = field(default_factory=list)
    safety_flags: Dict[str, bool] = field(default_factory=lambda: dict(DEFAULT_SAFETY_FLAGS))
    deterministic: bool = True
    local_only: bool = True
    no_network: bool = True
    no_exchange: bool = True


@dataclass(frozen=True)
class StrategySignal:
    """A single research-only signal emitted by a strategy adapter."""
    signal_id: str
    strategy_id: str
    symbol: str
    timeframe: str
    timestamp: float
    side: str  # LONG, SHORT, FLAT
    entry_reference_price: float
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


# --- Validation ---

class StrategyValidationError(Exception):
    """Raised when a strategy definition fails validation."""


def validate_strategy_definition(defn: StrategyDefinition) -> List[str]:
    """Validate a strategy definition. Returns list of errors (empty = valid)."""
    errors: List[str] = []

    if not defn.strategy_id:
        errors.append("missing strategy_id")
    if not defn.strategy_id.isidentifier() and not defn.strategy_id.replace("_", "").isalnum():
        errors.append(f"strategy_id must be snake_case alphanumeric: {defn.strategy_id!r}")

    if defn.strategy_family not in ALLOWED_STRATEGY_FAMILIES:
        errors.append(f"strategy_family must be one of {sorted(ALLOWED_STRATEGY_FAMILIES)}, got {defn.strategy_family!r}")

    if not defn.display_name:
        errors.append("missing display_name")
    if not defn.description:
        errors.append("missing description")

    if not defn.parameter_schema:
        errors.append("missing parameter_schema (must be non-empty bounded schema)")

    for field_name in REQUIRED_BAR_FIELDS:
        if field_name not in defn.required_bar_fields:
            errors.append(f"missing required_bar_fields: {field_name}")

    if not defn.safety_notes:
        errors.append("missing safety_notes")
    else:
        notes_set = set(n.lower() for n in defn.safety_notes)
        for required_note in REQUIRED_SAFETY_NOTES:
            if required_note.lower() not in notes_set:
                errors.append(f"missing required safety_note: {required_note!r}")

    if not defn.deterministic:
        errors.append("strategy must be deterministic")
    if not defn.local_only:
        errors.append("strategy must be local_only")
    if not defn.no_network:
        errors.append("strategy must be no_network")
    if not defn.no_exchange:
        errors.append("strategy must be no_exchange")

    for flag, expected in DEFAULT_SAFETY_FLAGS.items():
        actual = defn.safety_flags.get(flag)
        if actual != expected:
            errors.append(f"safety_flags[{flag!r}] must be {expected}, got {actual!r}")

    return errors


def validate_strategy_signal(sig: StrategySignal) -> List[str]:
    """Validate a strategy signal. Returns list of errors (empty = valid)."""
    errors: List[str] = []

    if not sig.signal_id:
        errors.append("missing signal_id")
    if not sig.strategy_id:
        errors.append("missing strategy_id")
    if not sig.symbol:
        errors.append("missing symbol")
    if not sig.timeframe:
        errors.append("missing timeframe")
    if sig.side not in ALLOWED_SIGNAL_SIDES:
        errors.append(f"side must be one of {sorted(ALLOWED_SIGNAL_SIDES)}, got {sig.side!r}")
    if sig.entry_reference_price <= 0:
        errors.append(f"entry_reference_price must be > 0, got {sig.entry_reference_price}")
    if not (0.0 <= sig.confidence <= 1.0):
        errors.append(f"confidence must be in [0.0, 1.0], got {sig.confidence}")

    return errors


def validate_adapter_safety(imports: List[str]) -> List[str]:
    """Check that adapter imports do not reference forbidden modules."""
    errors: List[str] = []
    for imp in imports:
        lower = imp.lower()
        for forbidden in FORBIDDEN_IMPORTS:
            if forbidden in lower:
                errors.append(f"forbidden import detected: {imp!r} (matches {forbidden!r})")
    return errors


def is_strategy_safe(defn: StrategyDefinition) -> bool:
    """Return True if strategy passes all safety checks."""
    errors = validate_strategy_definition(defn)
    return len(errors) == 0
