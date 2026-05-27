"""T1383 - HumanReviewDecisionRecord frozen dataclass."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum


class ReviewDecision(Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    DEFER = "DEFER"
    ESCALATE = "ESCALATE"


@dataclass(frozen=True)
class HumanReviewDecisionRecord:
    record_id: str
    decision: ReviewDecision
    rationale: str
    conditions: tuple[str, ...]
    reviewer_id: str
