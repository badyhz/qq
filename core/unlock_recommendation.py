"""T1459 - UnlockRecommendation frozen dataclass."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UnlockRecommendation:
    recommendation_id: str
    file_path: str
    risk_class: str
    readiness_score: float
    recommendation: str
    conditions: tuple[str, ...]
    blockers: tuple[str, ...]

    HOLD: str = "HOLD"
    PROMOTE: str = "PROMOTE"
    DEFER: str = "DEFER"
    REJECT: str = "REJECT"
    ALL_RECOMMENDATIONS: tuple[str, ...] = ("HOLD", "PROMOTE", "DEFER", "REJECT")
