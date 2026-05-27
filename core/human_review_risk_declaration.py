"""T1385 - HumanReviewRiskDeclaration frozen dataclass."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum


class RiskLevel(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True)
class HumanReviewRiskDeclaration:
    declaration_id: str
    risk_level: RiskLevel
    acknowledged_risks: tuple[str, ...]
    mitigation_plan: str
    reviewer_acknowledgement: bool
