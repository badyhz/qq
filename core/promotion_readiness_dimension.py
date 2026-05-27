"""T1451 - PromotionReadinessDimension frozen dataclass.

Pure, frozen, deterministic. No I/O. No timestamps. No network.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ReadinessDimensionName(Enum):
    """Named readiness dimensions."""
    IMPORT_SAFETY = "IMPORT_SAFETY"
    NETWORK_SAFETY = "NETWORK_SAFETY"
    CREDENTIAL_SAFETY = "CREDENTIAL_SAFETY"
    SIDE_EFFECT_SAFETY = "SIDE_EFFECT_SAFETY"
    DRY_RUN_PROOF = "DRY_RUN_PROOF"
    HUMAN_APPROVAL = "HUMAN_APPROVAL"
    ROLLBACK_PLAN = "ROLLBACK_PLAN"


@dataclass(frozen=True)
class PromotionReadinessDimension:
    """Single dimension of promotion readiness.

    Pure, frozen. No I/O. No random. No timestamps.
    """
    dimension_id: str
    name: ReadinessDimensionName
    weight: float
    score: float
    max_score: float
