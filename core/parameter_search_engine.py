"""Parameter search engine — deterministic grid search with budget enforcement.

Expands parameter spaces, generates parameter sets, enforces search budget,
and produces JSON artifacts.

No network, no exchange, no live, no submit.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from core.parameter_search_space import (
    ParameterSearchSpace,
    enumerate_parameter_sets,
    expand_search_space,
    search_space_to_dict,
)
from core.strategy_research_parameters import (
    ParameterSchema,
    ParameterSet,
    parameter_set_to_dict,
)


@dataclass
class ParameterSearchResult:
    """Result of a parameter search operation."""
    search_result_id: str = "parameter_search_001"
    strategy_ids: List[str] = field(default_factory=list)
    search_budget: int = 120
    expanded_combinations: int = 0
    evaluated_combinations: int = 0
    budget_truncated: bool = False
    overfit_warning: bool = False
    small_fixture_warning: bool = False
    parameter_sets: List[ParameterSet] = field(default_factory=list)
    search_spaces: List[ParameterSearchSpace] = field(default_factory=list)
    release_hold: str = "HOLD"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        return {
            "search_result_id": self.search_result_id,
            "strategy_ids": sorted(self.strategy_ids),
            "search_budget": self.search_budget,
            "expanded_combinations": self.expanded_combinations,
            "evaluated_combinations": self.evaluated_combinations,
            "budget_truncated": self.budget_truncated,
            "overfit_warning": self.overfit_warning,
            "small_fixture_warning": self.small_fixture_warning,
            "parameter_sets": [parameter_set_to_dict(ps) for ps in self.parameter_sets],
            "search_spaces": [search_space_to_dict(ss) for ss in self.search_spaces],
            "release_hold": self.release_hold,
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON."""
        return json.dumps(self.to_dict(), sort_keys=True, indent=indent)


def run_parameter_search(
    schemas: Dict[str, ParameterSchema],
    search_budget: int = 120,
    preset_values: Dict[str, Dict[str, Any]] = None,
) -> ParameterSearchResult:
    """Run grid search across multiple strategy schemas.

    Returns ParameterSearchResult with all parameter sets.
    Enforces search budget across the entire strategy universe.
    """
    if preset_values is None:
        preset_values = {}

    all_param_sets: List[ParameterSet] = []
    all_search_spaces: List[ParameterSearchSpace] = []
    total_expanded = 0
    budget_truncated = False
    strategy_ids = sorted(schemas.keys())

    # Calculate total combinations across all strategies
    for sid in strategy_ids:
        schema = schemas[sid]
        presets = preset_values.get(sid, {})
        space = expand_search_space(schema, search_budget, presets)
        total_expanded += space.expanded_combinations
        all_search_spaces.append(space)

    # Apply global budget
    if total_expanded > search_budget:
        budget_truncated = True

    # Enumerate parameter sets per strategy, sharing budget
    remaining_budget = search_budget
    for sid in strategy_ids:
        schema = schemas[sid]
        presets = preset_values.get(sid, {})
        per_strategy_budget = max(1, remaining_budget // len(strategy_ids))
        ps, truncated = enumerate_parameter_sets(
            schema,
            search_budget=per_strategy_budget,
            preset_values=presets,
            budget_truncate=True,
        )
        if truncated:
            budget_truncated = True
        all_param_sets.extend(ps)
        remaining_budget -= len(ps)

    return ParameterSearchResult(
        strategy_ids=strategy_ids,
        search_budget=search_budget,
        expanded_combinations=total_expanded,
        evaluated_combinations=len(all_param_sets),
        budget_truncated=budget_truncated,
        overfit_warning=budget_truncated,
        small_fixture_warning=False,
        parameter_sets=all_param_sets,
        search_spaces=all_search_spaces,
    )
