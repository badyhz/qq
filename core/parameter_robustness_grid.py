"""Parameter robustness grid — neighborhood perturbation grid.

Respects search budget. Deterministic ordering.
Pure functions. No network.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


@dataclass(frozen=True)
class ParameterPoint:
    """A single parameter combination."""
    param_id: str
    parameters: Dict[str, Any]
    score: float = 0.0


def build_perturbation_grid(
    base_params: Dict[str, Any],
    param_ranges: Dict[str, List[Any]],
    search_budget: int = 120,
) -> Tuple[ParameterPoint, ...]:
    """Build perturbation grid around base parameters.

    Respects search_budget. Deterministic ordering.
    """
    # Generate grid points
    param_names = sorted(param_ranges.keys())
    points = [base_params]

    for name in param_names:
        values = param_ranges[name]
        for v in values:
            if v != base_params.get(name):
                pt = dict(base_params)
                pt[name] = v
                points.append(pt)

    # Enforce budget
    if len(points) > search_budget:
        points = points[:search_budget]

    # Build parameter points
    result = []
    for i, p in enumerate(sorted(points, key=lambda x: str(x))):
        param_id = f"param_{i:04d}"
        result.append(ParameterPoint(param_id=param_id, parameters=p))

    return tuple(result)


def grid_to_dict(points: Tuple[ParameterPoint, ...]) -> Dict:
    return {
        "points": [
            {"param_id": p.param_id, "parameters": p.parameters, "score": p.score}
            for p in points
        ],
        "total_points": len(points),
    }
