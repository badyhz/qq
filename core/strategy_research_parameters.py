"""Strategy research parameters — bounded parameter schema and sets.

Defines parameter schema with min/max/default/values, deterministic ordering,
and parameter set generation.

All functions are pure, deterministic, offline-only.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple


@dataclass(frozen=True)
class ParameterSpec:
    """Specification for a single strategy parameter."""
    name: str
    type: str  # "int", "float", "enum"
    min: Optional[float] = None
    max: Optional[float] = None
    default: Optional[Any] = None
    values: Optional[Tuple[Any, ...]] = None

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("parameter name must not be empty")
        if self.type not in ("int", "float", "enum"):
            raise ValueError(f"type must be int/float/enum, got {self.type!r}")
        if self.type == "enum":
            if not self.values:
                raise ValueError(f"enum parameter {self.name!r} must have values")
        else:
            if self.min is None:
                raise ValueError(f"numeric parameter {self.name!r} must have min")
            if self.max is None:
                raise ValueError(f"numeric parameter {self.name!r} must have max")
            if self.min > self.max:
                raise ValueError(f"parameter {self.name!r}: min ({self.min}) > max ({self.max})")


@dataclass(frozen=True)
class ParameterSchema:
    """Bounded parameter schema for a strategy."""
    strategy_id: str
    parameters: Tuple[ParameterSpec, ...]
    bounded: bool = True
    deterministic_order: bool = True


@dataclass(frozen=True)
class ParameterSet:
    """A single parameter combination."""
    parameter_set_id: str
    strategy_id: str
    preset_name: Optional[str]
    parameters: Dict[str, Any]
    source: str = "grid_search"
    release_hold: str = "HOLD"


@dataclass(frozen=True)
class NamedPreset:
    """A named parameter preset (seed for research)."""
    name: str  # conservative, balanced, aggressive
    parameter_values: Dict[str, Any]


# --- Validation ---

class ParameterValidationError(Exception):
    """Raised when a parameter schema fails validation."""


def validate_parameter_spec(spec: ParameterSpec) -> List[str]:
    """Validate a single parameter spec. Returns list of errors."""
    errors: List[str] = []
    if not spec.name:
        errors.append("parameter name must not be empty")
    if spec.type not in ("int", "float", "enum"):
        errors.append(f"type must be int/float/enum, got {spec.type!r}")
    if spec.type == "enum":
        if not spec.values:
            errors.append(f"enum parameter {spec.name!r} must have values")
    else:
        if spec.min is None:
            errors.append(f"numeric parameter {spec.name!r} must have min")
        if spec.max is None:
            errors.append(f"numeric parameter {spec.name!r} must have max")
        elif spec.min is not None and spec.min > spec.max:
            errors.append(f"parameter {spec.name!r}: min ({spec.min}) > max ({spec.max})")
    return errors


def validate_parameter_schema(schema: ParameterSchema) -> List[str]:
    """Validate a parameter schema. Returns list of errors."""
    errors: List[str] = []
    if not schema.strategy_id:
        errors.append("missing strategy_id")
    if not schema.parameters:
        errors.append("parameters must be non-empty")
    if not schema.bounded:
        errors.append("schema must be bounded")
    if not schema.deterministic_order:
        errors.append("schema must have deterministic_order")
    for spec in schema.parameters:
        errors.extend(validate_parameter_spec(spec))
    return errors


# --- Preset generation ---

def generate_default_presets(schema: ParameterSchema) -> List[NamedPreset]:
    """Generate conservative/balanced/aggressive presets from schema."""
    presets: List[NamedPreset] = []
    for name in ("conservative", "balanced", "aggressive"):
        values: Dict[str, Any] = {}
        for spec in schema.parameters:
            if spec.type == "enum":
                if name == "conservative":
                    values[spec.name] = spec.values[0]
                elif name == "aggressive":
                    values[spec.name] = spec.values[-1]
                else:
                    mid = len(spec.values) // 2
                    values[spec.name] = spec.values[mid]
            else:
                if name == "conservative":
                    values[spec.name] = spec.min
                elif name == "aggressive":
                    values[spec.name] = spec.max
                else:
                    mid = (spec.min + spec.max) / 2.0
                    if spec.type == "int":
                        values[spec.name] = int(round(mid))
                    else:
                        values[spec.name] = round(mid, 6)
        presets.append(NamedPreset(name=name, parameter_values=values))
    return presets


# --- Parameter set id generation ---

def make_parameter_set_id(strategy_id: str, params: Dict[str, Any]) -> str:
    """Generate deterministic parameter_set_id from strategy_id and params."""
    sorted_keys = sorted(params.keys())
    canonical = json.dumps(
        {k: params[k] for k in sorted_keys},
        sort_keys=True,
        separators=(",", ":"),
    )
    digest = hashlib.sha256(f"{strategy_id}:{canonical}".encode()).hexdigest()[:12]
    return f"{strategy_id}_ps_{digest}"


# --- Serialization ---

def parameter_spec_to_dict(spec: ParameterSpec) -> Dict[str, Any]:
    """Serialize ParameterSpec to dict."""
    d: Dict[str, Any] = {"name": spec.name, "type": spec.type}
    if spec.type == "enum":
        d["values"] = list(spec.values)
    else:
        d["min"] = spec.min
        d["max"] = spec.max
    if spec.default is not None:
        d["default"] = spec.default
    return d


def parameter_schema_to_dict(schema: ParameterSchema) -> Dict[str, Any]:
    """Serialize ParameterSchema to dict."""
    return {
        "strategy_id": schema.strategy_id,
        "parameters": [parameter_spec_to_dict(s) for s in schema.parameters],
        "bounded": schema.bounded,
        "deterministic_order": schema.deterministic_order,
    }


def parameter_set_to_dict(ps: ParameterSet) -> Dict[str, Any]:
    """Serialize ParameterSet to dict."""
    return {
        "parameter_set_id": ps.parameter_set_id,
        "strategy_id": ps.strategy_id,
        "preset_name": ps.preset_name,
        "parameters": dict(ps.parameters),
        "source": ps.source,
        "release_hold": ps.release_hold,
    }
