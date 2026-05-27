"""Parameter search space — model and presets for grid search.

Defines search space with bounded parameter ranges, named presets,
and deterministic combination expansion.

No network, no exchange, no live, no submit.
"""
from __future__ import annotations

import itertools
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

from core.strategy_research_parameters import (
    NamedPreset,
    ParameterSchema,
    ParameterSpec,
    ParameterSet,
    generate_default_presets,
    make_parameter_set_id,
)


@dataclass(frozen=True)
class ParameterSearchSpace:
    """A bounded search space for a strategy."""
    search_space_id: str
    strategy_id: str
    parameters: Tuple[ParameterSpec, ...]
    expanded_combinations: int
    search_budget: int
    bounded: bool = True
    deterministic_order: bool = True


def _expand_values(spec: ParameterSpec) -> List[Any]:
    """Expand a parameter spec into concrete values."""
    if spec.type == "enum":
        return sorted(spec.values)
    # For numeric: use default value if available, otherwise min/max/mid
    values = []
    if spec.default is not None:
        values.append(spec.default)
    if spec.min is not None:
        values.append(spec.min)
    if spec.max is not None:
        values.append(spec.max)
    # Add midpoint
    if spec.min is not None and spec.max is not None:
        mid = (spec.min + spec.max) / 2.0
        if spec.type == "int":
            mid = int(round(mid))
        else:
            mid = round(mid, 6)
        if mid not in values:
            values.append(mid)
    # Deduplicate and sort
    return sorted(set(values))


def expand_search_space(
    schema: ParameterSchema,
    search_budget: int = 120,
    preset_values: Dict[str, Any] = None,
) -> ParameterSearchSpace:
    """Expand parameter schema into search space with bounded combinations.

    If preset_values given, include those as additional values.
    """
    all_params = list(schema.parameters)
    total_combos = 1
    for spec in all_params:
        vals = _expand_values(spec)
        if preset_values and spec.name in preset_values:
            pv = preset_values[spec.name]
            if pv not in vals:
                vals.append(pv)
                vals = sorted(vals)
        total_combos *= len(vals)

    return ParameterSearchSpace(
        search_space_id=f"search_space_{schema.strategy_id}",
        strategy_id=schema.strategy_id,
        parameters=tuple(all_params),
        expanded_combinations=total_combos,
        search_budget=search_budget,
        bounded=True,
        deterministic_order=True,
    )


def enumerate_parameter_sets(
    schema: ParameterSchema,
    search_budget: int = 120,
    preset_values: Dict[str, Any] = None,
    budget_truncate: bool = True,
) -> Tuple[List[ParameterSet], bool]:
    """Enumerate all parameter sets from schema.

    Returns (parameter_sets, budget_truncated).
    If combinations exceed budget and budget_truncate=True, truncates.
    """
    all_params = list(schema.parameters)
    value_lists: List[List[Any]] = []
    param_names: List[str] = []

    for spec in all_params:
        vals = _expand_values(spec)
        if preset_values and spec.name in preset_values:
            pv = preset_values[spec.name]
            if pv not in vals:
                vals.append(pv)
                vals = sorted(vals)
        value_lists.append(vals)
        param_names.append(spec.name)

    combos = list(itertools.product(*value_lists))
    truncated = False
    if len(combos) > search_budget:
        if budget_truncate:
            combos = combos[:search_budget]
            truncated = True

    # Sort deterministically
    combos.sort()

    param_sets: List[ParameterSet] = []
    for idx, combo in enumerate(combos):
        params = dict(zip(param_names, combo))
        psid = make_parameter_set_id(schema.strategy_id, params)
        param_sets.append(ParameterSet(
            parameter_set_id=psid,
            strategy_id=schema.strategy_id,
            preset_name=None,
            parameters=params,
            source="grid_search",
        ))

    return param_sets, truncated


def search_space_to_dict(space: ParameterSearchSpace) -> Dict[str, Any]:
    """Serialize search space to dict."""
    return {
        "search_space_id": space.search_space_id,
        "strategy_id": space.strategy_id,
        "expanded_combinations": space.expanded_combinations,
        "search_budget": space.search_budget,
        "bounded": space.bounded,
        "deterministic_order": space.deterministic_order,
    }
