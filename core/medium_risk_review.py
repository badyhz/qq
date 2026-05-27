from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MediumRiskReview:
    """T1211 - frozen dataclass for medium-risk review."""

    review_id: str
    scripts: tuple[str, ...]
    policies: tuple[str, ...]
    verdict: str
