"""T1382 - HumanReviewItem frozen dataclass."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum


class ReviewItemStatus(Enum):
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class HumanReviewItem:
    item_id: str
    category: str
    description: str
    required: bool
    status: ReviewItemStatus
