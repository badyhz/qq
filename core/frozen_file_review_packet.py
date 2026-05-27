"""T1441 - FrozenFileReviewPacket frozen dataclass.

Pure, frozen. No I/O. No network. No random. No timestamps. No env reads.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from core.frozen_review_check import FrozenReviewCheck


VALID_RISK_CLASSES = ("HIGH", "MEDIUM")
VALID_DECISION_STATUSES = ("PENDING", "APPROVED", "DENIED", "DEFERRED")


class RiskClass(Enum):
    """Risk classification for frozen files."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"


class DecisionStatus(Enum):
    """Decision status for a review packet."""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    DENIED = "DENIED"
    DEFERRED = "DEFERRED"


@dataclass(frozen=True)
class FrozenFileReviewPacket:
    """Immutable review packet for a frozen file.

    Pure deterministic. No I/O. No timestamps. No network.
    """
    packet_id: str
    file_path: str
    risk_class: RiskClass
    file_category: str
    review_checks: tuple[FrozenReviewCheck, ...]
    evidence_requirements: tuple[str, ...]
    decision_status: DecisionStatus


def build_review_packet(
    packet_id: str,
    file_path: str,
    risk_class: str,
    file_category: str = "",
    review_checks: tuple[FrozenReviewCheck, ...] = (),
    evidence_requirements: tuple[str, ...] = (),
    decision_status: str = "PENDING",
) -> FrozenFileReviewPacket:
    """Factory for FrozenFileReviewPacket with string-to-enum conversion."""
    return FrozenFileReviewPacket(
        packet_id=packet_id,
        file_path=file_path,
        risk_class=RiskClass(risk_class),
        file_category=file_category,
        review_checks=review_checks,
        evidence_requirements=evidence_requirements,
        decision_status=DecisionStatus(decision_status),
    )
