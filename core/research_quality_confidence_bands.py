"""Research quality confidence bands — integrate bootstrap/OOS/NC confidence.

No network.
"""
from __future__ import annotations

from typing import Any, Dict


def integrate_confidence_bands(
    bootstrap_ci: Dict[str, Any] = None,
    oos_ci: Dict[str, Any] = None,
    nc_margin: float = 0.0,
) -> Dict[str, Any]:
    """Integrate confidence bands from multiple sources."""
    bands = {}

    if bootstrap_ci:
        wr = bootstrap_ci.get("win_rate_ci", {})
        exp = bootstrap_ci.get("expectancy_ci", {})
        bands["bootstrap_win_rate"] = {
            "lower": wr.get("ci_lower", 0),
            "upper": wr.get("ci_upper", 0),
        }
        bands["bootstrap_expectancy"] = {
            "lower": exp.get("ci_lower", 0),
            "upper": exp.get("ci_upper", 0),
        }

    if oos_ci:
        bands["oos_stability"] = {
            "lower": oos_ci.get("lower", 0),
            "upper": oos_ci.get("upper", 0),
        }

    bands["negative_control_margin"] = nc_margin

    return bands
