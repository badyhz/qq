"""Parameter heatmap data — generate heatmap-ready data for parameter grid.

Pure functions. No network.
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple


def generate_heatmap_data(
    grid_points: List[Dict[str, Any]],
    x_param: str,
    y_param: str,
    score_key: str = "score",
) -> Dict:
    """Generate heatmap-ready data from parameter grid.

    Returns structured data for 2D parameter visualization.
    """
    x_values = sorted(set(p.get(x_param, 0) for p in grid_points))
    y_values = sorted(set(p.get(y_param, 0) for p in grid_points))

    matrix = []
    for y in y_values:
        row = []
        for x in x_values:
            matching = [p for p in grid_points if p.get(x_param) == x and p.get(y_param) == y]
            if matching:
                row.append(matching[0].get(score_key, 0))
            else:
                row.append(None)  # NaN placeholder
        matrix.append(row)

    return {
        "x_param": x_param,
        "y_param": y_param,
        "x_values": x_values,
        "y_values": y_values,
        "matrix": matrix,
        "total_cells": len(x_values) * len(y_values),
        "filled_cells": sum(1 for row in matrix for v in row if v is not None),
    }
