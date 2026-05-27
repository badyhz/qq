from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReadinessNextWaveRecommendation:
    """Frozen next wave recommendation. No I/O, no timestamps."""

    wave_id: str
    recommended_tasks: tuple  # tuple of str
    prerequisites: tuple  # tuple of str
    human_approval_required: bool
