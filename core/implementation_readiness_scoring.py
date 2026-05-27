from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ImplementationReadinessScoring:
    """Frozen scoring container. Pure deterministic, no I/O."""

    scoring_id: str
    dimensions: tuple  # tuple of ReadinessScoreDimension
    blockers: tuple  # tuple of ReadinessBlocker
    hold_state: object  # ReadinessHoldState
    verdict: object  # ReadinessScoringVerdict
