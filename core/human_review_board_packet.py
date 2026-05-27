"""T1381 - HumanReviewBoardPacket frozen dataclass."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

from core.human_review_item import HumanReviewItem


class PacketDecision(Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    DEFER = "DEFER"
    PENDING = "PENDING"


@dataclass(frozen=True)
class HumanReviewBoardPacket:
    packet_id: str
    target_file: str
    risk_class: str
    review_items: tuple[HumanReviewItem, ...]
    decision: PacketDecision
    reviewer: str
