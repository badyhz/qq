from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReadinessRegression:
    """Frozen regression check. No I/O, no timestamps."""

    test_name: str
    passed: bool
    baseline_value: float
    current_value: float
    delta_pct: float
