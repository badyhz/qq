"""T1450 - PromotionReadinessScore frozen dataclass.

Pure, frozen, deterministic. No I/O. No timestamps. No network.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from core.promotion_readiness_dimension import PromotionReadinessDimension


@dataclass(frozen=True)
class PromotionReadinessScore:
    """Aggregated promotion readiness score across dimensions.

    Pure, frozen. No I/O. No random. No timestamps.
    """
    score_id: str
    file_path: str
    dimensions: Tuple[PromotionReadinessDimension, ...]
    overall_score: float
    threshold: float
    is_ready: bool
