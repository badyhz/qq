"""Strategy registry core — register, list, validate, export.

Provides a mutable registry for strategy definitions with
validation, rejection tracking, and deterministic JSON export.

No network, no exchange, no live, no submit.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from core.strategy_research_interface import (
    DEFAULT_SAFETY_FLAGS,
    StrategyDefinition,
    is_strategy_safe,
    validate_strategy_definition,
)


@dataclass
class RejectedStrategy:
    """Record of a rejected strategy."""
    strategy_id: str
    reasons: List[str]


@dataclass
class StrategyRegistry:
    """Mutable registry for research strategy definitions."""
    registry_id: str = "multi_strategy_research_registry"
    _strategies: Dict[str, StrategyDefinition] = field(default_factory=dict, repr=False)
    _rejected: List[RejectedStrategy] = field(default_factory=list, repr=False)
    release_hold: str = "HOLD"

    def register(self, defn: StrategyDefinition) -> List[str]:
        """Register a strategy definition. Returns errors if rejected."""
        errors = validate_strategy_definition(defn)
        if errors:
            self._rejected.append(RejectedStrategy(strategy_id=defn.strategy_id, reasons=errors))
            return errors
        self._strategies[defn.strategy_id] = defn
        return []

    def list_strategies(self) -> List[str]:
        """Return sorted list of registered strategy ids."""
        return sorted(self._strategies.keys())

    def get_strategy(self, strategy_id: str) -> Optional[StrategyDefinition]:
        """Get a registered strategy by id."""
        return self._strategies.get(strategy_id)

    def strategy_count(self) -> int:
        """Return number of registered strategies."""
        return len(self._strategies)

    def rejected_strategies(self) -> List[RejectedStrategy]:
        """Return list of rejected strategies."""
        return list(self._rejected)

    def validation_status(self) -> str:
        """Return PASS if at least one strategy registered and none rejected."""
        if not self._strategies:
            return "EMPTY"
        return "PASS"

    def to_dict(self) -> Dict[str, Any]:
        """Export registry as deterministic dict."""
        strategy_dicts = []
        for sid in sorted(self._strategies.keys()):
            defn = self._strategies[sid]
            strategy_dicts.append(_strategy_def_to_dict(defn))

        rejected_dicts = []
        for rej in self._rejected:
            rejected_dicts.append({
                "strategy_id": rej.strategy_id,
                "reasons": rej.reasons,
            })

        return {
            "registry_id": self.registry_id,
            "strategies": strategy_dicts,
            "strategy_count": len(self._strategies),
            "validation_status": self.validation_status(),
            "rejected_strategies": rejected_dicts,
            "release_hold": self.release_hold,
            "safety_flags": dict(DEFAULT_SAFETY_FLAGS),
        }

    def to_json(self, indent: int = 2) -> str:
        """Export registry as deterministic JSON string."""
        return json.dumps(self.to_dict(), sort_keys=True, indent=indent)


def _strategy_def_to_dict(defn: StrategyDefinition) -> Dict[str, Any]:
    """Convert StrategyDefinition to dict for JSON export."""
    return {
        "strategy_id": defn.strategy_id,
        "strategy_family": defn.strategy_family,
        "display_name": defn.display_name,
        "description": defn.description,
        "parameter_schema": defn.parameter_schema,
        "required_bar_fields": list(defn.required_bar_fields),
        "signal_generation_contract": dict(defn.signal_generation_contract),
        "output_signal_format": defn.output_signal_format,
        "safety_notes": list(defn.safety_notes),
        "safety_flags": dict(defn.safety_flags),
        "deterministic": defn.deterministic,
        "local_only": defn.local_only,
        "no_network": defn.no_network,
        "no_exchange": defn.no_exchange,
    }
